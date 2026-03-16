# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool registry — aggregates definitions and handlers for create_image
and analyze_image tools and exposes a unified dispatch interface.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/tools.js

"""

from .create_image.definition import create_image_definition
from .create_image.handler import create_image
from .analyze_image.definition import analyze_image_definition
from .analyze_image.handler import analyze_image

# All native tool definitions in OpenAI function format
native_tools: list = [create_image_definition, analyze_image_definition]

_NATIVE_HANDLERS: dict = {
    "create_image": create_image,
    "analyze_image": analyze_image,
}


def is_native_tool(name: str) -> bool:
    """Return ``True`` if ``name`` is a known native (non-MCP) tool.

    Args:
        name: Tool name to check.
    """
    return name in _NATIVE_HANDLERS


async def execute_native_tool(name: str, args: dict) -> dict:
    """Dispatch a native tool call by name.

    Args:
        name: Tool name to invoke.
        args: Arguments dict for the tool.

    Returns:
        Tool result dict.

    Raises:
        Exception: If ``name`` is not a known native tool.
    """
    handler = _NATIVE_HANDLERS.get(name)
    if not handler:
        raise Exception(f"Unknown native tool: {name}")
    return await handler(**args)
