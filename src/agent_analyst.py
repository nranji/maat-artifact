"""Analyst-assistant agent — a standalone NLIP endpoint (separate process).

Two message types over NLIP:
  - "deliver": store a faithful summary + its OCSF event (from the harmonizer).
  - "ask":     a human question -> a grounded answer (local LLM via Ollama when
               available, deterministic otherwise). This is the agent-to-human edge.

Each answer is checked with the faithfulness validator before it is returned.

Run:  python3 agent_analyst.py --port 8732
"""
from __future__ import annotations

import argparse

import nlip_soc as core
import generators as gen
import nlip_transport as nt

STORE: dict = {}   # uid -> {summary, event, vr};  "_latest" -> uid


def make_handler(log):
    def handler(msg):
        if msg.message_type == "deliver":
            ev = msg.content["event"]
            uid = ev["finding_info"]["uid"]
            STORE[uid] = {"summary": msg.content["summary"], "event": ev,
                          "vr": msg.validator_result}
            STORE["_latest"] = uid
            log(f"[analyst] stored faithful summary for '{ev['finding_info']['title'][:46]}' (uid {uid})")
            return core.new_message({"stored": True}, from_endpoint="analyst-assistant",
                                    to_endpoint="harmonizer", message_type="ack")

        if msg.message_type == "ask":
            # An event supplied with the question lets the human query ANY alert,
            # including escalated ones the harmonizer never delivered here.
            event = msg.content.get("event")
            if not event:
                uid = msg.content.get("uid") or STORE.get("_latest")
                rec = STORE.get(uid)
                if not rec:
                    return core.new_message({"answer": "No alert is in context yet."},
                                            from_endpoint="analyst-assistant",
                                            to_endpoint="human", message_type="answer")
                event = rec["event"]
            uid = (msg.content.get("uid")
                   or (event.get("finding_info", {}) or {}).get("uid"))
            q = msg.content["question"]
            ans = gen.analyst_answer(q, event)
            fr = core.validate_faithfulness(ans, event)
            faithful = fr.decision == "EMIT"
            if not faithful:
                # fail closed on the human edge too (symmetric with the harmonizer):
                # withhold the unfaithful answer rather than return it flagged.
                log(f"[analyst] Q: {q!r} -> answer WITHHELD (unfaithful)")
                ans = ("I can't answer that faithfully from the structured event, so I am "
                       "withholding it and flagging this for manual review.")
            else:
                log(f"[analyst] Q: {q!r} -> answered (faithful)")
            return core.new_message(
                {"answer": ans, "faithful": faithful, "withheld": not faithful, "uid": uid},
                from_endpoint="analyst-assistant", to_endpoint="human",
                message_type="answer",
                validator_result={"decision": fr.decision})

        return core.new_message({"error": f"unknown message_type {msg.message_type}"},
                                from_endpoint="analyst-assistant",
                                to_endpoint=msg.from_endpoint, message_type="ack")

    return handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8732)
    a = ap.parse_args()
    log = lambda m: print(m, flush=True)
    log(f"[analyst] NLIP endpoint on 127.0.0.1:{a.port}  (ollama={gen.ollama_available()})")
    nt.serve(a.port, make_handler(log),
             health=lambda: {"ok": True, "agent": "analyst-assistant",
                             "ollama": gen.ollama_available(), "model": gen.OLLAMA_MODEL})
