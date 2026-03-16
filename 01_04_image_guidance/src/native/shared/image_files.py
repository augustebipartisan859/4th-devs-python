# -*- coding: utf-8 -*-

#   image_files.py

"""
### Description:
Shared image file utilities — loading reference images, reading project images,
and saving generated images to workspace/output/.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/shared/image-files.js

"""

import asyncio
import base64
import time
from pathlib import Path
from typing import Any

# Module root: src/native/shared/ → src/native/ → src/ → module root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

_MIME_MAP: dict = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

_EXT_MAP: dict = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def get_mime_type(filepath: str) -> str:
    """Return the MIME type for a file path based on its extension.

    Args:
        filepath: File path string (relative or absolute).

    Returns:
        MIME type string, defaulting to ``"image/png"``.
    """
    return _MIME_MAP.get(Path(filepath).suffix.lower(), "image/png")


def _get_extension(mime_type: str) -> str:
    return _EXT_MAP.get(mime_type, ".png")


async def load_reference_images(reference_images: list) -> list:
    """Load reference images from workspace-relative paths and encode as base64.

    Args:
        reference_images: List of workspace-relative path strings.

    Returns:
        List of dicts with ``data`` (base64 str) and ``mimeType`` keys.
    """
    async def _load(image_path: str) -> dict:
        full_path = _PROJECT_ROOT / image_path
        image_bytes = await asyncio.get_event_loop().run_in_executor(
            None, full_path.read_bytes
        )
        return {
            "data": base64.b64encode(image_bytes).decode(),
            "mimeType": get_mime_type(image_path),
        }

    return list(await asyncio.gather(*[_load(p) for p in reference_images]))


def read_project_image(image_path: str) -> dict:
    """Read a project image synchronously and return base64-encoded data.

    Args:
        image_path: Workspace-relative path to the image.

    Returns:
        Dict with ``imageBase64`` (str) and ``mimeType`` (str) keys.
    """
    full_path = _PROJECT_ROOT / image_path
    image_bytes = full_path.read_bytes()
    return {
        "imageBase64": base64.b64encode(image_bytes).decode(),
        "mimeType": get_mime_type(image_path),
    }


def save_generated_image(output_name: str, result: dict) -> str:
    """Save a generated image to workspace/output/ with a timestamped filename.

    Args:
        output_name: Base filename prefix (no extension).
        result: Dict with ``data`` (base64 str) and ``mimeType`` keys.

    Returns:
        Workspace-relative path string for the saved file.
    """
    output_dir = _PROJECT_ROOT / "workspace" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ext = _get_extension(result["mimeType"])
    filename = f"{output_name}_{int(time.time() * 1000)}{ext}"
    output_path = output_dir / filename

    output_path.write_bytes(base64.b64decode(result["data"]))
    return f"workspace/output/{filename}"
