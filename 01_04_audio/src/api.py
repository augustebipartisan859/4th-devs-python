# -*- coding: utf-8 -*-

#   api.py

"""
### Description:
Responses API client for chat completions with tool support.

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      api.js

"""

import json
import os
import sys
from typing import Any, Optional
from pathlib import Path

import httpx

from .config import API_CONFIG
from .helpers.stats import record_usage

# Get root config
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
try:
    from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT
except ImportError:
    # Fallback defaults
    AI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    EXTRA_API_HEADERS = {}
    RESPONSES_API_ENDPOINT = "https://api.openai.com/v1/responses"


def extract_response_text(data: dict) -> str:
    """Extract text from API response."""
    if isinstance(data.get("output_text"), str) and data.get("output_text", "").strip():
        return data["output_text"]

    messages = [item for item in (data.get("output") or []) if item.get("type") == "message"]

    for message in messages:
        content = message.get("content") or []
        for part in content:
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return part["text"]

    return ""


async def chat(
    model: str = API_CONFIG["model"],
    input_messages: Optional[list] = None,
    tools: Optional[list] = None,
    tool_choice: str = "auto",
    instructions: str = API_CONFIG["instructions"],
    max_output_tokens: int = API_CONFIG["max_output_tokens"],
) -> dict:
    """
    Call the Responses API for chat completion.

    Args:
        model: Model name
        input_messages: List of messages
        tools: Available tools
        tool_choice: Tool choice mode
        instructions: System instructions
        max_output_tokens: Max tokens in response

    Returns:
        API response dictionary
    """
    body = {"model": model, "input": input_messages or []}

    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    if instructions:
        body["instructions"] = instructions
    if max_output_tokens:
        body["max_output_tokens"] = max_output_tokens

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=body,
            timeout=120.0,
        )

        data = response.json()

        if not response.is_success or data.get("error"):
            error_msg = data.get("error", {}).get("message") or f"API request failed ({response.status_code})"
            raise Exception(error_msg)

        record_usage(data.get("usage", {}))
        return data


def extract_tool_calls(response: dict) -> list:
    """Extract tool calls from API response."""
    output = response.get("output") or []
    return [item for item in output if item.get("type") == "function_call"]


def extract_text(response: dict) -> Optional[str]:
    """Extract text from API response."""
    text = extract_response_text(response)
    return text or None
