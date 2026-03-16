# -*- coding: utf-8 -*-

#   report.py

"""
### Description:
Parser for structured VERDICT/SCORE/BLOCKING_ISSUES/MINOR_ISSUES/NEXT_PROMPT_HINT
analysis reports returned by the vision model.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/analyze-image/report.js

"""

import re
from typing import Optional


def _extract_tagged_value(text: str, tag: str) -> str:
    match = re.search(rf"^{tag}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_bullet_section(text: str, section: str) -> list:
    """Extract bullet items from a named section in the analysis report.

    Args:
        text: Full analysis text.
        section: Section header name (e.g. ``"BLOCKING_ISSUES"``).

    Returns:
        List of bullet item strings.
    """
    lines = text.split("\n")
    header = f"{section}:"
    start_index = next(
        (i for i, line in enumerate(lines) if line.strip().upper() == header),
        -1,
    )

    if start_index == -1:
        return []

    items = []
    for line in lines[start_index + 1:]:
        trimmed = line.strip()
        if not trimmed:
            continue
        # Stop at the next section header (ALL_CAPS word(s) followed by colon)
        if re.match(r"^[A-Z_ ]+:$", trimmed):
            break
        if trimmed.startswith("- "):
            items.append(trimmed[2:].strip())

    return items


def parse_analysis_report(analysis: str) -> dict:
    """Parse a structured analysis report into a normalized dict.

    Args:
        analysis: Raw analysis text from the vision model.

    Returns:
        Dict with ``verdict``, ``score``, ``blockingIssues``, ``minorIssues``,
        and ``nextPromptHints`` keys.
    """
    raw_verdict = _extract_tagged_value(analysis, "VERDICT").upper()
    score_text = _extract_tagged_value(analysis, "SCORE")

    try:
        score: Optional[int] = int(score_text)
    except (ValueError, TypeError):
        score = None

    return {
        "verdict": "retry" if raw_verdict == "RETRY" else "accept",
        "score": score,
        "blockingIssues": _extract_bullet_section(analysis, "BLOCKING_ISSUES"),
        "minorIssues": _extract_bullet_section(analysis, "MINOR_ISSUES"),
        "nextPromptHints": _extract_bullet_section(analysis, "NEXT_PROMPT_HINT"),
    }
