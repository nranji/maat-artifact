"""AIT-ADS loader: real Wazuh / Suricata / AMiner alerts -> canonical OCSF.

Two input modes, auto-detected:

  CSV mode (works out of the box):
    Reads the reduced, labelled alert lists shipped in the AIT-ADS repo
    (``alerts_csv.zip`` -> ``<scenario>_alerts.txt`` with columns
    time,name,ip,host,short,time_label,event_label). This is real, labelled data
    but reduced: it carries the detector, signature, one IP, the host, and the
    attack-phase label. Severity, ports, and user are absent, so they map to
    UNKNOWN.

  Raw mode (richer; needs the Zenodo download):
    Reads ``alerts_raw/<scenario>_wazuh.json`` (Wazuh + Suricata, one JSON object
    per line) and ``alerts_raw/<scenario>_aminer.json`` (AMiner anomalies). These
    carry rule level (-> real severity), the network 5-tuple, and full log lines.

The record layout for both raw files was taken from the AIT-ADS ``analyze.py``
parser (github.com/ait-aecid/alert-data-set).

Dataset: Landauer, Skopik, Wurzenberger, "Introducing a New Alert Data Set for
Multi-Step Attack Analysis", CSET '24. Zenodo 10.5281/zenodo.8263181.
"""
from __future__ import annotations

import csv
import io
import json
import os
import random
import zipfile
from typing import Any, Optional

import nlip_soc as core

DETECTOR_NAMES = {"wazuh": "Wazuh", "suricata": "Suricata", "aminer": "AMiner"}
SCENARIOS = ["russellmitchell", "fox", "harrison", "santos",
             "shaw", "wardbeck", "wheeler", "wilson"]


# --------------------------------------------------------------------------
# Single adapter: normalized AIT native record -> canonical OCSF event.
# The loader emits a uniform native dict (keys below) for both CSV and raw
# records, so one adapter covers all three detectors.
# --------------------------------------------------------------------------
def adapt_ait(a: dict) -> dict:
    det = a.get("detector", "wazuh")
    sid = a.get("severity_id")
    sid = 0 if sid is None else int(sid)
    return core._canonical(
        product=DETECTOR_NAMES.get(det, "Wazuh"),
        product_uid=a.get("uid") or core.UNKNOWN,
        title=a.get("title") or core.UNKNOWN,
        time=a.get("time_iso") or core.UNKNOWN,
        severity_id=sid,
        src_ip=a.get("src_ip") or core.UNKNOWN,
        src_port=core._to_int(a.get("src_port")),
        dst_ip=a.get("dst_ip") or core.UNKNOWN,
        dst_port=core._to_int(a.get("dst_port")),
        user=a.get("user") or core.UNKNOWN,
        message=a.get("message") or a.get("title") or core.UNKNOWN,
        unmapped={"short": a.get("short"), "host": a.get("host"),
                  "phase": a.get("phase"), "detector": det,
                  **core._surfaces(a)},
        raw=a.get("raw", a),
    )


ADAPTERS = {d: adapt_ait for d in DETECTOR_NAMES}


# --------------------------------------------------------------------------
# CSV mode
# --------------------------------------------------------------------------
def _detector_of(name: str) -> Optional[str]:
    low = name.lower()
    if low.startswith("wazuh"):
        return "wazuh"
    if low.startswith("suricata"):
        return "suricata"
    if low.startswith("aminer"):
        return "aminer"
    return None


def _clean_title(name: str, det: str) -> str:
    """Strip the vendor prefix the CSV puts on every signature."""
    for pre in ("Suricata: Alert - ", "Suricata: ", "Wazuh: ", "AMiner: "):
        if name.startswith(pre):
            return name[len(pre):]
    return name


def _csv_rows(zip_path: str, scenario: Optional[str]):
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.endswith("_alerts.txt")]
        if scenario:
            names = [n for n in names if os.path.basename(n).startswith(scenario)]
        if not names:
            raise FileNotFoundError(
                f"no *_alerts.txt in {zip_path} for scenario={scenario!r}")
        for n in names:
            with z.open(n) as fh:
                reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8"))
                for row in reader:
                    yield row


