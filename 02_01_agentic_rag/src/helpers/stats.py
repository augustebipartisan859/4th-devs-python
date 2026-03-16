# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and API call statistics tracker for the agentic RAG module.
Tracks input, output, reasoning (chain-of-thought), and prompt-cache tokens
separately — mirroring the extended stats tracked by the JS version.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/stats.js

"""

# Module-level singleton — mutable dict so reset replaces the reference
_total_tokens: dict = {
    "input": 0,
    "output": 0,
    "reasoning": 0,
    "cached": 0,
    "requests": 0,
}


def record_usage(usage: dict) -> None:
    """Accumulate token counts from an OpenAI Responses API usage object.

    Extracts ``cached_tokens`` from ``input_tokens_details`` and
    ``reasoning_tokens`` from ``output_tokens_details``, matching the
    extended tracking done in the JS original.

    Args:
        usage: The ``usage`` field from an API response dict.
    """
    if not usage:
        return
    global _total_tokens
    _total_tokens["input"] += usage.get("input_tokens", 0)
    _total_tokens["output"] += usage.get("output_tokens", 0)

    # Granular breakdown — present on OpenAI Responses API responses
    input_details = usage.get("input_tokens_details") or {}
    _total_tokens["cached"] += input_details.get("cached_tokens", 0)

    output_details = usage.get("output_tokens_details") or {}
    _total_tokens["reasoning"] += output_details.get("reasoning_tokens", 0)

    _total_tokens["requests"] += 1


def get_stats() -> dict:
    """Return a shallow copy of current accumulated stats.

    Returns:
        Dict with keys: input, output, reasoning, cached, requests.
    """
    return _total_tokens.copy()


def log_stats() -> None:
    """Print a single-line session summary to stdout."""
    inp = _total_tokens["input"]
    out = _total_tokens["output"]
    cached = _total_tokens["cached"]
    reasoning = _total_tokens["reasoning"]
    reqs = _total_tokens["requests"]
    print(
        f"\nTotal tokens: {inp} in ({cached} cached) / "
        f"{out} out ({reasoning} reasoning) — {reqs} requests\n"
    )


def reset_stats() -> None:
    """Reset all counters to zero (called on REPL ``clear`` command)."""
    global _total_tokens
    _total_tokens = {
        "input": 0,
        "output": 0,
        "reasoning": 0,
        "cached": 0,
        "requests": 0,
    }
