# -*- coding: utf-8 -*-

#   repl.py

"""
### Description:
Interactive REPL (Read-Evaluate-Print Loop) for the agentic RAG agent.
Maintains full conversation history across user turns so follow-up questions
work correctly. Supports ``exit`` and ``clear`` commands.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/repl.js

"""

import asyncio
import logging

from mcp import ClientSession

from .agent import create_conversation, run
from .helpers.logger import log
from .helpers.stats import reset_stats

logger = logging.getLogger(__name__)


async def run_repl(*, mcp_client: ClientSession, mcp_tools: list) -> None:
    """Run the interactive REPL until the user types ``exit``.

    Reads user input asynchronously (via ``asyncio.to_thread`` so the event
    loop is not blocked), dispatches each query to the agent, and prints the
    final response. The conversation object accumulates history across turns
    so multi-turn follow-up questions work correctly.

    Supported commands:
    - ``exit`` — break the loop and return to ``app.py``.
    - ``clear`` — reset conversation history and token stats.
    - ``<any text>`` — treated as a user query to the agent.

    Args:
        mcp_client: Connected MCP ``ClientSession``.
        mcp_tools: Raw MCP tool list from ``list_mcp_tools()``.
    """
    conversation = create_conversation()

    while True:
        try:
            # Run blocking input() in a thread so the event loop stays free
            user_input: str = await asyncio.to_thread(input, "You: ")
        except EOFError:
            # EOF (e.g. piped input exhausted) — treat as exit
            user_input = "exit"

        user_input = user_input.strip()

        if user_input == "exit":
            break

        if user_input == "clear":
            conversation = create_conversation()
            reset_stats()
            log.success("Conversation and stats cleared.")
            continue

        if not user_input:
            continue

        log.query(user_input)

        try:
            result = await run(
                user_input,
                mcp_client=mcp_client,
                mcp_tools=mcp_tools,
                conversation_history=conversation["history"],
            )
            # Persist updated history for the next turn
            conversation["history"] = result["conversation_history"]

            print(f"\nAssistant: {result['response']}\n")

        except Exception as exc:
            log.error("Agent error", str(exc))
            logger.exception("Unexpected error during agent run")
