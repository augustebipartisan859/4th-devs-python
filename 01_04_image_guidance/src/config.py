# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module-level configuration for the image guidance agent.
Detects available image backend (OpenRouter preferred, falls back to Gemini),
re-exports shared credentials from the repo root config, and defines agent
instructions for pose-guided cell-shaded character generation.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/config.js

"""

import os
import sys
from pathlib import Path

# Add repo root to sys.path so we can import the shared root config
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from config import (  # noqa: E402
        resolve_model_for_provider,
        AI_API_KEY,
        EXTRA_API_HEADERS,
        RESPONSES_API_ENDPOINT,
        OPENROUTER_API_KEY,
    )
except ImportError:
    # Fallback if root config is not available
    AI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or ""
    EXTRA_API_HEADERS: dict = {}
    RESPONSES_API_ENDPOINT = "https://api.openai.com/v1/responses"

    def resolve_model_for_provider(model: str) -> str:  # type: ignore[misc]
        return model


GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()

_has_gemini = bool(GEMINI_API_KEY)
_has_openrouter = bool(OPENROUTER_API_KEY)

if not _has_gemini and not _has_openrouter:
    import sys as _sys

    print("\x1b[31mError: image generation backend is not configured\x1b[0m")
    print("       Add one of these to the repo root .env file:")
    print("       OPENROUTER_API_KEY=sk-or-v1-...   # uses google/gemini-3.1-flash-image-preview")
    print("       GEMINI_API_KEY=...                # uses native Gemini image generation")
    _sys.exit(1)

# OpenRouter is preferred when available (matches JS logic)
IMAGE_BACKEND = "openrouter" if _has_openrouter else "gemini"

# Agent model — same model as used by the JS config
_MODEL = resolve_model_for_provider("gpt-5.2")

# Pose-guided cell-shaded character generation system instructions (matches JS src/config.js)
_INSTRUCTIONS = """You are an image generation agent creating cell-shaded 3D style characters in a walking pose.

## STYLE
- Cell-shaded 3D illustration with rough, sketchy outlines
- Hand-drawn feel with bold dark outlines
- Hard-edged shadows (2-3 shade levels, no smooth gradients)
- Western illustration style (not anime)

## POSE REFERENCE (MANDATORY)
Every image generation REQUIRES a pose reference from workspace/reference/.

**Pose Selection:**
1. **Explicit**: User says "running knight" → use running-pose.png
2. **Inferred**: User says "warrior charging into battle" → infer running, use running-pose.png
3. **Default**: If pose is unclear/neutral, use walking-pose.png

**Before generating:**
1. List files in workspace/reference/ to see available poses
2. Match user's request (explicit or inferred) to available pose files
3. If no matching pose exists → STOP and ask user to add the pose reference first

**Example pose matching:**
- "running", "charging", "sprinting" → running-pose.png
- "walking", "strolling", "wandering" → walking-pose.png
- "sitting", "seated" → sitting-pose.png (if exists, else refuse)
- "fighting", "combat stance" → fighting-pose.png (if exists, else refuse)

## WORKFLOW

1. **COPY template**: Copy workspace/template.json → workspace/prompts/{subject_name}_{timestamp}.json
2. **EDIT subject only**: Modify ONLY the "subject" section (main, details) in the copied file
3. **READ prompt file**: Read the complete JSON from the prompt file
4. **GENERATE**: Call create_image with:
   - prompt: the JSON content
   - reference_images: [pose reference file] (default: "workspace/reference/walking-pose.png")
   - aspect_ratio: from template's technical.aspect_ratio (default "3:4")
   - image_size: from template's technical.resolution (default "2k")
5. **REPORT**: Return the generated image path

## EDITING THE SUBJECT

Only modify subject.main and subject.details:
{
  "subject": {
    "main": "medieval knight",
    "details": "silver armor with blue cape, sword at hip, weathered helmet under arm"
  }
}

Keep pose, orientation, position, scale from template - they're designed for the walking reference.

## RULES
- **POSE REQUIRED**: Every create_image call MUST include a pose reference from workspace/reference/
- **NO POSE = NO IMAGE**: If required pose doesn't exist, refuse and ask user to add it to workspace/reference/
- **INFER POSE**: Analyze user description to determine appropriate pose
- **COPY FIRST**: Never edit template.json directly
- **MINIMAL EDITS**: Only edit subject.main, subject.details, and subject.pose

## FILE NAMING
- Format: {subject_slug}_{timestamp}.json
- Example: medieval_knight_1769959315686.json"""

# Agent API configuration
API_CONFIG: dict = {
    "model": _MODEL,
    "vision_model": _MODEL,
    "max_output_tokens": 16384,
    "instructions": _INSTRUCTIONS,
}

# Gemini / image backend configuration
GEMINI_CONFIG: dict = {
    "api_key": GEMINI_API_KEY,
    "image_backend": IMAGE_BACKEND,
    # OpenRouter uses a versioned flash model; native Gemini uses the pro image model
    "image_model": (
        "google/gemini-3.1-flash-image-preview"
        if IMAGE_BACKEND == "openrouter"
        else "gemini-3-pro-image-preview"
    ),
    "endpoint": "https://generativelanguage.googleapis.com/v1beta/interactions",
    "openrouter_endpoint": "https://openrouter.ai/api/v1/chat/completions",
}

OUTPUT_FOLDER = "workspace/output"
