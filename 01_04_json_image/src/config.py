# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module configuration for JSON image agent — API settings, dual image backend
(Gemini native vs OpenRouter), model selection, system prompt, and folder constants.

The agent uses JSON templates for token-efficient image generation: copy template →
edit subject only → pass full JSON to create_image.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/config.js

"""

import os
import sys
from pathlib import Path

# Repo root is 2 levels above this file: src/ → module root → repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from config import (  # type: ignore[import]
        resolve_model_for_provider,
        AI_API_KEY,
        EXTRA_API_HEADERS,
        RESPONSES_API_ENDPOINT,
        OPENROUTER_API_KEY,
    )
except ImportError:
    AI_API_KEY: str = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY") or ""
    EXTRA_API_HEADERS: dict = {}
    RESPONSES_API_ENDPOINT: str = "https://api.openai.com/v1/responses"

    def resolve_model_for_provider(model: str) -> str:  # type: ignore[misc]
        """Fallback: return model name unchanged."""
        return model


GEMINI_API_KEY: str = (os.getenv("GEMINI_API_KEY") or "").strip()

_has_gemini = bool(GEMINI_API_KEY)
_has_openrouter = bool(OPENROUTER_API_KEY)

if not _has_gemini and not _has_openrouter:
    print("\033[31mError: image generation backend is not configured\033[0m", file=sys.stderr)
    print("       Add one of these to the repo root .env file:", file=sys.stderr)
    print("       OPENROUTER_API_KEY=sk-or-v1-...   # uses google/gemini-3.1-flash-image-preview", file=sys.stderr)
    print("       GEMINI_API_KEY=...                # uses native Gemini image generation", file=sys.stderr)
    sys.exit(1)

# Prefer OpenRouter if available; fall back to native Gemini
IMAGE_BACKEND: str = "openrouter" if _has_openrouter else "gemini"

API_CONFIG: dict = {
    "model": resolve_model_for_provider("gpt-5.2"),
    "vision_model": resolve_model_for_provider("gpt-5.2"),
    "max_output_tokens": 16384,
    "instructions": """You are an image generation agent using JSON-based prompting with minimal token usage.

## WORKFLOW (Token-Efficient)

1. **COPY template**: Copy workspace/template.json → workspace/prompts/{subject_name}_{timestamp}.json
2. **EDIT subject only**: Use MCP file tools to edit ONLY the "subject" section in the copied file
3. **READ prompt file**: Read the complete JSON from the prompt file
4. **GENERATE**: Pass the JSON content to create_image with format settings from the template
5. **REPORT**: Return the generated image path and prompt file path

## PROCESS STEPS

1. Copy template.json to workspace/prompts/ with descriptive filename
   Example: workspace/prompts/phoenix_1769959315686.json

2. Edit the copied file - ONLY modify the "subject" object:
   {
     "subject": {
       "main": "phoenix",
       "details": "rising from flames, wings fully spread, feathers transforming to fire",
       "orientation": "three-quarter view, facing slightly left",
       "position": "centered horizontally and vertically",
       "scale": "occupies 60% of frame height"
     }
   }
   Keep orientation, position, scale from template unless user specifies otherwise.

3. Read the complete JSON from the prompt file

4. Pass JSON content to create_image. Extract technical settings from the JSON:
   - aspect_ratio: use technical.aspect_ratio from JSON (e.g., "1:1", "16:9")
   - image_size: use technical.resolution from JSON (e.g., "1k", "2k", "4k")

## RULES
- **COPY FIRST**: Always create a new prompt file, never edit template.json directly
- **MINIMAL EDITS**: Only edit the "subject" section, preserve everything else
- **VERSION FILES**: Each generation gets its own prompt file for history
- **READ BEFORE GENERATE**: Always read the complete JSON before passing to create_image
- **USE TEMPLATE SETTINGS**: Always use aspect_ratio and resolution from the template's technical section

## FILE NAMING
- Format: {subject_slug}_{timestamp}.json
- Example: dragon_breathing_fire_1769959315686.json
- Keep names short but descriptive""",
}

GEMINI_CONFIG: dict = {
    "api_key": GEMINI_API_KEY,
    "image_backend": IMAGE_BACKEND,
    # OpenRouter uses the flash model; native Gemini uses the pro image model
    "image_model": (
        "google/gemini-3.1-flash-image-preview"
        if IMAGE_BACKEND == "openrouter"
        else "gemini-3-pro-image-preview"
    ),
    "endpoint": "https://generativelanguage.googleapis.com/v1beta/interactions",
    "openrouter_endpoint": "https://openrouter.ai/api/v1/chat/completions",
}

OUTPUT_FOLDER: str = "workspace/output"