def load_csv(zip_path: str, n_per_detector: int, seed: int,
             scenario: Optional[str] = "russellmitchell",
             attack_ratio: float = 0.6) -> list[dict]:
    """Reservoir-sample a balanced set of real alerts from the reduced CSV.

    Samples up to ``n_per_detector`` per detector, split by ``attack_ratio``
    between attack-phase alerts and false positives when both are available.
    Pass ``scenario=None`` to pool across all scenarios in the zip (paper-style
    stratified sample).
    """
    rng = random.Random(seed)
    # reservoirs keyed by (detector, is_attack)
    res: dict[tuple, list] = {}
    seen: dict[tuple, int] = {}
    cap = max(n_per_detector * 4, 200)  # oversample, then trim to the ratio
    for row in _csv_rows(zip_path, scenario):
        det = _detector_of(row.get("name", ""))
        if not det:
            continue
        is_attack = row.get("time_label", "") != "false_positive"
        key = (det, is_attack)
        seen[key] = seen.get(key, 0) + 1
        bucket = res.setdefault(key, [])
        if len(bucket) < cap:
            bucket.append(row)
        else:  # reservoir replacement
            j = rng.randint(0, seen[key] - 1)
            if j < cap:
                bucket[j] = row

    items: list[dict] = []
    n_attack = int(round(n_per_detector * attack_ratio))
    n_benign = n_per_detector - n_attack
    for det in DETECTOR_NAMES:
        atk = res.get((det, True), [])[:]
        ben = res.get((det, False), [])[:]
        rng.shuffle(atk)
        rng.shuffle(ben)
        take_a = atk[:n_attack]
        take_b = ben[:n_benign]
        # backfill from whichever class has surplus so we hit n_per_detector
        deficit = n_per_detector - len(take_a) - len(take_b)
        if deficit > 0:
            extra = atk[len(take_a):] + ben[len(take_b):]
            take_a += extra[:deficit]
        for row in (take_a + take_b):
            items.append(_csv_item(det, row))
    rng.shuffle(items)
    return items


def load_csv_pooled(zip_path: str, n_per_detector: int, seed: int,
                    attack_ratio: float = 0.6) -> list[dict]:
    """Stratified sample pooled across all AIT-ADS scenarios (detector × phase)."""
    return load_csv(zip_path, n_per_detector, seed, scenario=None,
                    attack_ratio=attack_ratio)


def _csv_item(det: str, row: dict) -> dict:
    name = row.get("name", "")
    phase = row.get("time_label", "")
    label = "benign" if phase == "false_positive" else "attack"
    try:
        time_iso = core._iso(int(row["time"]))
    except (KeyError, ValueError, TypeError):
        time_iso = core.UNKNOWN
    native = {
        "detector": det,
        "title": _clean_title(name, det),
        "uid": row.get("short") or core.UNKNOWN,
        "time_iso": time_iso,
        "severity_id": None,               # CSV carries no severity -> UNKNOWN
        "src_ip": row.get("ip") or None,   # the alert's associated host IP
        "dst_ip": None,
        "src_port": None, "dst_port": None,
        "user": None,
        "host": row.get("host"),
        "short": row.get("short"),
        "phase": phase,
        "message": name,
        "raw": dict(row),
    }
    return {"detector": det, "label": label, "native": native, "source": "ait_ads_csv"}


# --------------------------------------------------------------------------
# Raw mode (Zenodo ait_ads.zip -> alerts_raw/*.json)
# --------------------------------------------------------------------------
def _iter_jsonl(path: str):
    with open(path, encoding="utf-8") as fh:
        head = fh.read(64).lstrip()
        fh.seek(0)
        if head.startswith("["):            # a single JSON array
            for obj in json.load(fh):
                yield obj
            return
        for line in fh:                      # JSON-per-line
            line = line.strip().rstrip(",")
            if not line or line in "[]":
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _wazuh_origin(j: dict) -> str:
    groups = (j.get("rule", {}) or {}).get("groups", []) or []
    if any("suricata" in str(g).lower() or g == "ids" for g in groups):
        return "suricata"
    if str((j.get("decoder", {}) or {}).get("name", "")).lower() == "suricata":
        return "suricata"
    if str((j.get("rule", {}) or {}).get("description", "")).lower().startswith("suricata"):
        return "suricata"
    return "wazuh"


