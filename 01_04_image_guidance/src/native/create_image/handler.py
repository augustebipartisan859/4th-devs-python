# -*- coding: utf-8 -*-

#   handler.py

"""
### Description:
Handler for the create_image native tool — loads reference images, calls the
Gemini backend, and saves the result to workspace/output/.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/create-image/handler.js

"""

from typing import Optional

from .gemini import edit_image, edit_image_with_references, generate_image
from ..shared.image_files import load_reference_images, save_generated_image
from ...helpers.logger import log


def _build_options(aspect_ratio: Optional[str], image_size: Optional[str]) -> dict:
    options: dict = {}
    if aspect_ratio:
        options["aspectRatio"] = aspect_ratio
    if image_size:
        options["imageSize"] = image_size
    return options


async def create_image(
    *,
    prompt: str,
    output_name: str,
    reference_images: list,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
) -> dict:
    """Generate or edit an image and save it to workspace/output/.

    Args:
        prompt: Generation prompt or editing instructions.
        output_name: Base filename prefix (no extension).
        reference_images: Workspace-relative paths to source images for editing.
        aspect_ratio: Optional aspect ratio string.
        image_size: Optional image size string.

    Returns:
        Dict describing the result (success, mode, output_path, etc.).
    """
    try:
        options = _build_options(aspect_ratio, image_size)

        if not reference_images:
            result = await generate_image(prompt, options)
            mode = "generate"
        else:
            loaded = await load_reference_images(reference_images)
            if len(loaded) == 1:
                result = await edit_image(prompt, loaded[0]["data"], loaded[0]["mimeType"], options)
            else:
                result = await edit_image_with_references(prompt, loaded, options)
            mode = "edit"

        output_path = save_generated_image(output_name, result)
        log.success(f"Image saved: {output_path}")

        return {
            "success": True,
            "mode": mode,
            "output_path": output_path,
            "mime_type": result["mimeType"],
            "prompt_used": prompt,
            "reference_images": reference_images or [],
        }

    except Exception as error:
        log.error("create_image", str(error))
        return {"success": False, "error": str(error)}
