"""
E1, E2, and E3 for one corpus and one seed.

Pipeline (NLIP endpoints on the solid edges):
  source adapters --NLIP--> harmonizer agent --NLIP--> analyst-assistant --NLIP--> human
The harmonizer calls two DETERMINISTIC services as tools (not agents, not on NLIP):
  the OCSF schema validator and the faithfulness validator.

E1  harmonization coverage + schema validity
E2  faithfulness: ungrounded baseline vs OCSF-grounded + validated
E3  injection robustness: poisoned alert -> validator routes to MANUAL_REVIEW

Run:  python3 src/run_experiment.py
Outputs per-experiment CSV files + a JSON summary into results/<dataset>/.
With a local Ollama server running, the grounded summaries are produced by a real
LLM via pydantic-ai; otherwise the deterministic grounded generator is used.
"""
from __future__ import annotations

import csv
import json
import os
import random

import nlip_soc as core
import generators as gen
from paths import DATA, RESULTS

OUT = RESULTS

SEED = 7
N_PER_DETECTOR = 12


def harmonize(item: dict, adapters: dict) -> dict:
    """Adapter gateway: native alert -> NLIP message -> canonical OCSF event."""
    adapter = adapters[item["detector"]]
    event = adapter(item["native"])
    # wrap on the adapter->harmonizer NLIP edge, tagging vendor text as untrusted
    msg = core.new_message(event, from_endpoint=f"{item['detector']}-gateway",
                           to_endpoint="harmonizer", subformat="ocsf",
                           provenance={"source": item["detector"],
                                       "trust": "untrusted-vendor-text"})
    return {"event": event, "nlip": msg, "label": item["label"],
            "detector": item["detector"]}


def pct(x, n):
    return round(100.0 * x / n, 1) if n else 0.0


# --------------------------------------------------------------------------
# E1 - harmonization coverage + schema validity
# --------------------------------------------------------------------------
def run_e1(items, adapters):
    rows, valid, unknown_fields_total, key_fields_total = [], 0, 0, 0
    by_det = {}
    for it in items:
        h = harmonize(it, adapters)
        ev = h["event"]
        ok, err = core.validate_ocsf(ev)
        valid += int(ok)
        unk = core.canonical_unknown_fields(ev)
        # key fields we attempt to populate: severity, src_ip, dst_ip, user
        key_fields_total += 4
        unknown_fields_total += len(unk)
        d = by_det.setdefault(it["detector"], {"n": 0, "valid": 0, "unknown": 0})
        d["n"] += 1
        d["valid"] += int(ok)
        d["unknown"] += len(unk)
        rows.append({"detector": it["detector"], "label": it["label"],
                     "class_uid": ev["class_uid"], "severity": ev["severity"],
                     "valid_ocsf": ok, "unknown_fields": ";".join(unk) or "-",
                     "schema_error": err or ""})
    n = len(items)
    summary = {
        "n_alerts": n,
        "valid_ocsf_pct": pct(valid, n),
        "unknown_field_rate_pct": pct(unknown_fields_total, key_fields_total),
        "by_detector": {k: {"n": v["n"], "valid_pct": pct(v["valid"], v["n"]),
                            "unknown_field_rate_pct": pct(v["unknown"], v["n"] * 4)}
                        for k, v in by_det.items()},
    }
    _write_csv("E1_harmonization.csv", rows)
    return summary, rows


