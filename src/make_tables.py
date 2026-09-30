"""Format run_all.py results into paper-ready tables (Markdown + LaTeX booktabs).

This is a pure formatter: it transcribes the numbers your experiments produced in
results/all/consolidated.json into tables. It performs no analysis and invents no
content; the interpretation is the authors' to write.

Usage:
  python src/make_tables.py
  python src/make_tables.py --json results/all/consolidated.json --out results/all/tables
Outputs <out>.md and <out>.tex.
"""
from __future__ import annotations

import argparse
import json
import os

from paths import RESULTS


def ci(x):
    """Format a {mean, ci95} metric as 'mean [lo, hi]'."""
    if not x or x.get("mean") is None:
        return "--"
    lo, hi = x.get("ci95", [None, None])
    if lo is None:
        return f"{x['mean']}"
    return f"{x['mean']} [{lo}, {hi}]"


def _agg_baseline(configs):
    """Sum LLM-judge vs deterministic leak/over-block counts across seeds, per label."""
    by = {}
    for c in configs:
        b = c.get("baseline_vs_deterministic")
        if not b:
            continue
        d = by.setdefault(c["label"], {"det_leak": 0, "judge_leak": 0,
                                       "det_block": 0, "judge_block": 0, "seeds": 0})
        d["det_leak"] += b["deterministic_gate"]["leaked_unfaithful"]
        d["judge_leak"] += b["llm_judge"]["leaked_unfaithful"]
        d["det_block"] += b["deterministic_gate"]["over_blocked_clean"]
        d["judge_block"] += b["llm_judge"]["over_blocked_clean"]
        d["seeds"] += 1
    return by


def build_markdown(p):
    L = []
    e1f = p.get("e1_full")
    if e1f:
        L += ["### Table: Full-corpus harmonization (E1, deterministic)", "",
              f"Over the entire AIT-ADS reduced corpus: **{e1f['n_alerts']:,}** alerts, "
              f"**{e1f['valid_ocsf_pct']}%** valid OCSF.", "",
              "| Detector | Alerts | Valid OCSF % | UNKNOWN field % |",
              "|---|---:|---:|---:|"]
        for d, v in e1f.get("by_detector", {}).items():
            L.append(f"| {d} | {v['n']:,} | {v['valid_pct']} | {v['unknown_field_rate_pct']} |")
        L.append("")

    agg = p.get("aggregated")
    if agg:
        L += ["### Table: Faithfulness and injection (mean [95% CI] over seeds)", "",
              "_C3 emitted-clean and injection-caught are 100% by construction "
              "(gate definition; non-adaptive injection strings). The empirical "
              "quantities are C1, C2, gated-to-review, and false-block._", "",
              "| Config | C1 raw | C2 grounded | C3 validated | Gated→review % | "
              "Injection caught % | False-block % |",
              "|---|---|---|---|---|---|---|"]
        for a in agg:
            L.append(f"| {a['label']} | {ci(a['E2_C1_emitted_clean_pct'])} | "
                     f"{ci(a['E2_C2_emitted_clean_pct'])} | {ci(a['E2_C3_emitted_clean_pct'])} | "
                     f"{ci(a['E2_gated_to_review_pct'])} | {ci(a['E3_injection_caught_pct'])} | "
                     f"{ci(a['E3_false_block_pct'])} |")
        L += ["", "### Table: Runtime per alert (mean [95% CI])", "",
              "| Config | Summarize ms | Validate ms | Validator overhead % |",
              "|---|---|---|---|"]
        for a in agg:
            L.append(f"| {a['label']} | {ci(a['runtime_summarize_ms'])} | "
                     f"{ci(a['runtime_validate_ms'])} | {ci(a['runtime_validator_overhead_pct'])} |")
        L.append("")

    base = _agg_baseline(p.get("configs", []))
    if base:
        # The reference label is the deterministic checker's own decision, so the
        # gate's leaked/over-blocked are 0 by construction and are NOT reported.
        # This table reports only LLM-judge disagreement with the field-level
        # checker (see paper Sec. "An LLM-as-judge is inconsistent...").
        L += ["### Table: LLM-judge disagreement with the deterministic checker "
              "(totals over seeds)", "",
              "Judge = LLM-as-judge; Checker = deterministic field-level validator. "
              "The gate equals the checker by construction, so it is not a column.",
              "",
              "| Config | Judge faithful, checker flags | "
              "Judge unfaithful, checker clean |",
              "|---|---:|---:|"]
        for lbl, d in base.items():
            L.append(f"| {lbl} | {d['judge_leak']} | {d['judge_block']} |")
        L.append("")
    return "\n".join(L) + "\n"


def _tex_rows(rows):
    return " \\\\\n".join(rows)


def build_latex(p):
    T = ["% Auto-generated from consolidated.json by make_tables.py",
         "% Requires \\usepackage{booktabs}"]
    e1f = p.get("e1_full")
    if e1f:
        body = [f"{d} & {v['n']:,} & {v['valid_pct']} & {v['unknown_field_rate_pct']}"
                for d, v in e1f.get("by_detector", {}).items()]
        T += [r"\begin{table}[t]\centering",
              rf"\caption{{Full-corpus harmonization over all {e1f['n_alerts']:,} AIT-ADS "
              rf"alerts: {e1f['valid_ocsf_pct']}\% valid OCSF.}}",
              r"\begin{tabular}{lrrr}\toprule",
              r"Detector & Alerts & Valid OCSF \% & UNKNOWN \% \\ \midrule",
              _tex_rows(body) + r" \\ \bottomrule",
              r"\end{tabular}\end{table}", ""]

    agg = p.get("aggregated")
    if agg:
        body = [f"{a['label']} & {ci(a['E2_C1_emitted_clean_pct'])} & "
                f"{ci(a['E2_C2_emitted_clean_pct'])} & {ci(a['E2_C3_emitted_clean_pct'])} & "
                f"{ci(a['E2_gated_to_review_pct'])} & {ci(a['E3_injection_caught_pct'])} & "
                f"{ci(a['E3_false_block_pct'])}".replace("[", "{[}").replace("]", "{]}")
                for a in agg]
        T += [r"\begin{table*}[t]\centering",
              r"\caption{Faithfulness and injection robustness (mean [95\% CI] over seeds).}",
              r"\begin{tabular}{lcccccc}\toprule",
              r"Config & C1 raw & C2 grounded & C3 validated & Gated \% & Caught \% & False-block \% \\ \midrule",
              _tex_rows(body) + r" \\ \bottomrule",
              r"\end{tabular}\end{table*}", ""]
    return "\n".join(T) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(RESULTS, "all", "consolidated.json"))
    ap.add_argument("--out", default=os.path.join(RESULTS, "all", "tables"))
    a = ap.parse_args()
    with open(a.json, encoding="utf-8") as f:
        p = json.load(f)
    with open(a.out + ".md", "w", encoding="utf-8") as f:
        f.write(build_markdown(p))
    with open(a.out + ".tex", "w", encoding="utf-8") as f:
        f.write(build_latex(p))
    print(f"wrote {a.out}.md and {a.out}.tex")


if __name__ == "__main__":
    main()
