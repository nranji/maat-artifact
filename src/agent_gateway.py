"""Source gateway — a standalone NLIP endpoint (separate process), one per detector.

This makes every node on the diagram its own service. The gateway receives a
NATIVE vendor alert over NLIP, maps it to the canonical OCSF event (the adapter),
and forwards it to the harmonizer over NLIP. It returns the harmonizer's verdict
plus the OCSF event it produced.

Run:  python3 agent_gateway.py --detector wazuh --port 8741 \
                               --harmonizer-url http://127.0.0.1:8731/nlip
"""
from __future__ import annotations

import argparse

import nlip_soc as core
import nlip_transport as nt

try:
    from datasets import ait_ads as _ait
    from datasets import guide as _guide
except Exception:          # datasets package optional; synthetic still works
    _ait = _guide = None


def _adapt(dataset, detector, native):
    """Pick the adapter for the alert's dataset of origin (carried in provenance)."""
    if dataset == "ait_ads" and _ait is not None:
        return _ait.adapt_ait(native)
    if dataset == "guide" and _guide is not None:
        return _guide.adapt_guide(native)
    return core.ADAPTERS[detector](native)


def make_handler(detector, harmonizer_url, log):

    def handler(msg):
        native = msg.content
        prov = dict(msg.provenance or {})
        dataset = prov.get("dataset", "synthetic")
        event = _adapt(dataset, detector, native)
        prov.setdefault("source", detector)
        prov.setdefault("trust", "untrusted-vendor-text")
        fwd = core.new_message(event, from_endpoint=f"{detector}-gateway",
                               to_endpoint="harmonizer", subformat="ocsf",
                               provenance=prov)
        log(f"[{detector}-gw] native -> OCSF '{event['finding_info']['title'][:42]}' -> harmonizer")
        ack = nt.send(harmonizer_url, fwd)
        content = dict(ack.content)
        content["event"] = event
        content["detector"] = detector
        return core.new_message(content, from_endpoint=f"{detector}-gateway",
                                to_endpoint=msg.from_endpoint, subformat="json",
                                message_type="ack", validator_result=ack.validator_result)

    return handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True,
                    choices=["wazuh", "suricata", "aminer", "guide"])
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--harmonizer-url", default="http://127.0.0.1:8731/nlip")
    a = ap.parse_args()
    log = lambda m: print(m, flush=True)
    log(f"[{a.detector}-gw] NLIP endpoint on 127.0.0.1:{a.port} -> {a.harmonizer_url}")
    nt.serve(a.port, make_handler(a.detector, a.harmonizer_url, log),
             health=lambda: {"ok": True, "agent": f"{a.detector}-gateway"})
