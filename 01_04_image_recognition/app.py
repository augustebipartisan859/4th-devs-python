# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Image Recognition Agent — classifies images from images/ into character folders
using knowledge profiles and vision analysis.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      app.js

"""

import asyncio
import sys
from pathlib import Path

# Make src importable as a package
sys.path.insert(0, str(Path(__file__).parent))

from src.mcp.client import create_mcp_client, list_mcp_tools
from src.native.tools import native_tools
from src.agent import run
from src.helpers.logger import log
from src.helpers.stats import log_stats

CLASSIFICATION_QUERY = (
    "Classify all images in the images/ folder based on the character knowledge files.\n"
    "Read the knowledge files first, then analyze each image and copy it to the "
    "appropriate character folder(s)."
)


async def main() -> None:
    """Main entry point — connect to MCP, run classification agent, print stats."""
    log.box("Image Recognition Agent\nClassify images by character")

    mcp_client = None

    try:
        log.start("Connecting to MCP server...")
        mcp_client = await create_mcp_client()
        mcp_tools = await list_mcp_tools(mcp_client)

        log.success(f"MCP: {', '.join(t.name for t in mcp_tools)}")
        log.success(f"Native: {', '.join(t['name'] for t in native_tools)}")

        log.start("Starting image classification...")
        result = await run(
            CLASSIFICATION_QUERY,
            mcp_client=mcp_client,
            mcp_tools=mcp_tools,
        )

        log.success("Classification complete")
        log.info(result["response"])
        log_stats()

    finally:
        if mcp_client is not None:
            try:
                await mcp_client.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)
    except Exception as e:
        log.error("Startup error", str(e))
        sys.exit(1)
