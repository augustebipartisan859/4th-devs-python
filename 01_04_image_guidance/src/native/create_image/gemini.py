# -*- coding: utf-8 -*-

#   gemini.py

"""
### Description:
Image generation wrapper with OpenRouter and native Gemini backends.
Dispatches generate/edit requests to the appropriate backend based on
the IMAGE_BACKEND setting in config.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/create-image/gemini.js

"""

import re
from typing import Any, Optional

import httpx

from ...config import GEMINI_CONFIG, OPENROUTER_API_KEY, EXTRA_API_HEADERS
from ...helpers.stats import record_gemini
from ...helpers.logger import log


def _normalize_image_size(image_size: Optional[str]) -> Optional[str]:
    """Normalize image size: convert trailing lowercase 'k' to uppercase 'K'.

    Args:
        image_size: Size string like ``"2k"`` or ``"4K"``.

    Returns:
        Normalized string, or the original value unchanged.
    """
    if isinstance(image_size, str) and image_size.endswith("k"):
        return image_size[:-1] + "K"
    return image_size


def _build_image_config(options: dict) -> Optional[dict]:
    """Build the image_config dict from generation options.

    Args:
        options: Dict with optional ``aspectRatio`` and ``imageSize`` keys.

    Returns:
        Dict with ``aspect_ratio`` / ``image_size`` keys, or ``None`` if empty.
    """
    image_config: dict = {}

    if options.get("aspectRatio"):
        image_config["aspect_ratio"] = options["aspectRatio"]
    if options.get("imageSize"):
        image_config["image_size"] = _normalize_image_size(options["imageSize"])

    return image_config if image_config else None


def _extract_native_text(interaction: dict) -> str:
    outputs = interaction.get("outputs") or []
    text_output = next((o for o in outputs if o.get("type") == "text"), None)
    return (text_output.get("text") or "").strip() if text_output else ""


def _extract_native_image(interaction: dict, action_label: str) -> dict:
    """Extract the image output from a native Gemini interaction response.

    Raises:
        Exception: If no image output was found.
    """
    outputs = interaction.get("outputs") or []
    image_output = next((o for o in outputs if o.get("type") == "image"), None)

    if not image_output:
        message = _extract_native_text(interaction)
        raise Exception(
            f"{action_label} failed: {message}"
            if message
            else "No image output received from image backend"
        )

    return {
        "data": image_output["data"],
        "mimeType": image_output.get("mime_type") or "image/png",
    }


def _extract_openrouter_text(data: dict) -> str:
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in content
        ).strip()
    return ""


def _parse_data_url(data_url: str) -> dict:
    """Parse a base64 data URL into mimeType and data components.

    Args:
        data_url: String like ``"data:image/png;base64,<data>"``.

    Returns:
        Dict with ``mimeType`` and ``data`` keys.

    Raises:
        Exception: If the URL does not match the expected format.
    """
    match = re.match(r"^data:([^;]+);base64,(.+)$", data_url or "", re.DOTALL)
    if not match:
        raise Exception("Expected OpenRouter image output as a base64 data URL")
    return {"mimeType": match.group(1), "data": match.group(2)}


def _extract_openrouter_image(data: dict, action_label: str) -> dict:
    """Extract the image from an OpenRouter response.

    Raises:
        Exception: If no image was found.
    """
    images = (data.get("choices") or [{}])[0].get("message", {}).get("images") or []
    image_url = (
        (images[0].get("image_url") or {}).get("url")
        or (images[0].get("imageUrl") or {}).get("url")
        if images
        else None
    )

    if not image_url:
        message = _extract_openrouter_text(data)
        raise Exception(
            f"{action_label} failed: {message}"
            if message
            else "No image output received from OpenRouter"
        )

    return _parse_data_url(image_url)


async def _create_native_interaction(
    prompt: Any,
    reference_images: list,
    image_config: Optional[dict],
) -> dict:
    """POST to the native Gemini Interactions endpoint.

    Args:
        prompt: Text prompt string.
        reference_images: List of dicts with ``data`` and ``mimeType`` keys.
        image_config: Optional generation config dict.

    Returns:
        Raw Gemini interaction response dict.
    """
    if reference_images:
        input_payload: Any = [
            {"type": "text", "text": prompt},
            *[
                {"type": "image", "data": img["data"], "mime_type": img["mimeType"]}
                for img in reference_images
            ],
        ]
    else:
        input_payload = prompt

    payload: dict = {
        "model": GEMINI_CONFIG["image_model"],
        "input": input_payload,
        "response_modalities": ["IMAGE"],
    }
    if image_config:
        payload["generation_config"] = {"image_config": image_config}

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_CONFIG["api_key"],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(GEMINI_CONFIG["endpoint"], json=payload, headers=headers)

    data = response.json()
    if not response.is_success or data.get("error"):
        msg = (data.get("error") or {}).get("message") or f"Gemini image request failed ({response.status_code})"
        raise Exception(msg)

    return data


