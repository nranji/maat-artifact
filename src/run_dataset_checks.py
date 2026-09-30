"""Deterministic full-corpus checks for MAAT Tables 1 and 2. No LLM.

  python3 src/run_dataset_checks.py --e1-full

Writes results/all/dataset_checks.json and prints paste-ready Markdown and LaTeX.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter

import nlip_soc as core
from datasets import ait_ads, guide
from paths import DATA, RESULTS

AIT_ZIP = os.path.join(DATA, "ait_ads", "alerts_csv.zip")
GUIDE_FILES = [
    ("train", os.path.join(DATA, "guide", "GUIDE_Train.csv")),
    ("test", os.path.join(DATA, "guide", "GUIDE_Test.csv")),
]
OUT = os.path.join(RESULTS, "all", "dataset_checks.json")


def _pct(x, n):
    return round(100.0 * x / n, 1) if n else 0.0


def _comma(n):
    return f"{n:,}"


def _raise_csv_limit():
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = int(limit / 10)


def _row_dict(header, values):
    if len(values) < len(header):
        values = values + [""] * (len(header) - len(values))
    elif len(values) > len(header):
        values = values[: len(header)]
    return dict(zip(header, values))


def scan_guide(path, label):
    """One pass: E1 validity + Table-1 statistics. Streams with csv.reader."""
    _raise_csv_limit()
    valid = total = unk_fields = key_fields = 0
    grades = Counter()
    entity_types = set()
    categories = set()
    suspicion_nonempty = 0
    n_cols = 0
    t0 = time.perf_counter()
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        n_cols = len(header)
        lower = {h.lower(): h for h in header}
        sus_key = lower.get("suspicionlevel")
        grade_key = lower.get("incidentgrade") or lower.get("grade")
        et_key = lower.get("entitytype")
        cat_key = lower.get("category")
        for values in reader:
            row = _row_dict(header, values)
            item = guide._row_item(row, lower)
            ev = guide.adapt_guide(item["native"])
            ok = core.is_valid_ocsf(ev)
            unk = core.canonical_unknown_fields(ev)
            total += 1
            valid += int(ok)
            key_fields += 4
            unk_fields += len(unk)

            g = (row.get(grade_key) or "").strip() if grade_key else ""
            grades[g if g and g.lower() not in ("nan", "none") else ""] += 1
            et = (row.get(et_key) or "").strip() if et_key else ""
            if et and et.lower() not in ("nan", "none"):
                entity_types.add(et)
            cat = (row.get(cat_key) or "").strip() if cat_key else ""
            if cat and cat.lower() not in ("nan", "none"):
                categories.add(cat)
            sus = (row.get(sus_key) or "").strip() if sus_key else ""
            if sus and sus.lower() not in ("nan", "none"):
                suspicion_nonempty += 1

            if total % 1_000_000 == 0:
                elapsed = time.perf_counter() - t0
                print(f"[guide {label}] {total:,} rows  "
                      f"valid={_pct(valid, total)}%  "
                      f"unk={_pct(unk_fields, key_fields)}%  "
                      f"elapsed={elapsed:.0f}s", flush=True)
    return {
        "split": label,
        "path": path,
        "n": total,
        "n_columns": n_cols,
        "valid_ocsf": valid,
        "valid_ocsf_pct": _pct(valid, total),
        "unknown_fields": unk_fields,
        "unknown_field_rate_pct": _pct(unk_fields, key_fields),
        "incident_grade": dict(grades),
        "entity_types": sorted(entity_types),
        "n_entity_types": len(entity_types),
        "n_categories": len(categories),
        "categories": sorted(categories),
        "suspicion_nonempty": suspicion_nonempty,
        "suspicion_coverage_pct": _pct(suspicion_nonempty, total),
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }


def merge_guide(parts):
    n = sum(p["n"] for p in parts)
    valid = sum(p["valid_ocsf"] for p in parts)
    unk = sum(p["unknown_fields"] for p in parts)
    grades = Counter()
    entities = set()
    sus = 0
    cats = 0  # summed only after union below
    for p in parts:
        grades.update(p["incident_grade"])
        entities.update(p["entity_types"])
        sus += p["suspicion_nonempty"]
    # categories are per-split sets; caller passes union via n_categories_union
    return {
        "n": n,
        "n_columns": parts[0]["n_columns"] if parts else 0,
        "valid_ocsf": valid,
        "valid_ocsf_pct": _pct(valid, n),
        "unknown_fields": unk,
        "unknown_field_rate_pct": _pct(unk, n * 4),
        "incident_grade": dict(grades),
        "entity_types": sorted(entities),
        "n_entity_types": len(entities),
        "suspicion_nonempty": sus,
        "suspicion_coverage_pct": _pct(sus, n),
        "by_split": {p["split"]: {"n": p["n"],
                                  "valid_ocsf_pct": p["valid_ocsf_pct"],
                                  "unknown_field_rate_pct": p["unknown_field_rate_pct"],
                                  "n_columns": p["n_columns"],
                                  "n_entity_types": p["n_entity_types"],
                                  "n_categories": p["n_categories"],
                                  "suspicion_coverage_pct": p["suspicion_coverage_pct"],
                                  "incident_grade": p["incident_grade"],
                                  "elapsed_s": p["elapsed_s"]}
                     for p in parts},
    }


def grade_pcts(grades, n):
    def c(*names):
        return sum(grades.get(k, 0) for k in names)
    tp = c("TruePositive", "True Positive")
    bp = c("BenignPositive", "Benign Positive")
    fp = c("FalsePositive", "False Positive")
    blank = grades.get("", 0)
    other = n - tp - bp - fp - blank
    return {
        "true_positive": {"n": tp, "pct": _pct(tp, n)},
        "benign_positive": {"n": bp, "pct": _pct(bp, n)},
        "false_positive": {"n": fp, "pct": _pct(fp, n)},
        "ungraded": {"n": blank, "pct": _pct(blank, n)},
        "other": {"n": other, "pct": _pct(other, n)},
        "raw": {k if k else "<blank>": v for k, v in grades.items()},
    }


def latex_tables(ait, guide_all, grades):
    w, s, a = (ait["by_detector"][k] for k in ("wazuh", "suricata", "aminer"))
    g_n = guide_all["n"]
    train_n = guide_all["by_split"]["train"]["n"]
    test_n = guide_all["by_split"]["test"]["n"]
    n_et = guide_all["n_entity_types"]
    sus = guide_all["suspicion_coverage_pct"]
    tp, bp, fp, ug = (grades[k]["pct"] for k in
                      ("true_positive", "benign_positive", "false_positive", "ungraded"))
    # Table 1
    t1 = f"""\\begin{{table*}}[t]
