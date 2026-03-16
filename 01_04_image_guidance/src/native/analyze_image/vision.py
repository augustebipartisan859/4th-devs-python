# -*- coding: utf-8 -*-

#   vision.py

"""
### Description:
Vision API call for image quality analysis — sends an image + question to the
Responses API vision endpoint and returns the model's text answer.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/analyze-image/vision.js

"""

import httpx

from ...config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT, API_CONFIG
from ...helpers.response import extract_response_text
from ...helpers.stats import record_usage


async def vision(*, image_base64: str, mime_type: str, question: str) -> str:
    """Send an image to the Responses API for vision analysis.

    Args:
        image_base64: Base64-encoded image data.
        mime_type: MIME type of the image.
        question: Analysis prompt / question to ask about the image.

    Returns:
        Model's text response.

    Raises:
        Exception: If the API returns an error.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
        **EXTRA_API_HEADERS,
    }

    body = {
        "model": API_CONFIG["vision_model"],
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": question},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_base64}",
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(RESPONSES_API_ENDPOINT, json=body, headers=headers)

    data = response.json()

    if not response.is_success or data.get("error"):
        msg = (data.get("error") or {}).get("message") or f"Vision request failed ({response.status_code})"
        raise Exception(msg)

    record_usage(data.get("usage"))
    return extract_response_text(data) or "No response"