async def _create_openrouter_interaction(
    prompt: Any,
    reference_images: list,
    image_config: Optional[dict],
) -> dict:
    """POST to the OpenRouter chat completions endpoint for image generation.

    Args:
        prompt: Text prompt string.
        reference_images: List of dicts with ``data`` and ``mimeType`` keys.
        image_config: Optional image_config dict.

    Returns:
        Raw OpenRouter response dict.
    """
    if reference_images:
        content: Any = [
            {"type": "text", "text": prompt},
            *[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img['mimeType']};base64,{img['data']}"},
                }
                for img in reference_images
            ],
        ]
    else:
        content = prompt

    body: dict = {
        "model": GEMINI_CONFIG["image_model"],
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }
    if image_config:
        body["image_config"] = image_config

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        **EXTRA_API_HEADERS,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            GEMINI_CONFIG["openrouter_endpoint"], json=body, headers=headers
        )

    data = response.json()
    if not response.is_success or data.get("error"):
        msg = (data.get("error") or {}).get("message") or f"OpenRouter image request failed ({response.status_code})"
        raise Exception(msg)

    return data


async def _request_image(
    *,
    prompt: str,
    reference_images: list,
    options: dict,
    log_action: str,
    success_label: str,
    stats_type: str,
    failure_label: str,
) -> dict:
    """Common dispatcher for all image generation/editing calls.

    Routes to OpenRouter or native Gemini based on ``GEMINI_CONFIG["image_backend"]``.
    """
    preview = prompt[:100] if not reference_images else f"{len(reference_images)} images"
    log.gemini(log_action, preview)

    image_config = _build_image_config(options)
    backend = GEMINI_CONFIG["image_backend"]

    if backend == "openrouter":
        raw = await _create_openrouter_interaction(prompt, reference_images, image_config)
        image = _extract_openrouter_image(raw, failure_label)
    else:
        raw = await _create_native_interaction(prompt, reference_images, image_config)
        image = _extract_native_image(raw, failure_label)

    record_gemini(stats_type)
    log.gemini_result(True, f"{success_label} ({image['mimeType']})")
    return image


async def generate_image(prompt: str, options: Optional[dict] = None) -> dict:
    """Generate a new image from a text prompt.

    Args:
        prompt: Image description.
        options: Optional dict with ``aspectRatio`` and/or ``imageSize``.

    Returns:
        Dict with ``data`` (base64 str) and ``mimeType`` keys.
    """
    return await _request_image(
        prompt=prompt,
        reference_images=[],
        options=options or {},
        log_action="Generating image",
        success_label="Generated image",
        stats_type="generate",
        failure_label="Image generation",
    )


async def edit_image(
    instructions: str,
    image_base64: str,
    mime_type: str,
    options: Optional[dict] = None,
) -> dict:
    """Edit a single reference image according to instructions.

    Args:
        instructions: Editing instructions.
        image_base64: Base64-encoded source image.
        mime_type: MIME type of the source image.
        options: Optional dict with ``aspectRatio`` and/or ``imageSize``.

    Returns:
        Dict with ``data`` (base64 str) and ``mimeType`` keys.
    """
    return await _request_image(
        prompt=instructions,
        reference_images=[{"data": image_base64, "mimeType": mime_type}],
        options=options or {},
        log_action="Editing image",
        success_label="Edited image",
        stats_type="edit",
        failure_label="Image editing",
    )


async def edit_image_with_references(
    instructions: str,
    reference_images: list,
    options: Optional[dict] = None,
) -> dict:
    """Edit multiple reference images according to instructions.

    Args:
        instructions: Editing instructions.
        reference_images: List of dicts with ``data`` and ``mimeType`` keys.
        options: Optional dict with ``aspectRatio`` and/or ``imageSize``.

    Returns:
        Dict with ``data`` (base64 str) and ``mimeType`` keys.
    """
    return await _request_image(
        prompt=instructions,
        reference_images=reference_images,
        options=options or {},
        log_action="Editing with references",
        success_label="Generated image with references",
        stats_type="edit",
        failure_label="Image editing",
    )