\\caption{{Datasets used in the evaluation.}}
\\label{{tab:datasets}}
\\centering
\\small
\\begin{{tabular}}{{@{{}}l p{{6.1cm}} p{{6.6cm}}@{{}}}}
\\toprule
 & \\textbf{{AIT-ADS}}~\\cite{{aitads}} & \\textbf{{GUIDE}}~\\cite{{guide}} \\\\
\\midrule
Records       & {_comma(ait['n_alerts'])} alerts (reduced corpus) & {_comma(g_n)} records ({train_n/1e6:.2f}M train, {test_n/1e6:.2f}M test) \\\\
Sources       & Wazuh (HIDS), Suricata (NIDS), AMiner (anomaly) & Microsoft Defender/Sentinel (SIEM/XDR) \\\\
Fields        & per-detector alert fields mapped to OCSF & {guide_all['n_columns']} columns; {n_et} entity types (IP, user, mailbox, machine, file, URL, cloud logon, \\ldots) across endpoint, identity, email, cloud \\\\
Labels        & attack-phase, recovered by joining on host IP + normalized signature & IncidentGrade: {tp}\\% true-positive, {bp}\\% benign-positive, {fp}\\% false-positive, {ug}\\% ungraded \\\\
Severity      & Wazuh rule levels; \\unk{{}} for Suricata and AMiner & SuspicionLevel populated for {sus}\\% of records; \\unk{{}} otherwise \\\\
Used in E1--E3 & pooled stratified sample, 120 alerts/seed & training-split sample, 40 records/seed \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table*}}"""
    t2 = f"""\\begin{{table}}[t]