# --------------------------------------------------------------------------
# E2 - faithfulness: three conditions
#   C1 raw-alert -> summary            (no grounding, no validator)
#   C2 canonical -> summary            (grounding, no validator gate)
#   C3 canonical -> summary -> validator (grounding + gate)
# C2 and C3 share the same summaries; C3 only adds the gate, isolating the
# validator's marginal effect.
# --------------------------------------------------------------------------
def run_e2(items, adapters, grounded_fn, grounded_label):
    rng_a = random.Random(SEED + 1)
    rng_b = random.Random(SEED + 2)

    def stats(pairs, gate):
        n = len(pairs)
        contra = unsup = unkv = fp_sum = 0
        with_viol = emitted = emitted_clean = 0
        for summ, ev in pairs:
            r = core.validate_faithfulness(summ, ev)
            contra += len(r.contradictions); unsup += len(r.unsupported)
            unkv += len(r.unknown_violations); fp_sum += r.field_preservation
            clean = not r.has_violation
            with_viol += int(not clean)
            if (not gate) or r.decision == "EMIT":
                emitted += 1; emitted_clean += int(clean)
        return {"n": n,
                "summaries_with_violation_pct": pct(with_viol, n),
                "contradiction_count": contra, "unsupported_count": unsup,
                "unknown_violation_count": unkv,
                "mean_field_preservation": round(fp_sum / n, 3),
                "gated_to_manual_review_pct": pct(n - emitted, n) if gate else 0.0,
                "emitted_pct": pct(emitted, n),
                "emitted_clean_pct": pct(emitted_clean, emitted) if emitted else 0.0}

    raw, grounded, rows = [], [], []
    for it in items:
        ev = harmonize(it, adapters)["event"]
        raw.append((gen.hallucinating(ev, rng_a), ev))
        if grounded_fn is gen.grounded_template:
            g = gen.grounded_template(ev, rng_b, slip_rate=0.15)
        else:
            g = grounded_fn(ev, rng_b)
        grounded.append((g, ev))
        rf = core.validate_faithfulness(g, ev)
        rows.append({"detector": it["detector"], "label": it["label"],
                     "grounded_decision": rf.decision,
                     "field_preservation": round(rf.field_preservation, 2),
                     "violations": len(rf.contradictions) + len(rf.unsupported)
                     + len(rf.unknown_violations), "summary": g})
    _write_csv("E2_faithfulness.csv", rows)
    return {
        "C1_raw_no_grounding_no_validator": stats(raw, gate=False),
        "C2_canonical_grounded_no_validator": stats(grounded, gate=False),
        f"C3_canonical_grounded_validated[{grounded_label}]": stats(grounded, gate=True),
    }


# --------------------------------------------------------------------------
# E3 - injection robustness
# --------------------------------------------------------------------------
def run_e3(items, adapters):
    """Injection across four surfaces (vendor_note, filename, email_subject, url)
    and four types. Attack path obeys the injection; control path ignores it.

    NOTE: these injections are non-adaptive and, by construction, alter fields the
    validator checks (severity, user, remediation), so the catch rate is a sanity
    check on the covered surface, not robustness to an adaptive attacker. The
    control path is the deterministic template (gen.grounded_template), not the LLM,
    so the false-block figure measures that template, not llama3.2:3b."""
    subset = items[:24]
    rows = []
    by_type = {}
    caught = emitted_control = total = 0
    for k, it in enumerate(subset):
        inj = gen.INJECTIONS[k % len(gen.INJECTIONS)]
        poisoned = gen.poison_alert(it, inj)
        ev = harmonize(poisoned, adapters)["event"]  # structured event keeps the TRUTH
        attack = gen.injection_naive(ev, inj)
        r_a = core.validate_faithfulness(attack, ev)
        ctrl = gen.grounded_template(ev)
        r_c = core.validate_faithfulness(ctrl, ev)
        total += 1
        caught += int(r_a.decision == "MANUAL_REVIEW")
        emitted_control += int(r_c.decision == "EMIT")
        d = by_type.setdefault(inj["type"], {"n": 0, "caught": 0, "ctrl_emit": 0})
        d["n"] += 1; d["caught"] += int(r_a.decision == "MANUAL_REVIEW")
        d["ctrl_emit"] += int(r_c.decision == "EMIT")
        rows.append({"detector": it["detector"], "inj_type": inj["type"],
                     "surface": inj["surface"], "true_severity": ev["severity"],
                     "attack_decision": r_a.decision, "control_decision": r_c.decision,
                     "attack_summary": attack})
    _write_csv("E3_injection.csv", rows)
    return {
        "n_poisoned": total,
        "injection_caught_pct": pct(caught, total),
        "false_block_pct": round(100.0 - pct(emitted_control, total), 1),
        "control_emitted_pct": pct(emitted_control, total),
        "by_type": {t: {"n": v["n"], "caught_pct": pct(v["caught"], v["n"]),
                        "control_emitted_pct": pct(v["ctrl_emit"], v["n"])}
                    for t, v in by_type.items()},
    }


