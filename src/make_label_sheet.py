"""Build a labeling sheet for the faithfulness gate.

Writes a sample of (event, summary) pairs. The sheet has the event fields and
the summary. Generator source and the gate decision go to label_key.csv.
score_labels.py compares the gate with the labels filled in later.

--dataset both draws from AIT-ADS and GUIDE and balances corpus and gate
decision (about n/4 in each of AIT-emit, AIT-review, GUIDE-emit, GUIDE-review).

Usage:
  MAAT_OLLAMA_MODEL=llama3.2:3b python3 make_label_sheet.py --dataset both --n 300
Outputs:
  results/labels/label_sheet.csv  (fill human_faithful_1..4)
  results/labels/label_key.csv    (id -> source, gate_decision; keep from annotators)
"""
from __future__ import annotations

import argparse
import csv
import os
import random
from collections import defaultdict

import nlip_soc as core
import generators as gen
import run_experiment as R
from paths import RESULTS


def compact_event(ev):
    return {
        "product": ev["metadata"]["product"]["name"],
        "title": ev["finding_info"]["title"],
        "severity": ev["severity"],
        "src_ip": ev["src_endpoint"].get("ip"),
        "dst_ip": ev["dst_endpoint"].get("ip"),
        "user": ev["actor"]["user"].get("name"),
    }


def build_rows(cname, cmode, n_alerts, seed, scenario, data_dir, use_ollama, rng):
    """Return candidate rows (grounded/ungrounded/injection summaries) for one corpus."""
    grounded_fn = gen.ollama_agent if use_ollama else gen.grounded_template
    items, adapters, _ = R.load_dataset(cname, data_dir, n_alerts, seed, scenario, cmode)
    rows = []
    for it in items:
        ev = adapters[it["detector"]](it["native"])
        cands = []
        g = grounded_fn(ev) if use_ollama else gen.grounded_template(ev, rng, slip_rate=0.15)
        cands.append(("grounded", g))
        cands.append(("ungrounded", gen.hallucinating(ev, rng)))
        inj = gen.INJECTIONS[rng.randrange(len(gen.INJECTIONS))]
        cands.append(("injection", gen.injection_naive(ev, inj)))
        for src, summ in cands:
            fr = core.validate_faithfulness(summ, ev)
            rows.append({"dataset": cname, "detector": it["detector"], "source": src,
                         "gate_decision": fr.decision, **compact_event(ev), "summary": summ})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="both",
                    choices=["synthetic", "ait_ads", "guide", "both"])
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--scenario", default="russellmitchell")
    ap.add_argument("--mode", default="csv_pooled")
    ap.add_argument("--n", type=int, default=300, help="target rows on the sheet (~half emitted)")
    ap.add_argument("--seed", type=int, default=23)
    args = ap.parse_args()

    if args.dataset == "both":
        corpora = [("ait_ads", "csv_pooled"), ("guide", "auto")]
    else:
        corpora = [(args.dataset, args.mode)]

    n_alerts = max(args.n, 80)
    use_ollama = gen.ollama_available()
    rng = random.Random(args.seed)

    all_rows = []
    for cname, cmode in corpora:
        all_rows += build_rows(cname, cmode, n_alerts, args.seed, args.scenario,
                               args.data_dir, use_ollama, rng)

    # Balance the sheet. With multiple corpora, stratify across (corpus, gate) so both
    # corpora and both gate decisions are well represented; otherwise 50/50 by gate.
    if len(corpora) > 1:
        buckets = defaultdict(list)
        for r in all_rows:
            buckets[(r["dataset"], r["gate_decision"])].append(r)
        per = max(1, args.n // len(buckets))
        rows = []
        for k in sorted(buckets):
            rng.shuffle(buckets[k])
            rows += buckets[k][:per]
    else:
        emit = [r for r in all_rows if r["gate_decision"] == "EMIT"]
        review = [r for r in all_rows if r["gate_decision"] != "EMIT"]
        rng.shuffle(emit); rng.shuffle(review)
        half = args.n // 2
        rows = emit[:half] + review[:args.n - half]
    rng.shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["id"] = i

    out_dir = os.path.join(RESULTS, "labels")
    os.makedirs(out_dir, exist_ok=True)
    sheet_path = os.path.join(out_dir, "label_sheet.csv")
    key_path = os.path.join(out_dir, "label_key.csv")

    sheet_cols = ["id", "dataset", "detector", "product", "title", "severity",
                  "src_ip", "dst_ip", "user", "summary",
                  "human_faithful_1", "human_faithful_2", "human_faithful_3",
                  "human_faithful_4", "human_faithful_adjudicated", "notes"]
    with open(sheet_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sheet_cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r.update({"human_faithful_1": "", "human_faithful_2": "",
                      "human_faithful_3": "", "human_faithful_4": "",
                      "human_faithful_adjudicated": "", "notes": ""})
            w.writerow(r)

    with open(key_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "gate_decision"])
        for r in rows:
            w.writerow([r["id"], r["source"], r["gate_decision"]])

    from collections import Counter
    by_corpus = Counter(r["dataset"] for r in rows)
    n_emit = sum(1 for r in rows if r["gate_decision"] == "EMIT")
    print(f"wrote {sheet_path}: {len(rows)} blinded rows "
          f"({n_emit} EMIT, {len(rows) - n_emit} MANUAL_REVIEW; by corpus {dict(by_corpus)})")
    print(f"wrote {key_path}: id -> source/gate_decision (keep away from annotators)")
    print("generator:", ("ollama:" + gen.OLLAMA_MODEL) if use_ollama else "deterministic templates")
    print("Fill human_faithful_1..4 (y/n) INDEPENDENTLY; score_labels.py takes the majority "
          "vote and reports Fleiss' kappa.")


if __name__ == "__main__":
    main()
