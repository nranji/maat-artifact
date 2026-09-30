"""LLM-as-judge baseline for the deterministic validator.

Asks a local model whether a summary is faithful to the structured event.
Runs only when an Ollama server is reachable.
"""
from __future__ import annotations

import json
import re

import generators as gen  # reuse the Ollama/pydantic-ai plumbing + availability check

JUDGE_SYSTEM = (
    "You are a strict verifier. You are given a security event as canonical JSON and a "
    "one-paragraph analyst SUMMARY. Decide whether the summary is FAITHFUL, meaning it "
    "asserts nothing that the JSON does not support: no invented IPs, users, severities, "
    "CVEs, or remediations, no contradicted fields, and it says UNKNOWN rather than "
    "guessing absent fields. Answer with a single word on the first line: FAITHFUL or "
    "UNFAITHFUL."
)


def llm_judge_available() -> bool:
    return gen.ollama_available()


def llm_judge_faithful(summary: str, event: dict,
                       model: str = gen.OLLAMA_MODEL,
                       base_url: str = gen.OLLAMA_BASE_URL) -> bool | None:
    """Return True/False for the judge's verdict, or None if the judge is unreachable
    or its answer can't be parsed. None-safe so callers can skip cleanly."""
    if not gen.ollama_available(base_url):
        return None
    try:
        agent = gen._get_agent(JUDGE_SYSTEM, model, base_url)
        payload = {k: v for k, v in event.items() if k != "raw_data"}
        out = agent.run_sync(
            f"EVENT:\n{json.dumps(payload, ensure_ascii=False)}\n\nSUMMARY:\n{summary}"
        ).output.strip()
        head = re.split(r"\s+", out.upper(), 1)[0]
        if "UNFAITHFUL" in out.upper():
            return False
        if "FAITHFUL" in head:
            return True
        return None
    except Exception:
        return None


def confusion(deterministic_emit: list[bool], judge_faithful: list[bool],
              truly_clean: list[bool]) -> dict:
    """Compare both gates against a ground-truth 'clean' label (no violations).

    deterministic_emit[i]: did MAAT's gate emit summary i (EMIT vs MANUAL_REVIEW)
    judge_faithful[i]:     did the LLM judge call summary i faithful
    truly_clean[i]:        the deterministic checker's own decision (no violation).

    IMPORTANT: because truly_clean IS the checker's decision and the gate emits iff
    no violation, the deterministic gate's leaked/over-blocked are 0 BY CONSTRUCTION
    and are not a result. Only the LLM judge's disagreement with the checker is
    meaningful here; a gate-vs-judge superiority claim needs an INDEPENDENT (human)
    reference. Callers should report only the llm_judge stats (see run_all/make_tables).
    """
    def stats(gate):
        tp = sum(1 for g, c in zip(gate, truly_clean) if g and c)         # admitted & clean
        fp = sum(1 for g, c in zip(gate, truly_clean) if g and not c)     # admitted a dirty one
        fn = sum(1 for g, c in zip(gate, truly_clean) if not g and c)     # blocked a clean one
        n = len(gate)
        admitted = tp + fp
        return {
            "admitted": admitted,
            "admitted_clean_pct": round(100.0 * tp / admitted, 1) if admitted else 100.0,
            "leaked_unfaithful": fp,   # the number that matters: dirty summaries let through
            "over_blocked_clean": fn,
            "n": n,
        }
    return {"deterministic_gate": stats(deterministic_emit),
            "llm_judge": stats(judge_faithful)}
