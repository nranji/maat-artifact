"""
Core types: NLIP envelope, synthetic alerts, OCSF adapters, faithfulness validator.

Contains:
  - A minimal NLIP envelope (modelled on ECMA-430: control/format/subformat/content)
    plus routing metadata, used on the agent-to-agent and agent-to-human edges.
  - Synthetic, heterogeneous downstream alerts shaped like the three AIT-ADS
    detectors (Wazuh, Suricata, AMiner).
  - Per-source adapter gateways that map native alerts to an OCSF-subset canonical
    event and wrap them in NLIP.
  - An OCSF-subset JSON Schema and a validator (E1 schema-validity check).
  - The deterministic faithfulness validator (E2/E3 contribution).

No external LLM is required for the deterministic parts; those are real and runnable.
The LLM summary step lives in generators.py (agents: agent_harmonizer.py / agent_analyst.py).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# --------------------------------------------------------------------------
# NLIP envelope (ECMA-430-style). NLIP lives on endpoint-to-endpoint edges.
# --------------------------------------------------------------------------

NLIP_VERSION = "ECMA-430:2025"


@dataclass
class NLIPMessage:
    """A single NLIP message. Mirrors the ECMA-430 core fields (control, format,
    subformat, content) and adds the envelope/routing metadata an endpoint needs.
    Security profile reflects ECMA-434 (mandatory-for-conformance) tiers."""
    content: Any
    format: str = "structured"          # "text" | "structured" | "binary" | "location"
    subformat: str = "ocsf"             # e.g. "ocsf", "plain", "wazuh", "suricata", "aminer"
    control: bool = False               # control vs. data message
    message_type: str = "alert"
    # envelope / routing
    from_endpoint: str = ""
    to_endpoint: str = ""
    conversation_id: str = ""
    message_id: str = ""
    security_profile: str = "ECMA-434:rigorous"
    submessages: list = field(default_factory=list)
    # trust metadata carried in the envelope (used on the emit edge)
    provenance: Optional[dict] = None      # e.g. {"source": "...", "trust": "untrusted-vendor-text"}
    confidence: Optional[float] = None
    validator_result: Optional[dict] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False)


_counter = {"n": 0}


def new_message(content, *, from_endpoint, to_endpoint, subformat="ocsf",
                fmt="structured", conversation_id="", message_type="alert",
                provenance=None, confidence=None, validator_result=None,
                submessages=None) -> NLIPMessage:
    _counter["n"] += 1
    return NLIPMessage(
        content=content, format=fmt, subformat=subformat,
        from_endpoint=from_endpoint, to_endpoint=to_endpoint,
        conversation_id=conversation_id or f"conv-{_counter['n']:04d}",
        message_id=f"msg-{_counter['n']:06d}", message_type=message_type,
        provenance=provenance, confidence=confidence,
        validator_result=validator_result, submessages=submessages or [],
    )


# --------------------------------------------------------------------------
# Synthetic heterogeneous alerts (Wazuh / Suricata / AMiner shaped)
# --------------------------------------------------------------------------
# These mimic the field layouts of the three AIT-ADS detectors. The point is
# schema heterogeneity: the signature lives in a different field per detector,
# severity is present for two and absent for one, user/ports vary.

SRC_HOSTS = ["10.0.0.5", "10.0.0.11", "10.0.0.23", "192.168.10.7"]
DST_HOSTS = ["10.0.12.20", "10.0.12.21", "10.0.12.30"]
USERS = ["admin", "jsmith", "root", "svc_backup"]


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def make_wazuh(i: int, rng, *, attack: bool) -> dict:
    sigs = [
        ("5710", 5, "sshd: Attempt to login using a non-existent user"),
        ("5712", 10, "sshd: brute force trying to get access to the system"),
        ("100002", 12, "Web server 400 error code - possible attack"),
        ("5402", 3, "Successful sudo to ROOT executed"),
    ]
    rid, level, desc = sigs[i % len(sigs)] if attack else sigs[3]
    src = rng.choice(SRC_HOSTS)
    dst = rng.choice(DST_HOSTS)
    user = rng.choice(USERS)
    sport = rng.randint(40000, 60000)
    return {
        "timestamp": _iso(1709539953 + i * 37) + ".000",
        "rule": {"id": rid, "level": level, "description": desc,
                 "groups": ["syslog", "sshd"]},
        "agent": {"id": f"00{(i % 5) + 1}", "name": f"web-server-0{(i % 3) + 1}", "ip": dst},
        "data": {"srcip": src, "srcport": str(sport), "dstuser": user},
        "full_log": f"sshd[{1000 + i}]: Invalid user {user} from {src} port {sport}",
        "decoder": {"name": "sshd"},
    }


def make_suricata(i: int, rng, *, attack: bool) -> dict:
    sigs = [
        ("ET SCAN Nmap Scripting Engine User-Agent Detected", 2, 2024364, "Attempted Information Leak"),
        ("ET WEB_SERVER SQL Injection Attempt", 1, 2006445, "Web Application Attack"),
        ("ET POLICY curl User-Agent Outbound", 3, 2013028, "Potentially Bad Traffic"),
    ]
    sig, sev, sid, cat = sigs[i % len(sigs)] if attack else sigs[2]
    src = rng.choice(SRC_HOSTS)
    dst = rng.choice(DST_HOSTS)
    return {
        "timestamp": _iso(1709540102 + i * 41) + ".123456+0000",
        "event_type": "alert",
        "src_ip": src, "src_port": rng.randint(40000, 60000),
        "dest_ip": dst, "dest_port": rng.choice([80, 443, 3306]),
        "proto": "TCP",
        "alert": {"signature": sig, "category": cat, "severity": sev,
                  "signature_id": sid, "gid": 1},
        "flow_id": 1000000000 + i,
    }   # note: no user, no severity *label* (numeric, inverted scale)


def make_aminer(i: int, rng, *, attack: bool) -> dict:
    comps = [
        ("NewMatchPathValueDetector", "/model/syslog/host"),
        ("EntropyDetector", "/model/messages/cmd"),
        ("NewMatchPathDetector", "/model/apache/request"),
    ]
    comp, path = comps[i % len(comps)]
    val = rng.choice(SRC_HOSTS)
    return {
        "Timestamp": 1709540102.5 + i * 29,
        "AnalysisComponentName": comp,
        "AnalysisComponentType": comp,
        "Message": f"New value(s) detected for path {path}",
        "AffectedLogAtomPaths": [path],
        "AffectedLogAtomValues": [val],
        "LogData": {"RawLogData": [f"raw atom {i} value {val}"]},
    }   # note: no severity, no dst, signature == AnalysisComponentName


def generate_alerts(n_per_detector: int = 12, seed: int = 7) -> list[dict]:
    import random
    rng = random.Random(seed)
    out = []
    for i in range(n_per_detector):
        attack = (i % 3 != 0)  # ~2/3 attack, ~1/3 benign FP, mirrors SOC reality
        out.append({"detector": "wazuh", "label": "attack" if attack else "benign",
                    "native": make_wazuh(i, rng, attack=attack)})
        out.append({"detector": "suricata", "label": "attack" if attack else "benign",
                    "native": make_suricata(i, rng, attack=attack)})
        out.append({"detector": "aminer", "label": "attack" if attack else "benign",
                    "native": make_aminer(i, rng, attack=attack)})
    return out


# --------------------------------------------------------------------------
# OCSF-subset canonical schema + adapter gateways (E1)
# --------------------------------------------------------------------------
# OCSF severity_id: 0 Unknown,1 Informational,2 Low,3 Medium,4 High,5 Critical,6 Fatal
SEVERITY_LABEL = {0: "Unknown", 1: "Informational", 2: "Low", 3: "Medium",
                  4: "High", 5: "Critical", 6: "Fatal"}

UNKNOWN = "UNKNOWN"


def _wazuh_severity(level: int) -> int:
    if level >= 12:
        return 5
    if level >= 8:
        return 4
    if level >= 4:
        return 3
    return 2


def _suricata_severity(sev: int) -> int:
    # Suricata: 1 = most severe ... 3 = least
    return {1: 4, 2: 3, 3: 2}.get(sev, 0)


def _surfaces(a: dict) -> dict:
    """Attacker-influenced free-text fields, surfaced into `unmapped` so an injected
    instruction is visible in the canonical event (and reaches an LLM summarizer)."""
    return {k: a[k] for k in ("vendor_note", "filename", "url", "email_subject",
                              "payload_printable") if a.get(k)}


def adapt_wazuh(a: dict) -> dict:
    r = a["rule"]
    sid = _wazuh_severity(int(r["level"]))
    return _canonical(
        product="Wazuh", product_uid=str(r["id"]),
        title=r["description"], time=a["timestamp"],
        severity_id=sid,
        src_ip=a["data"].get("srcip", UNKNOWN),
        src_port=_to_int(a["data"].get("srcport")),
        dst_ip=a["agent"].get("ip", UNKNOWN),
        dst_port=None,
        user=a["data"].get("dstuser", UNKNOWN),
        message=a.get("full_log", r["description"]),
        unmapped={"decoder": a.get("decoder"), "groups": r.get("groups"),
                  "full_log": a.get("full_log"), **_surfaces(a)},
        raw=a,
    )


def adapt_suricata(a: dict) -> dict:
    al = a["alert"]
    return _canonical(
        product="Suricata", product_uid=str(al["signature_id"]),
        title=al["signature"], time=a["timestamp"],
        severity_id=_suricata_severity(int(al["severity"])),
        src_ip=a.get("src_ip", UNKNOWN), src_port=a.get("src_port"),
        dst_ip=a.get("dest_ip", UNKNOWN), dst_port=a.get("dest_port"),
        user=UNKNOWN,                       # Suricata NIDS has no user -> UNKNOWN
        message=al["signature"],
        unmapped={"category": al.get("category"), "proto": a.get("proto"),
                  "flow_id": a.get("flow_id"), **_surfaces(a)},
        raw=a,
    )


def adapt_aminer(a: dict) -> dict:
    vals = a.get("AffectedLogAtomValues", [])
    ip = next((v for v in vals if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", str(v))), UNKNOWN)
    return _canonical(
        product="AMiner", product_uid=a.get("AnalysisComponentName", UNKNOWN),
        title=a.get("AnalysisComponentName", UNKNOWN),
        time=_iso(a["Timestamp"]),
        severity_id=0,                      # AMiner anomaly: no severity -> Unknown
        src_ip=ip, src_port=None,
        dst_ip=UNKNOWN, dst_port=None,      # no destination concept
        user=UNKNOWN,
        message=a.get("Message", UNKNOWN),
        unmapped={"AffectedLogAtomPaths": a.get("AffectedLogAtomPaths"),
                  "RawLogData": a.get("LogData", {}).get("RawLogData"), **_surfaces(a)},
        raw=a,
    )


ADAPTERS = {"wazuh": adapt_wazuh, "suricata": adapt_suricata, "aminer": adapt_aminer}


def _to_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _canonical(*, product, product_uid, title, time, severity_id,
               src_ip, src_port, dst_ip, dst_port, user, message,
               unmapped, raw) -> dict:
    observables = []
    for ip, role in ((src_ip, "Source IP"), (dst_ip, "Destination IP")):
        if ip and ip != UNKNOWN:
            observables.append({"name": role, "type": "IP Address", "value": ip})
    if user and user != UNKNOWN:
        observables.append({"name": "User", "type": "User", "value": user})
    return {
        "class_uid": 2004, "class_name": "Detection Finding",
        "category_uid": 2, "category_name": "Findings",
        "activity_id": 1,
        "severity_id": severity_id, "severity": SEVERITY_LABEL[severity_id],
        "time": time,
        "metadata": {"product": {"vendor_name": product, "name": product},
                     "uid": str(product_uid), "version": "1.5.0"},
        "finding_info": {"title": title, "uid": str(product_uid)},
        "src_endpoint": {"ip": src_ip, "port": src_port},
        "dst_endpoint": {"ip": dst_ip, "port": dst_port},
        "actor": {"user": {"name": user}},
        "observables": observables,
        "message": message,
        "unmapped": unmapped,
        "raw_data": json.dumps(raw, ensure_ascii=False),
    }


# OCSF-subset JSON Schema for E1 validity check
OCSF_SUBSET_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["class_uid", "category_uid", "severity_id", "time",
                 "metadata", "finding_info", "message"],
    "properties": {
        "class_uid": {"type": "integer", "enum": [2004, 4001, 3002]},
        "category_uid": {"type": "integer", "minimum": 1, "maximum": 6},
        "activity_id": {"type": "integer"},
        "severity_id": {"type": "integer", "minimum": 0, "maximum": 6},
        "time": {"type": "string", "minLength": 1},
        "metadata": {
            "type": "object", "required": ["product"],
            "properties": {"product": {
                "type": "object", "required": ["name"],
                "properties": {"name": {"type": "string", "minLength": 1}}}},
        },
        "finding_info": {
            "type": "object", "required": ["title"],
            "properties": {"title": {"type": "string", "minLength": 1}},
        },
        "src_endpoint": {"type": "object"},
        "dst_endpoint": {"type": "object"},
        "message": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}


def validate_ocsf(event: dict) -> tuple[bool, Optional[str]]:
    """Schema validity check (E1). Returns (is_valid, error_message)."""
    try:
        import jsonschema
        jsonschema.validate(event, OCSF_SUBSET_SCHEMA)
        return True, None
    except Exception as e:  # jsonschema.ValidationError or import error
        return False, str(e).splitlines()[0]


_OCSF_VALIDATOR = None


def _ocsf_validator():
    """Compile the OCSF-subset schema once (jsonschema.validate recompiles per call,
    which is ~12x slower over millions of events in the full-corpus E1 pass)."""
    global _OCSF_VALIDATOR
    if _OCSF_VALIDATOR is None:
        import jsonschema
        cls = (getattr(jsonschema, "Draft202012Validator", None)
               or getattr(jsonschema, "Draft7Validator"))
        _OCSF_VALIDATOR = cls(OCSF_SUBSET_SCHEMA)
    return _OCSF_VALIDATOR


def is_valid_ocsf(event: dict) -> bool:
    """Fast boolean validity using a cached compiled validator (no error message).
    Use for large batches such as full-corpus E1; use validate_ocsf when you need
    the specific error string."""
    try:
        return _ocsf_validator().is_valid(event)
    except Exception:
        return False


def native_field_count(detector: str, native: dict) -> int:
    """Count of leaf native fields, used for preservation accounting."""
    def leaves(x):
        if isinstance(x, dict):
            return sum(leaves(v) for v in x.values())
        if isinstance(x, list):
            return sum(leaves(v) for v in x) or 1
        return 1
    return leaves(native)


def canonical_unknown_fields(event: dict) -> list[str]:
    """Which key fields are UNKNOWN/absent in the canonical event."""
    unk = []
    if event["severity_id"] == 0:
        unk.append("severity")
    if event["src_endpoint"].get("ip") in (None, UNKNOWN):
        unk.append("src_ip")
    if event["dst_endpoint"].get("ip") in (None, UNKNOWN):
        unk.append("dst_ip")
    if event["actor"]["user"].get("name") in (None, UNKNOWN):
        unk.append("user")
    return unk


# --------------------------------------------------------------------------
# Deterministic faithfulness validator (the contribution: E2 + E3)
# --------------------------------------------------------------------------
IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
USER_RE = re.compile(
    r"\buser(?:name)?\s+'?([A-Za-z_][A-Za-z0-9_]*(?:[.-][A-Za-z0-9_]+)*)'?", re.I)
SEV_RE = re.compile(r"\b(Unknown|Informational|Low|Medium|High|Critical|Fatal)\b")


@dataclass
class FaithfulnessResult:
    decision: str                  # "EMIT" or "MANUAL_REVIEW"
    field_preservation: float      # 0..1 over present key fields
    contradictions: list
    unsupported: list
    unknown_violations: list
    n_present_fields: int
    n_preserved: int

    @property
    def has_violation(self) -> bool:
        return bool(self.contradictions or self.unsupported or self.unknown_violations)


def validate_faithfulness(summary: str, event: dict) -> FaithfulnessResult:
    """Deterministically check that a natural-language summary asserts nothing the
    canonical event does not support. Compares entities extracted from the summary
    against the typed canonical fields. Routes any violation to MANUAL_REVIEW.

    - field_preservation: of the present (non-UNKNOWN) key fields, how many are
      correctly reflected in the summary.
    - contradictions (intrinsic): summary states a value that conflicts with a field
      (e.g., wrong severity label).
    - unsupported (extrinsic): summary asserts a checkable entity (IP, CVE) absent
      from the event.
    - unknown_violations: summary asserts a concrete value for a field the event
      marks UNKNOWN (the UNKNOWN-instead-of-invent rule).
    """
    contradictions: list = []
    unsupported: list = []
    unknown_violations: list = []

    # ground-truth entity sets from the typed event
    gt_ips = {o["value"] for o in event["observables"] if o["type"] == "IP Address"}
    src_ip = event["src_endpoint"].get("ip")
    dst_ip = event["dst_endpoint"].get("ip")
    if src_ip and src_ip != UNKNOWN:
        gt_ips.add(src_ip)
    if dst_ip and dst_ip != UNKNOWN:
        gt_ips.add(dst_ip)
    gt_user = event["actor"]["user"].get("name")
    gt_sev = event["severity"]
    sev_known = event["severity_id"] != 0
    unknown_fields = set(canonical_unknown_fields(event))

    summary_ips = set(m.group(0) for m in IP_RE.finditer(summary))
    summary_sevs = set(SEV_RE.findall(summary))
    summary_cves = set(c.upper() for c in CVE_RE.findall(summary))
    _user_stop = {"is", "are", "was", "were", "the", "a", "an", "account",
                  "name", "named", "agent", "activity", "action", "login",
                  "access", "associated", "no"}
    summary_users = {u for u in USER_RE.findall(summary)
                     if u.lower() not in _user_stop}

    # ---- contradictions / unsupported on severity ----
    if summary_sevs:
        if sev_known:
            if gt_sev not in summary_sevs:
                contradictions.append(
                    f"severity stated {sorted(summary_sevs)} but event is {gt_sev}")
        else:
            # event severity UNKNOWN; asserting any concrete severity is a violation
            concrete = summary_sevs - {"Unknown"}
            if concrete:
                unknown_violations.append(
                    f"severity asserted {sorted(concrete)} but event severity is UNKNOWN")

    # ---- unsupported IPs ----
    for ip in summary_ips:
        if ip not in gt_ips:
            unsupported.append(f"IP {ip} not present in event")

    # ---- CVEs: event has none in this prototype, so any CVE is unsupported ----
    for cve in summary_cves:
        unsupported.append(f"{cve} not present in event")

    # ---- user UNKNOWN handling ----
    if "user" in unknown_fields and summary_users:
        invented = {u for u in summary_users if u.lower() != "unknown"}
        if invented:
            unknown_violations.append(
                f"user asserted {sorted(invented)} but event user is UNKNOWN")
    elif gt_user and gt_user != UNKNOWN:
        for u in summary_users:
            if u.lower() != gt_user.lower() and u.lower() != "unknown":
                unsupported.append(f"user {u} not present in event (event user {gt_user})")

    # ---- field preservation over present key fields ----
    present, preserved = 0, 0

    def check(present_cond, ok_cond):
        nonlocal present, preserved
        if present_cond:
            present += 1
            if ok_cond:
                preserved += 1

    check(sev_known, gt_sev in summary)
    check(src_ip not in (None, UNKNOWN), src_ip in summary)
    check(dst_ip not in (None, UNKNOWN), dst_ip in summary)
    check(gt_user not in (None, UNKNOWN), bool(gt_user) and gt_user in summary)
    # product/detector and title always present
    present += 1
    if event["metadata"]["product"]["name"] in summary:
        preserved += 1
    fp = (preserved / present) if present else 1.0

    decision = "EMIT"
    if contradictions or unsupported or unknown_violations:
        decision = "MANUAL_REVIEW"

    return FaithfulnessResult(
        decision=decision, field_preservation=fp,
        contradictions=contradictions, unsupported=unsupported,
        unknown_violations=unknown_violations,
        n_present_fields=present, n_preserved=preserved,
    )
