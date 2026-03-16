# -*- coding: utf-8 -*-

#   response.py

"""
### Description:
Utility for extracting text from Responses API response objects.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/response.js

"""

from typing import Any, Optional


def extract_response_text(data: Any) -> str:
    """Extract the assistant's text from a Responses API response dict.

    Args:
        data: Raw response dict from the Responses API.

    Returns:
        Extracted text string, or empty string if none found.
    """
    # Fast path: top-level output_text field
    if isinstance(data, dict):
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

    # Walk output array looking for message items with output_text content parts
    output = data.get("output", []) if isinstance(data, dict) else []
    messages = [item for item in output if isinstance(item, dict) and item.get("type") == "message"]

    for message in messages:
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                return part["text"]

    return ""