def _wazuh_time(j: dict) -> str:
    for path in (("data", "timestamp"), ("predecoder", "timestamp")):
        d = j.get(path[0], {}) or {}
        if isinstance(d, dict) and d.get(path[1]):
            return str(d[path[1]])
    return str(j.get("timestamp") or core.UNKNOWN)


def _norm_name(name: Optional[str]) -> str:
    """Strip the vendor prefix so raw signatures (bare in the Wazuh JSON) match the
    reduced CSV, which prepends 'Wazuh: ' / 'Suricata: Alert - ' / 'AMiner: '."""
    s = (name or "").strip()
    for pre in ("Suricata: Alert - ", "Suricata: ", "Wazuh: ", "AMiner: "):
        if s.startswith(pre):
            return s[len(pre):].strip()
    return s


def _label_index(zip_path: Optional[str], scenario: str) -> dict:
    """Build a lookup from the vendored reduced CSV keyed by (host_ip, normalized
    signature). Each entry stores the attack-phase Counter AND the authoritative
    detector taken from the CSV 'name' prefix (Wazuh:/Suricata:/AMiner:). The raw
    Zenodo alerts carry no per-alert label, and both Wazuh- and Suricata-origin
    alerts share {scenario}_wazuh.json, so we recover BOTH the label and the true
    detector by joining to the reduced list rather than guessing from rule groups."""
    from collections import Counter
    idx: dict = {}
    if not zip_path or not os.path.exists(zip_path):
        return idx
    try:
        for row in _csv_rows(zip_path, scenario):
            key = (row.get("ip", ""), _norm_name(row.get("name", "")))
            rec = idx.setdefault(key, {"phase": Counter(), "det": None})
            rec["phase"][row.get("time_label", "")] += 1
            if rec["det"] is None:
                rec["det"] = _detector_of(row.get("name", ""))
    except (FileNotFoundError, KeyError):
        return {}
    return idx


def _lookup_phase(idx: dict, ip: Optional[str], name: Optional[str]) -> Optional[str]:
    rec = idx.get((ip or "", _norm_name(name)))
    if not rec or not rec["phase"]:
        return None
    return rec["phase"].most_common(1)[0][0]   # majority phase where a signature recurs


def _lookup_det(idx: dict, ip: Optional[str], name: Optional[str]) -> Optional[str]:
    rec = idx.get((ip or "", _norm_name(name)))
    return rec["det"] if rec else None


def _phase_to_label(phase: Optional[str]) -> str:
    if phase is None:
        return "unlabeled"
    return "benign" if phase == "false_positive" else "attack"


def _wazuh_item(j: dict, idx: dict) -> Optional[dict]:
    rule = j.get("rule", {}) or {}
    if not rule:
        return None
    data = j.get("data", {}) or {}
    agent = j.get("agent", {}) or {}
    try:
        sid = core._wazuh_severity(int(rule.get("level", 0)))
    except (TypeError, ValueError):
        sid = 0
    name = rule.get("description")
    # authoritative detector from the reduced CSV; heuristic only as a fallback
    det = _lookup_det(idx, agent.get("ip"), name) or _wazuh_origin(j)
    phase = _lookup_phase(idx, agent.get("ip"), name)
    native = {
        "detector": det,
        "title": name or core.UNKNOWN,
        "uid": str(rule.get("id") or core.UNKNOWN),
        "time_iso": _wazuh_time(j),
        "severity_id": sid,
        "src_ip": data.get("src_ip") or data.get("srcip"),
        "dst_ip": data.get("dest_ip") or agent.get("ip"),
        "src_port": data.get("src_port") or data.get("srcport"),
        "dst_port": data.get("dest_port"),
        "user": data.get("dstuser") or data.get("srcuser") or data.get("user"),
        "host": agent.get("name"),
        "short": None,
        "phase": phase,
        "message": j.get("full_log") or name or core.UNKNOWN,
        "raw": j,
    }
    return {"detector": det, "label": _phase_to_label(phase),
            "native": native, "source": "ait_ads_raw"}


