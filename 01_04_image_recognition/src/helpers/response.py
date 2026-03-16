# -*- coding: utf-8 -*-

#   response.py

"""
### Description:
Helpers for extracting text content from Responses API output objects.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/response.js

"""


def extract_response_text(data: dict) -> str:
    """Extract text from a Responses API response dict.

    Args:
        data: Raw API response dictionary.

    Returns:
        Extracted text string, or empty string if not found.
    """
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]

    output = data.get("output") or []
    messages = [item for item in output if isinstance(item, dict) and item.get("type") == "message"]

    for message in messages:
        content = message.get("content") or []
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                return part["text"]

    return ""
