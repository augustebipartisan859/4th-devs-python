# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Audio Processing Agent - Main entry point

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      app.js

"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.mcp.client import create_mcp_client, list_mcp_tools
from src.native.tools import native_tools
from src.repl import run_repl
from src.helpers.logger import log
from src.helpers.stats import log_stats
from src.helpers.shutdown import on_shutdown


EXAMPLES = [
    "Transcribe the file from workspace/input/",
    "Generate audio: Welcome to our product demo",
    "Analyze the speech patterns in workspace/input/tech_briefing.wav",
    "What topics are discussed in this recording?",
]


def print_examples():
    """Print example queries."""
    log.heading("EXAMPLES", "For demo purposes, try these queries:")
    for example in EXAMPLES:
        log.example(example)
    log.hint("Type 'exit' to quit, 'clear' to reset conversation")


async def main():
    """Main entry point."""
    log.box("Audio Processing Agent")

    log.heading("TOOLS")
    for tool in native_tools:
        description = tool["description"].split(".")[0]
        print(f"{tool['name'].ljust(20)} — {description}")

    log.start("Connecting to MCP server...")
    mcp_client = await create_mcp_client()
    mcp_tools = await list_mcp_tools(mcp_client)
    log.success(f"MCP: {', '.join(t.name for t in mcp_tools)}")

    print_examples()

    # Setup shutdown handler
    async def cleanup():
        log_stats()
        await mcp_client.close()

    shutdown = on_shutdown(cleanup)

    # Run REPL
    await run_repl(mcp_client, mcp_tools)

    # Cleanup
    await cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)
    except Exception as e:
        log.error("Startup error", str(e))
        sys.exit(1)
