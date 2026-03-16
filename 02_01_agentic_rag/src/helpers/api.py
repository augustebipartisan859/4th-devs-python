# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Thin async wrapper around the OpenAI Responses API (or OpenRouter equivalent).
Sends requests via httpx, extracts tool calls / text / reasoning from the
structured ``output`` array, and records token usage via the stats module.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      helpers/api.js

"""

import sys
import json
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

# Root config provides API key, endpoint, and extra headers
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import AI_API_KEY, RESPONSES_API_ENDPOINT, EXTRA_API_HEADERS

# Module config provides default model and generation settings
from ..config import api as api_config
from .stats import record_usage
from .logger import log

logger = logging.getLogger(__name__)


async def chat(
    *,
    model: Optional[str] = None,
    input: list,
    tools: Optional[list] = None,
    tool_choice: Optional[str] = None,
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    reasoning: Optional[dict] = None,
) -> dict:
    """Send a request to the OpenAI Responses API and return the raw response.

    Uses module-level defaults from ``src/config.py`` for any omitted params.

    Args:
        model: Model identifier. Defaults to ``api_config.model``.
        input: The full message/history array (Responses API ``input`` field).
        tools: List of function tool definitions in OpenAI format.
        tool_choice: Tool-choice constraint (e.g. ``"auto"``).
        instructions: System prompt / instructions string.
        max_output_tokens: Max tokens to generate.
        reasoning: Reasoning config dict, e.g. ``{"effort": "medium"}``.

    Returns:
        Parsed JSON response dict from the API.

    Raises:
        RuntimeError: If the API returns an error field.
    """
    body: dict[str, Any] = {
        "model": model or api_config["model"],
        "input": input,
    }

    effective_instructions = instructions or api_config.get("instructions")
    if effective_instructions:
        body["instructions"] = effective_instructions

    effective_max_tokens = max_output_tokens or api_config.get("maxOutputTokens")
    if effective_max_tokens:
        body["max_output_tokens"] = effective_max_tokens

    effective_reasoning = reasoning or api_config.get("reasoning")
    if effective_reasoning:
        body["reasoning"] = effective_reasoning

    if tools:
        body["tools"] = tools
        # Default to "auto" when tools are provided, matching JS behaviour
        body["tool_choice"] = tool_choice or "auto"
    elif tool_choice:
        body["tool_choice"] = tool_choice

    log.api(f"Step {len(input)} messages", len(input))

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        **EXTRA_API_HEADERS,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            RESPONSES_API_ENDPOINT,
            headers=headers,
            content=json.dumps(body),
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")

    # Accumulate token usage for session stats
    if "usage" in data:
        record_usage(data["usage"])
        log.api_done(data["usage"])

    return data


def extract_tool_calls(response: dict) -> list:
    """Return all ``function_call`` items from the response ``output`` array.

    Args:
        response: Parsed API response dict.

    Returns:
        List of function_call output items (may be empty).
    """
    return [
        item
        for item in (response.get("output") or [])
        if item.get("type") == "function_call"
    ]


def extract_text(response: dict) -> str:
    """Return the text content of the first ``message`` item in ``output``.

    Args:
        response: Parsed API response dict.

    Returns:
        Text string, or empty string if no message output found.
    """
    for item in response.get("output") or []:
        if item.get("type") == "message":
            for content in item.get("content") or []:
                if content.get("type") == "output_text":
                    return content.get("text", "")
    return ""


def extract_reasoning(response: dict) -> list[str]:
    """Collect reasoning summary text strings from the ``output`` array.

    The Responses API returns ``reasoning`` items with a ``summary`` list of
    ``{type: "summary_text", text: "..."}`` objects when reasoning is enabled.

    Args:
        response: Parsed API response dict.

    Returns:
        List of reasoning summary text strings (may be empty).
    """
    summaries: list[str] = []
    for item in response.get("output") or []:
        if item.get("type") == "reasoning":
            for entry in item.get("summary") or []:
                if entry.get("type") == "summary_text" and entry.get("text"):
                    summaries.append(entry["text"])
    return summaries
