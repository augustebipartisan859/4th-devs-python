# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
JSON Image Agent — interactive terminal REPL that combines MCP file tools
with JSON-based token-efficient image generation using Gemini or OpenRouter.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      app.js

"""

import asyncio
import sys

from src.mcp.client import create_mcp_client, list_mcp_tools
from src.native.tools import native_tools
from src.repl import run_repl
from src.helpers.shutdown import on_shutdown
from src.helpers.stats import log_stats
from src.helpers.logger import log

EXAMPLES = [
    "Generate a phoenix rising from flames",
    "Create a cyberpunk hacker with neon implants using character-template.json",
    "Generate a steampunk pocket watch with exposed gears",
    "Create a medieval market stall selling magical artifacts",
]


def _confirm_run() -> None:
    """Prompt the user to confirm before starting (may incur API costs)."""
    print(
        "\n⚠️  UWAGA: Uruchomienie tego agenta może zużyć zauważalną liczbę tokenów i wygenerować obrazy."
    )
    print("   Agent używa szablonów JSON do efektywnego generowania obrazów.")
    print("   Szablony dostępne w: workspace/template.json, workspace/character-template.json")
    print("")

    answer = input("Czy chcesz kontynuować? (yes/y): ").strip().lower()
    if answer not in ("yes", "y"):
        print("Przerwano.")
        sys.exit(0)


def _print_tools() -> None:
    log.heading("TOOLS")
    for tool in native_tools:
        name = tool["name"].ljust(14)
        desc = tool["description"].split(".")[0]
        log.info(f"{name} — {desc}")


def _print_examples() -> None:
    log.heading("EXAMPLES", "Try these subject descriptions:")
    for example in EXAMPLES:
        log.example(example)
    log.hint("Type 'exit' to quit, 'clear' to reset conversation")


async def main() -> None:
    log.box("JSON Image Agent\nType 'exit' to quit, 'clear' to reset")
    _confirm_run()
    _print_tools()

    mcp_client = None

    try:
        log.start("Connecting to MCP server...")
        mcp_client = await create_mcp_client()
        mcp_tools = await list_mcp_tools(mcp_client)
        log.success(f"MCP: {', '.join(t.name for t in mcp_tools)}")

        _print_examples()

        async def cleanup() -> None:
            log_stats()
            if mcp_client:
                await mcp_client.close()

        shutdown = on_shutdown(cleanup)

        await run_repl(mcp_client=mcp_client, mcp_tools=mcp_tools)
        await shutdown()

    except Exception as error:
        if mcp_client:
            try:
                await mcp_client.close()
            except Exception:
                pass
        raise error


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        log.error("Startup error", str(err))
        sys.exit(1)