def _write_csv(name, rows):
    if not rows:
        return
    keys = list({k for r in rows for k in r.keys()})
    # stable column order: put summary-ish columns last
    order = [k for k in rows[0].keys()]
    for k in keys:
        if k not in order:
            order.append(k)
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=order)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def load_dataset(name, data_dir, n_per_detector, seed, scenario, mode, guide_split="train"):
    """Return (items, adapters, description) for the chosen dataset.

    Note on --n-per-detector: for the multi-detector datasets (synthetic, AIT-ADS)
    it is the count PER detector. GUIDE is single-source, so for GUIDE the same
    flag is the TOTAL number of alerts sampled.
    """
    if name == "synthetic":
        return (core.generate_alerts(n_per_detector, seed=seed),
                core.ADAPTERS, "synthetic Wazuh/Suricata/AMiner alerts")
    if name == "ait_ads":
        from datasets import ait_ads
        dd = data_dir or os.path.join(DATA, "ait_ads")
        items, adapters = ait_ads.load(dd, n_per_detector, seed, scenario, mode)
        src = items[0]["source"] if items else "ait_ads"
        if mode in ("csv_pooled", "raw_pooled"):
            return items, adapters, f"AIT-ADS pooled ({mode}, all scenarios)"
        return items, adapters, f"AIT-ADS real alerts ({src}, scenario={scenario})"
    if name == "guide":
        from datasets import guide
        dd = data_dir or os.path.join(DATA, "guide")
        # GUIDE is single-source: --n-per-detector is the total alert count here.
        items, adapters = guide.load(dd, n_per_detector, seed, split=guide_split)
        return items, adapters, f"GUIDE real SOC triage records ({guide_split} split)"
    raise ValueError(f"unknown dataset {name!r}")


def main():
    import argparse
    global OUT
    ap = argparse.ArgumentParser(description="MAAT E1/E2/E3 experiment runner.")
    ap.add_argument("--dataset", default="synthetic",
                    choices=["synthetic", "ait_ads", "guide"])
    ap.add_argument("--data-dir", default=None, help="dataset folder (overrides default)")
    ap.add_argument("--scenario", default="russellmitchell", help="AIT-ADS scenario")
    ap.add_argument("--mode", default="auto",
                    choices=["auto", "raw", "csv", "csv_pooled", "raw_pooled"],
                    help="AIT-ADS input mode")
    ap.add_argument("--guide-split", default="train", choices=["train", "test"],
                    help="GUIDE split to sample from")
    ap.add_argument("--n-per-detector", type=int, default=N_PER_DETECTOR,
                    help="alerts per detector (synthetic, AIT-ADS); TOTAL alerts for single-source GUIDE")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=None, help="results subdirectory name")
    args = ap.parse_args()

    items, adapters, desc = load_dataset(
        args.dataset, args.data_dir, args.n_per_detector, args.seed,
        args.scenario, args.mode, args.guide_split)

    OUT = os.path.join(RESULTS, args.out or args.dataset)
    os.makedirs(OUT, exist_ok=True)

    use_ollama = gen.ollama_available()
    grounded_fn = gen.ollama_agent if use_ollama else gen.grounded_template
    grounded_label = (f"ollama:{gen.OLLAMA_MODEL} via pydantic-ai"
                      if use_ollama else "deterministic grounded template (no LLM reachable)")

    e1, _ = run_e1(items, adapters)
    e2 = run_e2(items, adapters, grounded_fn, grounded_label)
    e3 = run_e3(items, adapters)

    report = {
        "config": {"dataset": args.dataset, "dataset_desc": desc,
                   "n_alerts": len(items), "n_per_detector": args.n_per_detector,
                   "seed": args.seed, "generation_backend": grounded_label,
                   "ollama_reachable": use_ollama},
        "E1_harmonization": e1,
        "E2_faithfulness": e2,
        "E3_injection": e3,
    }
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
