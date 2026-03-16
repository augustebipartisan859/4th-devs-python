# -*- coding: utf-8 -*-

#   agent.py

"""
### Description:
Core agentic loop for the RAG agent. Executes the chat → tool call → result
cycle for up to MAX_STEPS iterations, then returns the final text response
together with the updated conversation history for multi-turn use.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/agent.js

"""

import asyncio
import json
import logging
from typing import Any

from mcp import ClientSession

from .helpers.api import chat, extract_reasoning, extract_text, extract_tool_calls
from .helpers.logger import log
from .mcp.client import call_mcp_tool, mcp_tools_to_openai

logger = logging.getLogger(__name__)

# Maximum number of chat→tool→result iterations before giving up
MAX_STEPS: int = 50


def create_conversation() -> dict:
    """Return a fresh conversation state dict.

    Returns:
        Dict with ``history`` key containing an empty list.
    """
    return {"history": []}


async def _run_tool(
    client: ClientSession,
    tool_call: dict,
) -> dict:
    """Execute a single tool call and return a ``function_call_output`` item.

    Errors are caught and returned as JSON-encoded error messages rather than
    raised — this mirrors the JS behaviour where a failing tool never aborts
    the step, allowing the model to observe the error and decide how to react.

    Args:
        client: Connected MCP ``ClientSession``.
        tool_call: A ``function_call`` item from the API response ``output``.

    Returns:
        A ``function_call_output`` dict ready to append to the message list.
    """
    name: str = tool_call.get("name", "")
    call_id: str = tool_call.get("call_id", "")

    # Arguments arrive as a JSON string from the Responses API
    try:
        args: dict = json.loads(tool_call.get("arguments", "{}"))
    except (json.JSONDecodeError, ValueError):
        args = {}

    log.tool(name, args)

    try:
        result = await call_mcp_tool(client, name, args)
        output_str = json.dumps(result) if not isinstance(result, str) else result
        log.tool_result(name, True, output_str)
        return {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output_str,
        }
    except Exception as exc:
        error_msg = json.dumps({"error": str(exc)})
        log.tool_result(name, False, error_msg)
        return {
            "type": "function_call_output",
            "call_id": call_id,
            "output": error_msg,
        }


async def run(
    query: str,
    *,
    mcp_client: ClientSession,
    mcp_tools: list,
    conversation_history: list,
) -> dict:
    """Run the agentic loop for a single user query.

    Appends *query* to *conversation_history*, then iterates the
    chat→tool→result cycle until the model returns a plain text response
    (no pending tool calls) or ``MAX_STEPS`` is reached.

    Tool calls within a single step are executed in parallel via
    ``asyncio.gather``, mirroring the ``Promise.all`` in the JS original.

    Args:
        query: The user's question or instruction.
        mcp_client: Connected MCP ``ClientSession`` for tool execution.
        mcp_tools: Raw MCP tool list from ``list_mcp_tools()``.
        conversation_history: Existing message list to extend. Modified in
            place and also returned so callers can re-use it.

    Returns:
        Dict with keys:
        - ``response`` (str): The agent's final answer.
        - ``conversation_history`` (list): Updated message list.

    Raises:
        RuntimeError: If ``MAX_STEPS`` is exhausted without a final answer.
    """
    openai_tools = mcp_tools_to_openai(mcp_tools)

    # Append the new user turn to the shared history
    messages: list = list(conversation_history)
    messages.append({"role": "user", "content": query})

    for step in range(1, MAX_STEPS + 1):
        log.api(f"Step {step}", len(messages))

        response = await chat(input=messages, tools=openai_tools)

        # Log any reasoning summaries the model produced
        for summary in extract_reasoning(response):
            log.reasoning(summary)

        tool_calls = extract_tool_calls(response)

        if not tool_calls:
            # No tool calls → the model has a final answer; return it
            final_text = extract_text(response)

            # Persist the full response output items into history so future
            # turns have the complete context (reasoning + message items)
            messages.extend(response.get("output") or [])
            return {"response": final_text, "conversation_history": messages}

        # Append all response output items (tool call records) to messages
        messages.extend(response.get("output") or [])

        # Execute all tool calls in this step in parallel
        tool_results = await asyncio.gather(
            *[_run_tool(mcp_client, tc) for tc in tool_calls]
        )
        messages.extend(tool_results)

    raise RuntimeError(
        f"Agent did not produce a final answer within {MAX_STEPS} steps."
    )