\\caption{{Harmonization coverage and OCSF validity (deterministic, no LLM). AIT-ADS is the full reduced corpus; GUIDE is the full train+test release ({_comma(g_n)} records).}}
\\label{{tab:e1}}
\\centering
\\begin{{tabular}}{{lrrr}}
\\toprule
Source & Records & Valid OCSF \\% & \\unk{{}} field \\% \\\\
\\midrule
Wazuh (HIDS)     & {_comma(w['n'])} & {w['valid_pct']} & {w['unknown_field_rate_pct']} \\\\
Suricata (NIDS)  & {_comma(s['n'])} & {s['valid_pct']} & {s['unknown_field_rate_pct']} \\\\
AMiner (anomaly) & {_comma(a['n'])} & {a['valid_pct']} & {a['unknown_field_rate_pct']} \\\\
\\textbf{{AIT-ADS total}} & \\textbf{{{_comma(ait['n_alerts'])}}} & \\textbf{{{ait['valid_ocsf_pct']}}} & {ait['unknown_field_rate_pct']} \\\\
\\midrule
GUIDE (SIEM/XDR) & {_comma(g_n)} & {guide_all['valid_ocsf_pct']} & {guide_all['unknown_field_rate_pct']} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""
    return t1, t2


def markdown_tables(ait, guide_all, grades):
    w, s, a = (ait["by_detector"][k] for k in ("wazuh", "suricata", "aminer"))
    g_n = guide_all["n"]
    train_n = guide_all["by_split"]["train"]["n"]
    test_n = guide_all["by_split"]["test"]["n"]
    tp, bp, fp, ug = (grades[k] for k in
                      ("true_positive", "benign_positive", "false_positive", "ungraded"))
    t1 = f"""## Table 1 — Datasets used in the evaluation

| | AIT-ADS | GUIDE |
|---|---|---|
| Records | {_comma(ait['n_alerts'])} alerts (reduced corpus) | {_comma(g_n)} records ({_comma(train_n)} train, {_comma(test_n)} test) |
| Sources | Wazuh (HIDS), Suricata (NIDS), AMiner (anomaly) | Microsoft Defender/Sentinel (SIEM/XDR) |
| Fields | per-detector alert fields mapped to OCSF | {guide_all['n_columns']} columns; {guide_all['n_entity_types']} entity types |
| Labels | attack-phase, recovered by joining on host IP + normalized signature | IncidentGrade: {tp['pct']}% true-positive ({_comma(tp['n'])}), {bp['pct']}% benign-positive ({_comma(bp['n'])}), {fp['pct']}% false-positive ({_comma(fp['n'])}), {ug['pct']}% ungraded ({_comma(ug['n'])}) |
| Severity | Wazuh rule levels; UNKNOWN for Suricata and AMiner | SuspicionLevel populated for {guide_all['suspicion_coverage_pct']}% of records; UNKNOWN otherwise |
| Used in E1--E3 | pooled stratified sample, 120 alerts/seed | training-split sample, 40 records/seed |
"""
    t2 = f"""## Table 2 — Harmonization coverage and OCSF validity (deterministic, no LLM)

| Source | Records | Valid OCSF % | UNKNOWN field % |
|---|---:|---:|---:|
| Wazuh (HIDS) | {_comma(w['n'])} | {w['valid_pct']} | {w['unknown_field_rate_pct']} |
| Suricata (NIDS) | {_comma(s['n'])} | {s['valid_pct']} | {s['unknown_field_rate_pct']} |
| AMiner (anomaly) | {_comma(a['n'])} | {a['valid_pct']} | {a['unknown_field_rate_pct']} |
| **AIT-ADS total** | **{_comma(ait['n_alerts'])}** | **{ait['valid_ocsf_pct']}** | {ait['unknown_field_rate_pct']} |
| GUIDE (SIEM/XDR) | {_comma(g_n)} | {guide_all['valid_ocsf_pct']} | {guide_all['unknown_field_rate_pct']} |
"""
    return t1, t2


