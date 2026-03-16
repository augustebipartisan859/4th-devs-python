# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and Gemini call statistics tracker for the image guidance agent.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/stats.js

"""

from typing import Any, Optional

_total_tokens: dict = {"input": 0, "output": 0, "requests": 0}
_gemini_calls: dict = {"generations": 0, "edits": 0, "analyses": 0}


def record_usage(usage: Optional[Any]) -> None:
    """Accumulate token counts from a Responses API usage object.

    Args:
        usage: Usage dict from the API response (may be None).
    """
    if not usage:
        return
    _total_tokens["input"] += usage.get("input_tokens", 0)
    _total_tokens["output"] += usage.get("output_tokens", 0)
    _total_tokens["requests"] += 1


def record_gemini(stats_type: str) -> None:
    """Increment the appropriate Gemini call counter.

    Args:
        stats_type: One of ``"generate"``, ``"edit"``, or ``"analyze"``.
    """
    if stats_type == "generate":
        _gemini_calls["generations"] += 1
    elif stats_type == "edit":
        _gemini_calls["edits"] += 1
    elif stats_type == "analyze":
        _gemini_calls["analyses"] += 1


def get_stats() -> dict:
    """Return a snapshot of current statistics.

    Returns:
        Dict with ``openai`` and ``gemini`` sub-dicts.
    """
    return {
        "openai": dict(_total_tokens),
        "gemini": dict(_gemini_calls),
    }


def log_stats() -> None:
    """Print a summary of token usage and Gemini call counts."""
    reqs = _total_tokens["requests"]
    inp = _total_tokens["input"]
    out = _total_tokens["output"]
    gens = _gemini_calls["generations"]
    edits = _gemini_calls["edits"]
    analyses = _gemini_calls["analyses"]
    print(f"\n📊 OpenAI Stats: {reqs} requests, {inp} input tokens, {out} output tokens")
    print(f"🎨 Gemini Stats: {gens} generations, {edits} edits, {analyses} analyses\n")


def reset_stats() -> None:
    """Reset all statistics counters to zero."""
    global _total_tokens, _gemini_calls
    _total_tokens = {"input": 0, "output": 0, "requests": 0}
    _gemini_calls = {"generations": 0, "edits": 0, "analyses": 0}
