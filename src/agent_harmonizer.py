"""Harmonizer agent — a standalone NLIP endpoint (separate process).

Receives an OCSF event from a gateway over NLIP, drafts an analyst summary
(local LLM via Ollama when available, deterministic otherwise), calls the two
deterministic validators as tools, and on EMIT forwards the faithful summary to
the analyst-assistant endpoint over NLIP. On any violation it fails closed to
MANUAL_REVIEW and does not deliver.

Run:  python3 agent_harmonizer.py --port 8731 --analyst-url http://127.0.0.1:8732/nlip
"""
from __future__ import annotations

import argparse

import nlip_soc as core
import generators as gen
import nlip_transport as nt


def make_handler(analyst_url, log):
    def handler(msg):
        event = msg.content
        prov = msg.provenance or {}
        poisoned, inj = prov.get("poisoned"), prov.get("injection")
        mode = prov.get("mode")

        # draft the summary
        if poisoned and inj:
            # "Simulate prompt injection": model a summarizer that obeyed the injected
            # instruction, regardless of backend, so the validator's catch is demonstrable.
            summary = gen.injection_naive(event, inj)
        elif mode == "ungrounded":
            summary = gen.ungrounded(event)        # LLM with no schema grounding (hallucinates)
        elif gen.ollama_available():
            summary = gen.ollama_agent(event)
        else:
            summary = gen.grounded_template(event)

        # deterministic tool calls
        schema_ok, _ = core.validate_ocsf(event)
        fr = core.validate_faithfulness(summary, event)
        vr = {"decision": fr.decision,
              "field_preservation": round(fr.field_preservation, 2),
              "contradictions": fr.contradictions, "unsupported": fr.unsupported,
              "unknown_violations": fr.unknown_violations,
              "unknown_fields": core.canonical_unknown_fields(event),
              "violations": fr.contradictions + fr.unsupported + fr.unknown_violations}
        title = event["finding_info"]["title"][:46]
        prod = event["metadata"]["product"]["name"]

        if fr.decision == "EMIT":
            deliver = core.new_message(
                {"summary": summary, "event": event},
                from_endpoint="harmonizer", to_endpoint="analyst-assistant",
                subformat="mixed", message_type="deliver",
                provenance={"source": prov.get("source"), "trust": "validated"},
                validator_result=vr)
            nt.send(analyst_url, deliver)
            log(f"[harmonizer] {prod} '{title}' -> EMIT -> delivered to analyst-assistant over NLIP")
        else:
            log(f"[harmonizer] {prod} '{title}' -> MANUAL_REVIEW (withheld): {vr['violations']}")

        return core.new_message(
            {"schema_valid": schema_ok, "summary": summary, **vr},
            from_endpoint="harmonizer", to_endpoint=msg.from_endpoint,
            subformat="json", message_type="ack", validator_result=vr)

    return handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8731)
    ap.add_argument("--analyst-url", default="http://127.0.0.1:8732/nlip")
    a = ap.parse_args()
    log = lambda m: print(m, flush=True)
    log(f"[harmonizer] NLIP endpoint on 127.0.0.1:{a.port}  (ollama={gen.ollama_available()})")
    nt.serve(a.port, make_handler(a.analyst_url, log),
             health=lambda: {"ok": True, "agent": "harmonizer",
                             "ollama": gen.ollama_available(), "model": gen.OLLAMA_MODEL})
