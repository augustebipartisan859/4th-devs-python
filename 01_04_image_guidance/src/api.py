# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API client — sends chat requests and extracts tool calls and text
from the response.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/api.js

"""

from typing import Any, Optional

import httpx

from .config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT, API_CONFIG
from .helpers.response import extract_response_text
from .helpers.stats import record_usage


async def chat(
    *,
    input_messages: list,
    tools: Optional[list] = None,
    tool_choice: str = "auto",
    model: Optional[str] = None,
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
) -> dict:
    """Send a request to the Responses API and return the raw response dict.

    Args:
        input_messages: Conversation history in Responses API format.
        tools: Optional tool definitions to expose to the model.
        tool_choice: How the model should choose tools (default ``"auto"``).
        model: Model override; uses ``API_CONFIG["model"]`` if omitted.
        instructions: System instructions override.
        max_output_tokens: Token limit override.

    Returns:
        Raw response dict from the Responses API.

    Raises:
        Exception: If the API returns an error status or error body.
    """
    _model = model or API_CONFIG["model"]
    _instructions = instructions if instructions is not None else API_CONFIG.get("instructions")
    _max_tokens = max_output_tokens or API_CONFIG.get("max_output_tokens")

    body: dict = {"model": _model, "input": input_messages}

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if _instructions:
        body["instructions"] = _instructions
    if _max_tokens:
        body["max_output_tokens"] = _max_tokens

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
        **EXTRA_API_HEADERS,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(RESPONSES_API_ENDPOINT, json=body, headers=headers)

    data = response.json()

    if not response.is_success or data.get("error"):
        msg = data.get("error", {}).get("message") or f"Responses API request failed ({response.status_code})"
        raise Exception(msg)

    record_usage(data.get("usage"))
    return data


def extract_tool_calls(response: dict) -> list:
    """Extract all function_call items from the response output.

    Args:
        response: Raw Responses API response dict.

    Returns:
        List of function_call dicts (may be empty).
    """
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def extract_text(response: dict) -> Optional[str]:
    """Extract the assistant's text reply from the response.

    Args:
        response: Raw Responses API response dict.

    Returns:
        Text string, or ``None`` if no text was found.
    """
    text = extract_response_text(response)
    return text if text else None