def _aminer_item(j: dict, idx: dict) -> Optional[dict]:
    comp = (j.get("AnalysisComponent", {}) or {}).get("AnalysisComponentName")
    logd = j.get("LogData", {}) or {}
    if not comp and not logd:
        return None
    ts = logd.get("DetectionTimestamp")
    if isinstance(ts, list) and ts:
        ts = ts[-1]
    try:
        time_iso = core._iso(float(ts)) if ts is not None else core.UNKNOWN
    except (TypeError, ValueError):
        time_iso = core.UNKNOWN
    raw_lines = logd.get("RawLogData") or []
    msg = raw_lines[0] if raw_lines else (comp or core.UNKNOWN)
    host_ip = (j.get("AMiner", {}) or {}).get("ID")
    ip = None
    for token in str(msg).replace(",", " ").split():
        if core.IP_RE.fullmatch(token):
            ip = token
            break
    phase = _lookup_phase(idx, host_ip, comp)
    native = {
        "detector": "aminer",
        "title": comp or core.UNKNOWN,
        "uid": comp or core.UNKNOWN,
        "time_iso": time_iso,
        "severity_id": 0,                    # AMiner anomalies carry no severity
        "src_ip": ip, "dst_ip": None,
        "src_port": None, "dst_port": None,
        "user": None,
        "host": host_ip,
        "short": None, "phase": phase,
        "message": str(msg),
        "raw": j,
    }
    return {"detector": "aminer", "label": _phase_to_label(phase),
            "native": native, "source": "ait_ads_raw"}


def load_raw(raw_dir: str, n_per_detector: int, seed: int,
             scenario: str = "russellmitchell",
             label_zip: Optional[str] = None,
             attack_ratio: float = 0.6,
             scenarios: Optional[list] = None) -> list[dict]:
    """Sample raw alerts, attributing the detector from the reduced CSV and, like
    CSV mode, balancing each detector between attack-phase and benign alerts.

    Pass ``scenarios`` (e.g. all SCENARIOS) to pool across multiple scenario files.
    """
    rng = random.Random(seed)
    sc_list = scenarios or [scenario]
    # reservoir keyed by (detector, is_attack)
    res: dict[tuple, list] = {}
    seen: dict[tuple, int] = {}
    cap = max(n_per_detector * 4, 200)

    def offer(item):
        if not item:
            return
        key = (item["detector"], item["label"] != "benign")
        seen[key] = seen.get(key, 0) + 1
        b = res.setdefault(key, [])
        if len(b) < cap:
            b.append(item)
        else:
            j = rng.randint(0, seen[key] - 1)
            if j < cap:
                b[j] = item

    for sc in sc_list:
        wazuh_path = os.path.join(raw_dir, f"{sc}_wazuh.json")
        aminer_path = os.path.join(raw_dir, f"{sc}_aminer.json")
        idx = _label_index(label_zip, sc)
        if os.path.exists(wazuh_path):
            for j in _iter_jsonl(wazuh_path):
                offer(_wazuh_item(j, idx))
        if os.path.exists(aminer_path):
            for j in _iter_jsonl(aminer_path):
                offer(_aminer_item(j, idx))

    items = []
    n_attack = int(round(n_per_detector * attack_ratio))
    n_benign = n_per_detector - n_attack
    for det in ("wazuh", "suricata", "aminer"):
        atk = res.get((det, True), [])[:]
        ben = res.get((det, False), [])[:]
        rng.shuffle(atk); rng.shuffle(ben)
        take = atk[:n_attack] + ben[:n_benign]
        deficit = n_per_detector - len(take)
        if deficit > 0:
            take += (atk[n_attack:] + ben[n_benign:])[:deficit]
        items.extend(take)
    rng.shuffle(items)
    return items


