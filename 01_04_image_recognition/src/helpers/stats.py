# -*- coding: utf-8 -*-

#   stats.py

"""
### Description:
Token usage and API call statistics tracker.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/stats.js

"""

# Module-level token tracking state
_total_tokens: dict = {"input": 0, "output": 0, "requests": 0}


def record_usage(usage: dict) -> None:
    """Record token usage from an API response.

    Args:
        usage: Usage dict from API response containing input_tokens and output_tokens.
    """
    if not usage:
        return
    _total_tokens["input"] += usage.get("input_tokens", 0)
    _total_tokens["output"] += usage.get("output_tokens", 0)
    _total_tokens["requests"] += 1


def get_stats() -> dict:
    """Return a copy of the current token statistics.

    Returns:
        Dict with input, output, and requests counts.
    """
    return _total_tokens.copy()


def log_stats() -> None:
    """Print a summary of token usage statistics to stdout."""
    input_tokens = _total_tokens["input"]
    output_tokens = _total_tokens["output"]
    requests = _total_tokens["requests"]
    print(
        f"\n📊 Stats: {requests} requests, {input_tokens} input tokens, "
        f"{output_tokens} output tokens, {input_tokens + output_tokens} total\n"
    )


def reset_stats() -> None:
    """Reset all token statistics to zero."""
    _total_tokens["input"] = 0
    _total_tokens["output"] = 0
    _total_tokens["requests"] = 0
