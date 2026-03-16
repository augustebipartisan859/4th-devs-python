# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module configuration for image recognition agent — API settings, model selection,
system prompt, and folder constants.

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
    )
except ImportError:
    AI_API_KEY: str = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
    EXTRA_API_HEADERS: dict = {}
    RESPONSES_API_ENDPOINT: str = "https://api.openai.com/v1/responses"

    def resolve_model_for_provider(model: str) -> str:  # type: ignore[misc]
        """Fallback: return model name unchanged."""
        return model


API_CONFIG: dict = {
    "model": resolve_model_for_provider("gpt-5.2"),
    "vision_model": resolve_model_for_provider("gpt-5.2"),
    "max_output_tokens": 16384,
    "instructions": """You are an autonomous classification agent.

## GOAL
Classify items from images/ into categories based on profiles in knowledge/.
Output to images/organized/<category>/ folders.

## PROCESS
Read profiles first using fs_read with mode:"list" on the knowledge/ folder to get file names, then read each file individually. Process items incrementally - complete each before moving to next. You can read the same image multiple times if you need to.

## REASONING

1. EVIDENCE
   Only use what you can clearly observe.
   "Not visible" means unknown, not absent.
   Criteria require visible features: if the feature is hidden, the criterion is unevaluable → no match.

2. MATCHING
   Profiles are minimum requirements, not exhaustive descriptions.
   Match when ALL stated criteria are satisfied—nothing more.
   Extra observed traits not in the profile are irrelevant; ignore them entirely.
   Profiles define sufficiency: a 1-criterion profile needs only that 1 criterion to match.
   If direct match fails, use elimination: rule out profiles until one remains.

3. AMBIGUITY
   Multiple matches → copy to all matching folders.
   No match possible → unclassified.
   Observation unclear (can't see features) → unclassified.
   Clear observation + criteria satisfied → classify; don't add hesitation.

4. COMPOSITES
   Items containing multiple subjects: evaluate each separately.
   Never combine traits from different subjects.

5. RECOVERY
   Mistakes can be corrected by moving files.

Run autonomously. Report summary when complete.""",
}

IMAGES_FOLDER: str = "images"
KNOWLEDGE_FOLDER: str = "knowledge"