def main():
    ap = argparse.ArgumentParser(description="Full-corpus AIT-ADS + GUIDE OCSF checks.")
    ap.add_argument("--e1-full", action="store_true",
                    help="accepted for compatibility with the README; this script always runs the full-corpus scan")
    ap.parse_args()
    wall0 = time.perf_counter()
    print("[ait] E1-full …", flush=True)
    t0 = time.perf_counter()
    ait = ait_ads.e1_full_csv(AIT_ZIP)
    ait_s = round(time.perf_counter() - t0, 1)
    print(f"[ait] n={ait['n_alerts']:,} valid={ait['valid_ocsf_pct']}% "
          f"unk={ait['unknown_field_rate_pct']}%  elapsed={ait_s}s", flush=True)

    parts = []
    for label, path in GUIDE_FILES:
        print(f"[guide {label}] scanning {path} …", flush=True)
        part = scan_guide(path, label)
        parts.append(part)
        # rescan isn't needed for category union: scan_guide doesn't return the set.
        # n_categories is per-split; union computed below from a second field we stored.
        print(f"[guide {label}] done n={part['n']:,} valid={part['valid_ocsf_pct']}% "
              f"unk={part['unknown_field_rate_pct']}% "
              f"entity_types={part['n_entity_types']} categories={part['n_categories']} "
              f"suspicion={part['suspicion_coverage_pct']}% elapsed={part['elapsed_s']}s",
              flush=True)

    # category union: scan_guide only stored counts. Recompute from stored entity
    # lists is not categories. Store category names in scan — fix by returning them.
    guide_all = merge_guide(parts)
    # n_categories union is not the sum. Attach max as lower bound if we lack the set.
    # scan_guide has the set locally; return it. Patched below via parts if present.
    if all("categories" in p for p in parts):
        cats = set()
        for p in parts:
            cats.update(p["categories"])
        guide_all["n_categories"] = len(cats)
        guide_all["categories"] = sorted(cats)
    else:
        guide_all["n_categories"] = max(p["n_categories"] for p in parts)

    grades = grade_pcts(guide_all["incident_grade"], guide_all["n"])
    # train-only grades (paper currently quotes the training split)
    train = next(p for p in parts if p["split"] == "train")
    grades_train = grade_pcts(train["incident_grade"], train["n"])

    wall = round(time.perf_counter() - wall0, 1)
    payload = {
        "wall_clock_s": wall,
        "ait_elapsed_s": ait_s,
        "ait_ads": {
            "n_alerts": ait["n_alerts"],
            "valid_ocsf_pct": ait["valid_ocsf_pct"],
            "unknown_field_rate_pct": ait["unknown_field_rate_pct"],
            "by_detector": ait["by_detector"],
        },
        "guide": guide_all,
        "guide_incident_grade": grades,
        "guide_incident_grade_train": grades_train,
        "paper_guide_e1_sample_to_replace": {
            "n": 3_000_000,
            "valid_ocsf_pct": 100.0,
            "unknown_field_rate_pct": 46.2,
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    md1, md2 = markdown_tables(ait, guide_all, grades)
    lx1, lx2 = latex_tables(ait, guide_all, grades)
    print("\n" + md1)
    print(md2)
    print(f"Wall-clock: {wall}s ({wall/60:.1f} min)")
    print(f"Wrote {OUT}")
    print("\n--- LaTeX (paste into MAAT_SaTML.tex; not written by this script) ---\n")
    print(lx1)
    print()
    print(lx2)
    # also drop latex next to json for convenience, not into the paper
    tex_out = os.path.join(RESULTS, "all", "dataset_checks_tables.tex")
    with open(tex_out, "w", encoding="utf-8") as f:
        f.write(lx1 + "\n\n" + lx2 + "\n")
    print(f"\nWrote {tex_out}")


if __name__ == "__main__":
    main()
