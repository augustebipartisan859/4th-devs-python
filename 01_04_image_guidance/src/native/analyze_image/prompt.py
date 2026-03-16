# -*- coding: utf-8 -*-

#   prompt.py

"""
### Description:
Analysis prompt builder for the analyze_image tool.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/native/analyze-image/prompt.js

"""

DEFAULT_CHECK_ASPECTS: list = [
    "prompt_adherence",
    "visual_artifacts",
    "anatomy",
    "text_rendering",
    "style_consistency",
    "composition",
]


def build_analysis_prompt(original_prompt: str, aspects: list) -> str:
    """Build the structured analysis prompt for the vision model.

    Args:
        original_prompt: The prompt that produced the image.
        aspects: List of aspect names to evaluate.

    Returns:
        Formatted prompt string.
    """
    aspect_lines = []
    if "prompt_adherence" in aspects:
        aspect_lines.append(
            "1. PROMPT ADHERENCE: Does the image accurately represent what was requested? "
            "What elements match or are missing?"
        )
    if "visual_artifacts" in aspects:
        aspect_lines.append(
            "2. VISUAL ARTIFACTS: Are there any glitches, distortions, blur, noise, "
            "or unnatural patterns?"
        )
    if "anatomy" in aspects:
        aspect_lines.append(
            "3. ANATOMY: If there are people/animals, check for correct proportions, "
            "especially hands, fingers, faces, and limbs."
        )
    if "text_rendering" in aspects:
        aspect_lines.append(
            "4. TEXT RENDERING: If text was requested, is it readable and correctly spelled?"
        )
    if "style_consistency" in aspects:
        aspect_lines.append(
            "5. STYLE CONSISTENCY: Is the visual style coherent throughout the image?"
        )
    if "composition" in aspects:
        aspect_lines.append(
            "6. COMPOSITION: Is the framing and layout balanced and appropriate?"
        )

    return (
        f'Analyze this AI-generated image for quality issues. The original prompt was:\n'
        f'"{original_prompt}"\n\n'
        f"Please evaluate the following aspects:\n\n"
        + "\n".join(aspect_lines)
        + """

Use this exact output format:

VERDICT: ACCEPT or RETRY
SCORE: <1-10>
BLOCKING_ISSUES:
- <only issues that materially break the brief; use "none" if there are none>
MINOR_ISSUES:
- <optional polish notes that do not require another retry; use "none" if there are none>
NEXT_PROMPT_HINT:
- <targeted retry hint only if VERDICT is RETRY; otherwise use "none">

Decision rules:
- Use ACCEPT when the main subject, pose guidance, and style requirements are satisfied, even if minor polish notes remain.
- Use RETRY only when there are blocking issues such as wrong pose, broken composition, unreadable required text, severe artifacts, or clear style violations.
- Do NOT use RETRY for small polish improvements alone."""
    )
