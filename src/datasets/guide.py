"""GUIDE loader: Microsoft SOC triage records -> canonical OCSF.

GUIDE (Freitas et al., "AI-Driven Guided Response for SOCs with Microsoft Copilot
for Security", arXiv:2407.09017) is a large table of real SOC alert evidence with
triage labels. Unlike AIT-ADS it is not multi-detector IDS output; each row is a
piece of alert/incident evidence with an ``IncidentGrade`` label
(TruePositive / BenignPositive / FalsePositive) and typed entity columns.

We map each row to an OCSF Detection Finding, preserving the alert title, category,
entities (IP, account, URL, file), MITRE techniques, and the triage grade. The
grade drives the benign/attack label; it is never used to classify (MAAT does not
classify) but lets us stratify the faithfulness results.

The GUIDE column set varies between releases, so the loader maps columns
case-insensitively and treats anything missing as UNKNOWN. Point ``data_dir`` at a
folder holding the GUIDE CSV (e.g. ``GUIDE_Train.csv``).
"""
from __future__ import annotations

import csv
import glob
import os
import random
from typing import Optional

import nlip_soc as core

SEV_TEXT = {"informational": 1, "info": 1, "low": 2, "medium": 3, "moderate": 3,
            "high": 4, "critical": 5, "fatal": 6,
            # GUIDE has no Severity column; it exposes SuspicionLevel instead.
            "suspicious": 3, "incriminated": 4}


def _first(row: dict, *names, lower: Optional[dict] = None):
    """Return the first non-empty value among the given column names (case-insensitive)."""
    for n in names:
        for key in (n, n.lower(), n.upper()):
            if key in row and str(row[key]).strip() not in ("", "nan", "None"):
                return str(row[key]).strip()
        if lower is not None:
            k = lower.get(n.lower())
            if k and str(row.get(k, "")).strip() not in ("", "nan", "None"):
                return str(row[k]).strip()
    return None


def _grade_label(grade: Optional[str]) -> str:
    g = (grade or "").replace(" ", "").lower()
    return "attack" if g.startswith("truepositive") else "benign"


def adapt_guide(a: dict) -> dict:
    sev = a.get("severity_text")
    sid = SEV_TEXT.get((sev or "").lower(), 0)
    return core._canonical(
        product="Microsoft 365 Defender (GUIDE)",
        product_uid=a.get("uid") or core.UNKNOWN,
        title=a.get("title") or core.UNKNOWN,
        time=a.get("time_iso") or core.UNKNOWN,
        severity_id=sid,
        src_ip=a.get("src_ip") or core.UNKNOWN,
        src_port=None,
        dst_ip=core.UNKNOWN,
        dst_port=None,
        user=a.get("user") or core.UNKNOWN,
        message=a.get("message") or a.get("title") or core.UNKNOWN,
        unmapped={"category": a.get("category"), "mitre": a.get("mitre"),
                  "entity_type": a.get("entity_type"), "grade": a.get("grade"),
                  **core._surfaces(a)},
        raw=a.get("raw", a),
    )


ADAPTERS = {"guide": adapt_guide}


def _row_item(row: dict, lower: dict) -> dict:
    category = _first(row, "Category", lower=lower)
    # GUIDE anonymizes AlertTitle to an integer id, so prefer the readable Category
    # as the finding title and keep the numeric title id as metadata.
    alert_title_id = _first(row, "AlertTitle", "Title", lower=lower)
    title = category or alert_title_id or core.UNKNOWN
    grade = _first(row, "IncidentGrade", "Grade", lower=lower)
    native = {
        "detector": "guide",
        "title": title,
        "uid": _first(row, "AlertId", "Id", "IncidentId", lower=lower) or core.UNKNOWN,
        "time_iso": _first(row, "Timestamp", "Time", lower=lower) or core.UNKNOWN,
        "severity_text": _first(row, "Severity", "AlertSeverity", "SuspicionLevel", lower=lower),
        "src_ip": _first(row, "IpAddress", "Ip", "SourceIP", lower=lower),
        "user": _first(row, "AccountName", "AccountUpn", "AccountSid", lower=lower),
        "category": category,
        "alert_title_id": alert_title_id,
        "mitre": _first(row, "MitreTechniques", "AttackTechniques", lower=lower),
        "entity_type": _first(row, "EntityType", lower=lower),
        "grade": grade,
        # attacker-influenced free-text surfaces (also injection surfaces)
        "url": _first(row, "Url", lower=lower),
        "filename": _first(row, "FileName", "FolderPath", lower=lower),
        "message": (f"{category}: {title}" if category else title),
        "raw": {k: row[k] for k in list(row)[:20]},  # trim very wide rows
    }
    return {"detector": "guide", "label": _grade_label(grade),
            "native": native, "source": "guide"}


def load(data_dir: str, n_per_detector: int = 36, seed: int = 7,
         attack_ratio: float = 0.6, csv_glob: str = "*.csv", split: str = "train"):
    """Return (items, adapters). Reservoir-samples ``n_per_detector`` rows total
    (GUIDE is single-source), split by ``attack_ratio`` between graded-true and
    benign rows when both are present. ``split`` selects the train or test CSV."""
    paths = sorted(glob.glob(os.path.join(data_dir, csv_glob)))
    # prefer the requested split (train or test) when both files are present
    want = (split or "train").lower()
    paths.sort(key=lambda p: (0 if want in p.lower() else 1, p))
    if not paths:
        raise FileNotFoundError(
            f"no GUIDE CSV ({csv_glob}) in {data_dir}. Download it from Kaggle "
            "(see data/DOWNLOAD_DATASETS.md).")
    rng = random.Random(seed)
    cap = max(n_per_detector * 6, 400)
    res: dict[bool, list] = {True: [], False: []}
    seen: dict[bool, int] = {True: 0, False: 0}
    with open(paths[0], encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        lower = {c.lower(): c for c in (reader.fieldnames or [])}
        for row in reader:
            item = _row_item(row, lower)
            is_atk = item["label"] == "attack"
            seen[is_atk] += 1
            b = res[is_atk]
            if len(b) < cap:
                b.append(item)
            else:
                j = rng.randint(0, seen[is_atk] - 1)
                if j < cap:
                    b[j] = item

    n_attack = int(round(n_per_detector * attack_ratio))
    atk, ben = res[True][:], res[False][:]
    rng.shuffle(atk); rng.shuffle(ben)
    items = atk[:n_attack] + ben[:n_per_detector - n_attack]
    deficit = n_per_detector - len(items)
    if deficit > 0:
        items += (atk[n_attack:] + ben[n_per_detector - n_attack:])[:deficit]
    rng.shuffle(items)
    return items, ADAPTERS