def load_raw_pooled(raw_dir: str, n_per_detector: int, seed: int,
                    label_zip: Optional[str] = None,
                    attack_ratio: float = 0.6) -> list[dict]:
    """Stratified raw sample pooled across all scenarios with available JSON."""
    present = [sc for sc in SCENARIOS
               if os.path.exists(os.path.join(raw_dir, f"{sc}_wazuh.json"))]
    if not present:
        raise FileNotFoundError(f"no raw scenario JSON under {raw_dir}")
    return load_raw(raw_dir, n_per_detector, seed, scenario=present[0],
                    label_zip=label_zip, attack_ratio=attack_ratio,
                    scenarios=present)


def e1_full_csv(zip_path: str) -> dict:
    """Deterministic full-corpus E1: every reduced-CSV alert -> OCSF validity.

    Streams all ~2.66M alerts. No LLM.
    """
    valid = total = unk_fields = key_fields = 0
    by_det: dict = {}
    for row in _csv_rows(zip_path, None):
        det = _detector_of(row.get("name", ""))
        if not det:
            continue
        item = _csv_item(det, row)
        ev = adapt_ait(item["native"])
        ok = core.is_valid_ocsf(ev)          # cached compiled validator (~12x faster at scale)
        unk = core.canonical_unknown_fields(ev)
        total += 1
        valid += int(ok)
        key_fields += 4
        unk_fields += len(unk)
        d = by_det.setdefault(det, {"n": 0, "valid": 0, "unknown": 0})
        d["n"] += 1
        d["valid"] += int(ok)
        d["unknown"] += len(unk)
    pct = (lambda x, n: round(100.0 * x / n, 1) if n else 0.0)
    return {
        "n_alerts": total,
        "valid_ocsf_pct": pct(valid, total),
        "unknown_field_rate_pct": pct(unk_fields, key_fields),
        "by_detector": {k: {"n": v["n"], "valid_pct": pct(v["valid"], v["n"]),
                            "unknown_field_rate_pct": pct(v["unknown"], v["n"] * 4)}
                        for k, v in by_det.items()},
    }


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def load(data_dir: str, n_per_detector: int = 12, seed: int = 7,
         scenario: str = "russellmitchell", mode: str = "auto"):
    """Return (items, adapters). ``mode`` in {"auto","raw","csv"}.

    ``data_dir`` should contain either ``alerts_csv.zip`` (CSV mode) and/or an
    ``alerts_raw/`` directory with the Zenodo JSON files (raw mode).
    """
    raw_dir = os.path.join(data_dir, "alerts_raw")
    zip_path = os.path.join(data_dir, "alerts_csv.zip")
    have_raw = os.path.isdir(raw_dir) and any(
        os.path.exists(os.path.join(raw_dir, f"{scenario}_{d}.json"))
        for d in ("wazuh", "aminer"))
    have_csv = os.path.exists(zip_path)

    if mode == "auto":
        mode = "raw" if have_raw else "csv"
    if mode == "raw":
        if not have_raw:
            raise FileNotFoundError(
                f"raw mode needs {raw_dir}/{scenario}_wazuh.json (+ _aminer.json). "
                "Download the AIT-ADS from Zenodo (see data/DOWNLOAD_DATASETS.md).")
        label_zip = zip_path if have_csv else None
        return load_raw(raw_dir, n_per_detector, seed, scenario, label_zip), ADAPTERS
    if mode == "csv_pooled":
        if not have_csv:
            raise FileNotFoundError(f"csv_pooled mode needs {zip_path}")
        return load_csv_pooled(zip_path, n_per_detector, seed), ADAPTERS
    if mode == "raw_pooled":
        if not os.path.isdir(raw_dir):
            raise FileNotFoundError(f"raw_pooled mode needs {raw_dir}/")
        label_zip = zip_path if have_csv else None
        return load_raw_pooled(raw_dir, n_per_detector, seed, label_zip), ADAPTERS
    if not have_csv:
        raise FileNotFoundError(f"csv mode needs {zip_path}")
    return load_csv(zip_path, n_per_detector, seed, scenario), ADAPTERS
