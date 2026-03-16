# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Agentic loop — drives chat → tool calls → results until the model stops
issuing tool calls or MAX_STEPS is reached.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/agent.js

"""

import asyncio
import json
from typing import Optional

from .api import chat, extract_tool_calls, extract_text
from .mcp.client import call_mcp_tool, mcp_tools_to_openai
from .native.tools import native_tools, is_native_tool, execute_native_tool
from .helpers.logger import log

MAX_STEPS: int = 100


async def _run_tool(mcp_client, tool_call: dict) -> dict:
    """Execute a single tool call and return the output message.

    Args:
        mcp_client: Initialised MCP ``ClientSession``.
        tool_call: Function call dict from the Responses API output.

    Returns:
        ``function_call_output`` dict ready to append to the message list.
    """
    args = json.loads(tool_call.get("arguments", "{}"))
    log.tool(tool_call["name"], args)

    try:
        if is_native_tool(tool_call["name"]):
            result = await execute_native_tool(tool_call["name"], args)
        else:
            result = await call_mcp_tool(mcp_client, tool_call["name"], args)

        output = json.dumps(result)
        log.tool_result(tool_call["name"], True, output)

    except Exception as e:
        output = json.dumps({"error": str(e)})
        log.tool_result(tool_call["name"], False, str(e))

    return {
        "type": "function_call_output",
        "call_id": tool_call["call_id"],
        "output": output,
    }


async def _run_tools(mcp_client, tool_calls: list) -> list:
    """Execute multiple tool calls in parallel.

    Args:
        mcp_client: Initialised MCP ``ClientSession``.
        tool_calls: List of function call dicts.

    Returns:
        List of ``function_call_output`` dicts.
    """
    return list(await asyncio.gather(*[_run_tool(mcp_client, tc) for tc in tool_calls]))


async def run(
    query: str,
    mcp_client=None,
    mcp_tools: Optional[list] = None,
) -> dict:
    """Run the agentic loop until the model issues a final text response.

    Args:
        query: Initial user query to classify images.
        mcp_client: Initialised MCP ``ClientSession`` for file operations.
        mcp_tools: List of MCP tool definitions from ``list_mcp_tools``.

    Returns:
        Dict with ``response`` key containing the final model text.

    Raises:
        Exception: If ``MAX_STEPS`` is reached without a final response.
    """
    if mcp_tools is None:
        mcp_tools = []

    tools = mcp_tools_to_openai(mcp_tools) + native_tools
    messages: list = [{"role": "user", "content": query}]

    log.query(query)

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))
        response = await chat(input_messages=messages, tools=tools)
        log.api_done(response.get("usage"))

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            text = extract_text(response) or "No response"
            return {"response": text}

        messages.extend(response.get("output", []))

        results = await _run_tools(mcp_client, tool_calls)
        messages.extend(results)

    raise Exception(f"Max steps ({MAX_STEPS}) reached")
