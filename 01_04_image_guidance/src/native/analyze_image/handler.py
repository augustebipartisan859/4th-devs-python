# -*- coding: utf-8 -*-

#   handler.py

"""
### Description:
Handler for the analyze_image native tool — reads the image, calls vision API
with a structured analysis prompt, and returns a parsed quality report.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/analyze-image/handler.js

"""

from typing import Optional

from .vision import vision
from .report import parse_analysis_report
from .prompt import build_analysis_prompt, DEFAULT_CHECK_ASPECTS
from ..shared.image_files import read_project_image
from ...helpers.logger import log


async def analyze_image(
    *,
    image_path: str,
    original_prompt: str,
    check_aspects: Optional[list] = None,
) -> dict:
    """Analyse an image for quality issues and return a structured report.

    Args:
        image_path: Workspace-relative path to the image.
        original_prompt: The prompt that produced the image.
        check_aspects: List of aspect names to evaluate (defaults to all six).

    Returns:
        Dict with ``verdict``, ``score``, ``blocking_issues``, ``minor_issues``,
        ``next_prompt_hints``, and the raw ``analysis`` text.
    """
    try:
        image_data = read_project_image(image_path)
        aspects = check_aspects or DEFAULT_CHECK_ASPECTS

        log.vision(image_path, "Quality analysis")

        analysis = await vision(
            image_base64=image_data["imageBase64"],
            mime_type=image_data["mimeType"],
            question=build_analysis_prompt(original_prompt, aspects),
        )

        log.vision_result(analysis[:150] + "...")

        report = parse_analysis_report(analysis)

        return {
            "success": True,
            "image_path": image_path,
            "original_prompt": original_prompt,
            "aspects_checked": aspects,
            "verdict": report["verdict"],
            "score": report["score"],
            "blocking_issues": report["blockingIssues"],
            "minor_issues": report["minorIssues"],
            "next_prompt_hints": report["nextPromptHints"],
            "analysis": analysis,
        }

    except Exception as error:
        log.error("analyze_image", str(error))
        return {"success": False, "error": str(error)}
