# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Entry point for the agentic RAG example. Warns about token cost, requires
explicit user confirmation, spawns the MCP file server, and starts the
interactive REPL. Handles graceful shutdown on exit or SIGINT/SIGTERM.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      app.js

"""

import asyncio
import sys
from pathlib import Path

# Ensure root config.py is importable when running as `python app.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.helpers.logger import log
from src.helpers.shutdown import on_shutdown
from src.helpers.stats import log_stats
from src.mcp.client import close_mcp_client, create_mcp_client, list_mcp_tools
from src.repl import run_repl

# ---------------------------------------------------------------------------
# Cost warning — this agent can burn many tokens per session
# ---------------------------------------------------------------------------
_WARNING = """
╔══════════════════════════════════════════════════════════╗
║  ⚠  TOKEN COST WARNING                                   ║
║                                                          ║
║  This agent uses reasoning + multi-step tool loops       ║
║  (up to 50 steps per query) and can consume a large      ║
║  number of tokens in a single session.                   ║
║                                                          ║
║  Type  yes  or  y  to continue.                          ║
╚══════════════════════════════════════════════════════════╝
"""


async def _confirm_run() -> bool:
    """Print cost warning and ask for explicit confirmation.

    Returns:
        ``True`` if the user typed ``yes`` or ``y``, ``False`` otherwise.
    """
    print(_WARNING)
    answer: str = await asyncio.to_thread(input, "Proceed? ")
    return answer.strip().lower() in ("yes", "y")


async def main() -> None:
    """Bootstrap the application and run the REPL."""
    if not await _confirm_run():
        print("Aborted.")
        return

    mcp_client = None
    exit_stack = None

    async def cleanup() -> None:
        log_stats()
        if exit_stack is not None:
            await close_mcp_client(exit_stack)
        log.info("Goodbye.")

    # Register SIGINT/SIGTERM handlers. The returned coroutine has an
    # idempotency guard (shutting_down flag) — call it for both signal-
    # triggered and normal-exit paths so cleanup runs exactly once.
    shutdown_handler = on_shutdown(cleanup)

    try:
        log.start("Connecting to MCP file server…")
        mcp_client, exit_stack = await create_mcp_client("files")

        mcp_tools = await list_mcp_tools(mcp_client)
        tool_names = [t.name for t in mcp_tools]
        log.success(f"Discovered {len(tool_names)} MCP tool(s): {', '.join(tool_names)}")

        log.box("Agentic RAG — knowledge base explorer\nType 'exit' to quit, 'clear' to reset.")

        await run_repl(mcp_client=mcp_client, mcp_tools=mcp_tools)

    except Exception as exc:
        log.error("Fatal error", str(exc))
        raise
    finally:
        # Use the shutdown_handler (not cleanup directly) so the
        # shutting_down flag prevents double-execution on SIGINT + normal exit
        await shutdown_handler()


if __name__ == "__main__":
    asyncio.run(main())
