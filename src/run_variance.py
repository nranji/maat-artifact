"""Variance decomposition: model stochasticity vs sampling.

Fixes one AIT-ADS sample (seed 7, n=40/detector) and one GUIDE sample (seed 7, n=120),
then generates k independent grounded summaries per alert with the configured Ollama
model. Reports between-generation SD of C2 emitted-clean and gated-to-review, alongside
the between-seed SD already in the committed aggregates.

Writes only to results/variance/. Does not touch results/all*, paper, or other dirs.

Usage:
  MAAT_OLLAMA_MODEL=llama3.2:3b python3 run_variance.py --k 5
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time

import generators as gen
import nlip_soc as core
import run_experiment as R
from run_all import _e2_stats
from paths import RESULTS

OUT = os.path.join(RESULTS, "variance")

# Fixed samples (do not change without renaming the output).
CORPORA = [
    # label, dataset, mode, n, seed, between_seed_source
    ("ait_csv_pooled", "ait_ads", "csv_pooled", 40, 7, "all"),
    ("guide_train", "guide", None, 120, 7, "all_n120"),
]


def _sd(xs):
    return round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0


def _mean(xs):
    return round(statistics.mean(xs), 4) if xs else None


def between_seed_sd(source_subdir, label):
    path = os.path.join(RESULTS, source_subdir, "consolidated.json")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    for a in payload.get("aggregated") or []:
        if a["label"] == label:
            return {
                "C2_emitted_clean_pct_sd": a["E2_C2_emitted_clean_pct"]["std"],
                "C2_emitted_clean_pct_mean": a["E2_C2_emitted_clean_pct"]["mean"],
                "gated_to_review_pct_sd": a["E2_gated_to_review_pct"]["std"],
                "gated_to_review_pct_mean": a["E2_gated_to_review_pct"]["mean"],
                "n_seeds": a["E2_C2_emitted_clean_pct"]["n"],
                "source": path,
            }
    raise KeyError(f"{label} not in {path} aggregated")


def run_corpus(label, dataset, mode, n, seed, k):
    items, adapters, desc = R.load_dataset(
        dataset, None, n, seed, "russellmitchell", mode or "auto", "train")
    events = [(it, adapters[it["detector"]](it["native"])) for it in items]
    print(f"[variance] {label}: n={len(events)} alerts, k={k} gens, "
          f"model={gen.OLLAMA_MODEL}", flush=True)

    per_gen = []
    for g in range(k):
        t0 = time.perf_counter()
        pairs = []
        for it, ev in events:
            # rng is ignored by ollama_agent; each call is an independent draw
            summary = gen.ollama_agent(ev)
            pairs.append((summary, ev))
        c2 = _e2_stats(pairs, gate=False)
        c3 = _e2_stats(pairs, gate=True)
        row = {
            "generation": g,
            "n_alerts": len(pairs),
            "C2_emitted_clean_pct": c2["emitted_clean_pct"],
            "gated_to_review_pct": c3["gated_to_manual_review_pct"],
            "wall_sec": round(time.perf_counter() - t0, 1),
        }
        per_gen.append(row)
        print(f"  gen {g}: C2={row['C2_emitted_clean_pct']} "
              f"gated={row['gated_to_review_pct']} "
              f"({row['wall_sec']}s)", flush=True)
    return {
        "label": label,
        "dataset": dataset,
        "desc": desc,
        "n_alerts": len(events),
        "sample_seed": seed,
        "k": k,
        "per_generation": per_gen,
        "between_generation": {
            "C2_emitted_clean_pct_mean": _mean([r["C2_emitted_clean_pct"] for r in per_gen]),
            "C2_emitted_clean_pct_sd": _sd([r["C2_emitted_clean_pct"] for r in per_gen]),
            "gated_to_review_pct_mean": _mean([r["gated_to_review_pct"] for r in per_gen]),
            "gated_to_review_pct_sd": _sd([r["gated_to_review_pct"] for r in per_gen]),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5, help="independent generations per fixed sample")
    args = ap.parse_args()
    if not gen.ollama_available():
        raise SystemExit("Ollama not reachable; cannot run variance decomposition")

    os.makedirs(OUT, exist_ok=True)
    t0 = time.perf_counter()
    corpora = []
    for label, dataset, mode, n, seed, src in CORPORA:
        result = run_corpus(label, dataset, mode, n, seed, args.k)
        result["between_seed"] = between_seed_sd(src, label)
        corpora.append(result)

    wall = round(time.perf_counter() - t0, 1)
    payload = {
        "generator": f"ollama:{gen.OLLAMA_MODEL}",
        "k": args.k,
        "wall_clock_sec": wall,
        "note": (
            "Between-generation SD: k independent summaries on one fixed sample "
            "(seed 7). Between-seed SD: transcribed from the committed five-seed "
            "aggregates (AIT from results/all, GUIDE from results/all_n120)."
        ),
        "corpora": corpora,
    }
    out_json = os.path.join(OUT, "variance.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    lines = [
        f"# Variance decomposition ({payload['generator']}, k={args.k})",
        "",
        payload["note"],
        "",
        f"Wall-clock: {wall}s",
        "",
        "| Corpus | n alerts | between-gen SD C2 | between-seed SD C2 | "
        "between-gen SD gated | between-seed SD gated |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for c in corpora:
        bg, bs = c["between_generation"], c["between_seed"]
        lines.append(
            f"| {c['label']} | {c['n_alerts']} | "
            f"{bg['C2_emitted_clean_pct_sd']} | {bs['C2_emitted_clean_pct_sd']} | "
            f"{bg['gated_to_review_pct_sd']} | {bs['gated_to_review_pct_sd']} |"
        )
    lines.append("")
    out_md = os.path.join(OUT, "summary.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[variance] wrote {out_json} and {out_md} ({wall}s)", flush=True)
    print(f"WALL_CLOCK_SEC {wall}", flush=True)


if __name__ == "__main__":
    main()
