"""One-command experiment driver for the MAAT paper.

Paper-aligned defaults: one pooled stratified AIT-ADS sample + one GUIDE sample,
with optional multi-seed confidence intervals. Each grounded summary is generated
ONCE and reused for E2, runtime, and the LLM-judge baseline (self-consistent under
a non-deterministic model, and ~3x fewer LLM calls than the previous driver).

Examples
  python src/run_all.py --paper --seeds 7,11,13,17,19   # lean paper run
  python src/run_all.py --e1-full --no-llm-exps         # full-corpus OCSF only
  python src/run_all.py --ait-scenarios all --no-guide  # per-scenario audit (deterministic OK)

With an Ollama server running, grounded summaries come from the real model and
the LLM-judge baseline is computed; otherwise the deterministic generator is used.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import time

import nlip_soc as core
import generators as gen
import run_experiment as R
import baselines
from paths import DATA, RESULTS
ALL_SCENARIOS = ["russellmitchell", "fox", "harrison", "santos",
                 "shaw", "wardbeck", "wheeler", "wilson"]


def _pct(x, n):
    return round(100.0 * x / n, 1) if n else 0.0


def _e2_stats(pairs, gate):
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
            "summaries_with_violation_pct": _pct(with_viol, n),
            "contradiction_count": contra, "unsupported_count": unsup,
            "unknown_violation_count": unkv,
            "mean_field_preservation": round(fp_sum / n, 3) if n else 0.0,
            "gated_to_manual_review_pct": _pct(n - emitted, n) if gate else 0.0,
            "emitted_pct": _pct(emitted, n),
            "emitted_clean_pct": _pct(emitted_clean, emitted) if emitted else 0.0}


def _generate_once(items, adapters, grounded_fn, seed):
    """Adapt + summarize each alert once; time the three stages on that single pass.

    Returns (raw_pairs, grounded_pairs, runtime, grounded_rows) where grounded_pairs
    are (summary, event) and grounded_rows carry the faithfulness result for reuse.
    """
    rng_a = random.Random(seed + 1)
    rng_b = random.Random(seed + 2)
    raw, grounded, rows = [], [], []
    ad = sm = va = 0.0
    for it in items:
        t0 = time.perf_counter()
        ev = adapters[it["detector"]](it["native"])
        t1 = time.perf_counter()
        raw.append((gen.hallucinating(ev, rng_a), ev))
        if grounded_fn is gen.grounded_template:
            g = gen.grounded_template(ev, rng_b, slip_rate=0.15)
        else:
            g = grounded_fn(ev, rng_b)
        t2 = time.perf_counter()
        fr = core.validate_faithfulness(g, ev)
        t3 = time.perf_counter()
        grounded.append((g, ev))
        rows.append({"summary": g, "event": ev, "fr": fr,
                     "detector": it["detector"], "label": it["label"]})
        ad += t1 - t0; sm += t2 - t1; va += t3 - t2
    n = len(items) or 1
    runtime = {"n": len(items),
               "adapt_ms": round(1000 * ad / n, 3),
               "summarize_ms": round(1000 * sm / n, 3),
               "validate_ms": round(1000 * va / n, 3),
               "validator_overhead_pct": round(100 * va / (ad + sm + va), 1)
                                        if (ad + sm + va) else 0.0}
    return raw, grounded, runtime, rows


def _baseline_from_rows_once(rows):
    """Deterministic gate vs LLM-judge on the SAME grounded summaries as E2.

    Calls the judge exactly once per summary. Skips unparseable answers rather
    than treating None as unfaithful.
    """
    if not baselines.llm_judge_available():
        return None
    det_emit, judge, clean = [], [], []
    for row in rows:
        j = baselines.llm_judge_faithful(row["summary"], row["event"])
        if j is None:
            continue
        fr = row["fr"]
        det_emit.append(fr.decision == "EMIT")
        clean.append(not fr.has_violation)
        judge.append(bool(j))
    if not det_emit:
        return None
    return baselines.confusion(det_emit, judge, clean)


def run_config(label, dataset, *, n, seed, scenario=None, mode="auto",
               guide_split="train", data_dir=None, skip_baseline=False,
               out_subdir="all"):
    items, adapters, desc = R.load_dataset(
        dataset, data_dir, n, seed, scenario or "russellmitchell", mode, guide_split)
    out = os.path.join(RESULTS, out_subdir, f"{label}_s{seed}")
    R.OUT = out
    os.makedirs(R.OUT, exist_ok=True)
    use_ollama = gen.ollama_available()
    grounded_fn = gen.ollama_agent if use_ollama else gen.grounded_template
    glabel = (f"ollama:{gen.OLLAMA_MODEL}" if use_ollama
              else "deterministic grounded template")

    e1, _ = R.run_e1(items, adapters)
    raw, grounded, runtime, rows = _generate_once(items, adapters, grounded_fn, seed)
    e2 = {
        "C1_raw_no_grounding_no_validator": _e2_stats(raw, gate=False),
        "C2_canonical_grounded_no_validator": _e2_stats(grounded, gate=False),
        f"C3_canonical_grounded_validated[{glabel}]": _e2_stats(grounded, gate=True),
    }
    # write E2 CSV from the same summaries
    R._write_csv("E2_faithfulness.csv", [
        {"detector": r["detector"], "label": r["label"],
         "grounded_decision": r["fr"].decision,
         "field_preservation": round(r["fr"].field_preservation, 2),
         "violations": len(r["fr"].contradictions) + len(r["fr"].unsupported)
                       + len(r["fr"].unknown_violations),
         "summary": r["summary"]}
        for r in rows])
    e3 = R.run_e3(items, adapters)
    baseline = None if skip_baseline else _baseline_from_rows_once(rows)
    return {
        "label": label, "dataset": dataset, "desc": desc, "seed": seed,
        "n_alerts": len(items), "generator": glabel, "ollama": use_ollama,
        "E1": e1, "E2": e2, "E3": e3,
        "runtime": runtime,
        "baseline_vs_deterministic": baseline,
    }


def build_matrix(args):
    """Configs for one seed. ``--paper`` => pooled AIT + GUIDE (not per-scenario)."""
    cfgs = []
    if args.paper:
        if not args.no_synthetic:
            cfgs.append(dict(label="synthetic", dataset="synthetic", n=args.n))
        if not args.no_ait:
            cfgs.append(dict(label="ait_csv_pooled", dataset="ait_ads", n=args.n,
                             mode="csv_pooled"))
            if args.ait_raw:
                cfgs.append(dict(label="ait_raw_pooled", dataset="ait_ads", n=args.n,
                                 mode="raw_pooled"))
        if not args.no_guide:
            cfgs.append(dict(label="guide_train", dataset="guide", n=args.n,
                             guide_split="train"))
        return cfgs

    if not args.no_synthetic:
        cfgs.append(dict(label="synthetic", dataset="synthetic", n=args.n))
    scenarios = ALL_SCENARIOS if args.ait_scenarios == "all" else (
        [] if args.ait_scenarios in ("none", "pooled") else args.ait_scenarios.split(","))
    if args.ait_scenarios == "pooled":
        cfgs.append(dict(label="ait_csv_pooled", dataset="ait_ads", n=args.n,
                         mode="csv_pooled"))
        if args.ait_raw:
            cfgs.append(dict(label="ait_raw_pooled", dataset="ait_ads", n=args.n,
                             mode="raw_pooled"))
    else:
        for sc in scenarios:
            cfgs.append(dict(label=f"ait_csv_{sc}", dataset="ait_ads", n=args.n,
                             scenario=sc, mode="csv"))
            if args.ait_raw:
                cfgs.append(dict(label=f"ait_raw_{sc}", dataset="ait_ads", n=args.n,
                                 scenario=sc, mode="raw"))
    if not args.no_guide:
        cfgs.append(dict(label="guide_train", dataset="guide", n=args.n,
                         guide_split="train"))
    return cfgs


def _ci95(vals):
    if not vals:
        return {"mean": None, "std": None, "ci95": None, "n": 0}
    m = statistics.mean(vals)
    if len(vals) < 2:
        return {"mean": round(m, 2), "std": 0.0, "ci95": [round(m, 2), round(m, 2)], "n": 1}
    sd = statistics.stdev(vals)
    # normal approx 95% CI; clamp the lower bound to 0 (all metrics are non-negative
    # rates or latencies, so a negative bound from the normal approx is meaningless).
    se = sd / math.sqrt(len(vals))
    lo = max(0.0, m - 1.96 * se)
    return {"mean": round(m, 2), "std": round(sd, 2),
            "ci95": [round(lo, 2), round(m + 1.96 * se, 2)], "n": len(vals)}


def aggregate_seeds(runs):
    """Group runs by label and report mean±CI for the paper metrics."""
    by = {}
    for r in runs:
        by.setdefault(r["label"], []).append(r)
    out = []
    for label, rs in by.items():
        def take(path):
            vals = []
            for r in rs:
                cur = r
                for p in path:
                    if cur is None:
                        break
                    if isinstance(cur, dict):
                        # C3 key varies by generator label
                        if p == "C3":
                            k = next((x for x in cur if x.startswith("C3")), None)
                            cur = cur.get(k) if k else None
                        else:
                            cur = cur.get(p)
                    else:
                        cur = None
                if isinstance(cur, (int, float)):
                    vals.append(float(cur))
            return _ci95(vals)

        e2 = rs[0]["E2"]
        c3k = next(k for k in e2 if k.startswith("C3"))
        out.append({
            "label": label,
            "n_seeds": len(rs),
            "generator": rs[0]["generator"],
            "n_alerts": rs[0]["n_alerts"],
            "E1_valid_ocsf_pct": take(["E1", "valid_ocsf_pct"]),
            "E1_unknown_field_rate_pct": take(["E1", "unknown_field_rate_pct"]),
            "E2_C1_emitted_clean_pct": take(["E2", "C1_raw_no_grounding_no_validator",
                                             "emitted_clean_pct"]),
            "E2_C2_emitted_clean_pct": take(["E2", "C2_canonical_grounded_no_validator",
                                             "emitted_clean_pct"]),
            "E2_C3_emitted_clean_pct": take(["E2", "C3", "emitted_clean_pct"]),
            "E2_gated_to_review_pct": take(["E2", "C3", "gated_to_manual_review_pct"]),
            "E3_injection_caught_pct": take(["E3", "injection_caught_pct"]),
            "E3_false_block_pct": take(["E3", "false_block_pct"]),
            "runtime_summarize_ms": take(["runtime", "summarize_ms"]),
            "runtime_validate_ms": take(["runtime", "validate_ms"]),
            "runtime_validator_overhead_pct": take(["runtime", "validator_overhead_pct"]),
            "c3_key": c3k,
        })
    return out


def emit_markdown(results, path, *, e1_full=None, aggregated=None):
    L = ["# MAAT experiment results", ""]
    gen_used = results[0]["generator"] if results else "n/a"
    L += [f"Generator: **{gen_used}**  ·  runs: {len(results)}", ""]

    if e1_full:
        L += ["## E1-full — full-corpus OCSF validity (deterministic, no LLM)", "",
              f"Alerts: **{e1_full['n_alerts']:,}**  ·  "
              f"Valid OCSF: **{e1_full['valid_ocsf_pct']}%**  ·  "
              f"UNKNOWN field rate: {e1_full['unknown_field_rate_pct']}%", ""]
        L += ["| Detector | n | Valid % | UNKNOWN field % |", "|---|---|---|---|"]
        for d, v in e1_full.get("by_detector", {}).items():
            L.append(f"| {d} | {v['n']:,} | {v['valid_pct']} | {v['unknown_field_rate_pct']} |")
        L.append("")

    if aggregated:
        L += ["## Multi-seed summary (mean [95% CI])", "",
              "| Config | C1 raw | C2 grounded | C3 validated | gated→review % | "
              "E3 caught % | False-block % |",
              "|---|---|---|---|---|---|---|"]
        for a in aggregated:
            def fmt(x):
                if not x or x["mean"] is None:
                    return "—"
                lo, hi = x["ci95"]
                return f"{x['mean']} [{lo}, {hi}]"
            L.append(
                f"| {a['label']} | {fmt(a['E2_C1_emitted_clean_pct'])} | "
                f"{fmt(a['E2_C2_emitted_clean_pct'])} | {fmt(a['E2_C3_emitted_clean_pct'])} | "
                f"{fmt(a['E2_gated_to_review_pct'])} | {fmt(a['E3_injection_caught_pct'])} | "
                f"{fmt(a['E3_false_block_pct'])} |")
        L.append("")

    L += ["## E1 — harmonization coverage & schema validity", "",
          "| Config | Seed | Alerts | Valid OCSF % | UNKNOWN field % |",
          "|---|---|---|---|---|"]
    for r in results:
        e1 = r["E1"]
        L.append(f"| {r['label']} | {r.get('seed', '')} | {e1['n_alerts']} | "
                 f"{e1['valid_ocsf_pct']} | {e1['unknown_field_rate_pct']} |")

    L += ["", "## E2 — faithfulness (emitted-clean rate)", "",
          "_C3 emitted-clean is 100% by construction of the gate; the empirical "
          "quantities are C1, C2, and gated-to-review._", "",
          "| Config | Seed | C1 raw | C2 grounded | C3 validated | gated→review % |",
          "|---|---|---|---|---|---|"]
    for r in results:
        e2 = r["E2"]
        c1 = e2["C1_raw_no_grounding_no_validator"]["emitted_clean_pct"]
        c2 = e2["C2_canonical_grounded_no_validator"]["emitted_clean_pct"]
        c3k = next(k for k in e2 if k.startswith("C3"))
        c3 = e2[c3k]["emitted_clean_pct"]
        gated = e2[c3k]["gated_to_manual_review_pct"]
        L.append(f"| {r['label']} | {r.get('seed', '')} | {c1} | {c2} | {c3} | {gated} |")

    L += ["", "## E3 — injection robustness", "",
          "| Config | Seed | Poisoned | Caught % | False-block % |",
          "|---|---|---|---|---|"]
    for r in results:
        e3 = r["E3"]
        L.append(f"| {r['label']} | {r.get('seed', '')} | {e3['n_poisoned']} | "
                 f"{e3['injection_caught_pct']} | {e3['false_block_pct']} |")

    L += ["", "## Runtime (per alert; summarize timed on the single generation pass)", "",
          "| Config | Seed | adapt ms | summarize ms | validate ms | validator overhead % |",
          "|---|---|---|---|---|---|"]
    for r in results:
        rt = r["runtime"]
        if rt:
            L.append(f"| {r['label']} | {r.get('seed', '')} | {rt['adapt_ms']} | "
                     f"{rt['summarize_ms']} | {rt['validate_ms']} | "
                     f"{rt['validator_overhead_pct']} |")

    if any(r.get("baseline_vs_deterministic") for r in results):
        # NOTE: the reference label ("truly_clean") is the deterministic checker's
        # OWN decision, so the deterministic gate agrees with it by construction
        # (its leaked/over-blocked are 0 by definition and are NOT reported as a
        # result). This table therefore reports only where the LLM judge DISAGREES
        # with the field-level checker, matching the paper's framing. An independent
        # (human) reference is required for any gate-vs-judge superiority claim.
        L += ["", "## LLM-judge disagreement with the deterministic field-level checker",
              "",
              "Judge = LLM-as-judge; Checker = deterministic field-level validator. "
              "The gate equals the checker by construction, so it is not a column.",
              "",
              "| Config | Seed | Judge faithful, checker flags | "
              "Judge unfaithful, checker clean |",
              "|---|---|---|---|"]
        for r in results:
            b = r.get("baseline_vs_deterministic")
            if b:
                j = b["llm_judge"]
                L.append(f"| {r['label']} | {r.get('seed', '')} | "
                         f"{j['leaked_unfaithful']} | {j['over_blocked_clean']} |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description="MAAT full experiment driver.")
    ap.add_argument("--n", type=int, default=40,
                    help="alerts per detector (total for GUIDE)")
    ap.add_argument("--seed", type=int, default=7,
                    help="single seed (ignored if --seeds is set)")
    ap.add_argument("--seeds", default=None,
                    help="comma-separated seeds for mean±CI (e.g. 7,11,13,17,19)")
    ap.add_argument("--paper", action="store_true",
                    help="lean paper matrix: pooled AIT-ADS + GUIDE (+ synthetic)")
    ap.add_argument("--ait-scenarios", default="russellmitchell",
                    help="'all', 'none', 'pooled', or comma-separated names")
    ap.add_argument("--ait-raw", action="store_true",
                    help="also run AIT-ADS raw (or raw_pooled under --paper)")
    ap.add_argument("--no-synthetic", action="store_true")
    ap.add_argument("--no-guide", action="store_true")
    ap.add_argument("--no-ait", action="store_true")
    ap.add_argument("--e1-full", action="store_true",
                    help="stream all AIT-ADS CSV alerts for full-corpus OCSF validity")
    ap.add_argument("--no-llm-exps", action="store_true",
                    help="skip E1/E2/E3 sample runs (use with --e1-full)")
    ap.add_argument("--skip-baseline", action="store_true",
                    help="skip LLM-judge baseline (halves remaining LLM calls)")
    ap.add_argument("--out", default="all",
                    help="results subdirectory under results/ (default: all). "
                         "Use a distinct name for a second-model run.")
    args = ap.parse_args()

    out_dir = os.path.join(RESULTS, args.out)
    os.makedirs(out_dir, exist_ok=True)

    e1_full = None
    if args.e1_full:
        from datasets import ait_ads
        zip_path = os.path.join(DATA, "ait_ads", "alerts_csv.zip")
        print(f"[run_all] E1-full over {zip_path} …", flush=True)
        e1_full = ait_ads.e1_full_csv(zip_path)
        print(f"[run_all] E1-full: n={e1_full['n_alerts']:,} "
              f"valid={e1_full['valid_ocsf_pct']}%", flush=True)

    results = []
    if not args.no_llm_exps:
        seeds = ([int(s) for s in args.seeds.split(",")] if args.seeds
                 else [args.seed])
        # under --paper, default ait mode is pooled even if --ait-scenarios left default
        if args.paper and args.ait_scenarios == "russellmitchell":
            args.ait_scenarios = "pooled"
        for seed in seeds:
            for cfg in build_matrix(args):
                cfg = dict(cfg)
                cfg["seed"] = seed
                cfg["skip_baseline"] = args.skip_baseline
                cfg["out_subdir"] = args.out
                print(f"[run_all] {cfg['label']} seed={seed} …", flush=True)
                try:
                    results.append(run_config(**cfg))
                except Exception as e:
                    print(f"[run_all]   FAILED {cfg['label']} seed={seed}: {e}",
                          flush=True)

    aggregated = aggregate_seeds(results) if results and args.seeds else None
    payload = {
        "generator": results[0]["generator"] if results else "n/a",
        "ollama": gen.ollama_available(),
        "e1_full": e1_full,
        "aggregated": aggregated,
        "configs": results,
    }
    with open(os.path.join(out_dir, "consolidated.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    emit_markdown(results, os.path.join(out_dir, "summary.md"),
                  e1_full=e1_full, aggregated=aggregated)
    print(f"[run_all] wrote {out_dir}/consolidated.json and summary.md "
          f"({len(results)} runs)", flush=True)


if __name__ == "__main__":
    main()
