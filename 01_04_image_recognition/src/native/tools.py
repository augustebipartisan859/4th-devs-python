# -*- coding: utf-8 -*-

#   tools.py

"""
### Description:
Native tool definitions and handlers for image understanding via vision API.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/tools.js

"""

import base64
from pathlib import Path
from typing import Any

from .vision import vision
from ..helpers.logger import log

# Module root: src/native/ → src/ → module root
PROJECT_ROOT = Path(__file__).parent.parent.parent

_MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _get_mime_type(filepath: str) -> str:
    """Return the MIME type for an image file path.

    Args:
        filepath: File path string used to determine extension.

    Returns:
        MIME type string; defaults to ``"image/jpeg"`` for unknown extensions.
    """
    ext = Path(filepath).suffix.lower()
    return _MIME_TYPES.get(ext, "image/jpeg")


# Tool definition in OpenAI function-calling format
native_tools: list[dict] = [
    {
        "type": "function",
        "name": "understand_image",
        "description": (
            "Analyze an image and answer questions about it. "
            "Use this to identify people, objects, scenes, or any visual content in images."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": (
                        "Path to the image file relative to the project root "
                        "(e.g., 'images/photo.jpg')"
                    ),
                },
                "question": {
                    "type": "string",
                    "description": (
                        "Question to ask about the image "
                        "(e.g., 'Who is in this image?', 'Describe the person\\'s appearance')"
                    ),
                },
            },
            "required": ["image_path", "question"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


async def _understand_image_handler(image_path: str, question: str) -> dict:
    """Execute the understand_image tool.

    Args:
        image_path: Path to image relative to project root.
        question: Question to ask about the image.

    Returns:
        Dict with ``answer`` and ``image_path`` on success, or ``error`` and ``image_path``.
    """
    full_path = PROJECT_ROOT / image_path
    log.vision(image_path, question)

    try:
        image_bytes = full_path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = _get_mime_type(image_path)

        answer = await vision(
            image_base64=image_base64,
            mime_type=mime_type,
            question=question,
        )

        log.vision_result(answer)
        return {"answer": answer, "image_path": image_path}

    except Exception as e:
        log.error("Vision error", str(e))
        return {"error": str(e), "image_path": image_path}


_native_handlers: dict = {
    "understand_image": _understand_image_handler,
}


def is_native_tool(name: str) -> bool:
    """Check whether a tool name is handled natively (not via MCP).

    Args:
        name: Tool name.

    Returns:
        ``True`` if the tool has a native handler.
    """
    return name in _native_handlers


async def execute_native_tool(name: str, args: dict) -> Any:
    """Dispatch a native tool call to the appropriate handler.

    Args:
        name: Tool name to execute.
        args: Arguments dict for the tool.

    Returns:
        Tool handler result.

    Raises:
        ValueError: If the tool name has no registered handler.
    """
    handler = _native_handlers.get(name)
    if not handler:
        raise ValueError(f"Unknown native tool: {name}")
    return await handler(**args)
