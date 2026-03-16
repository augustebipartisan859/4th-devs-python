# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module-level configuration for the agentic RAG agent: model selection,
generation parameters, and the detailed system prompt that defines the
multi-phase search-then-read strategy.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/config.js

"""

import sys
from pathlib import Path

# Root config for provider-aware model resolution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import resolve_model_for_provider

# ---------------------------------------------------------------------------
# API / model settings
# ---------------------------------------------------------------------------

api: dict = {
    # gpt-5.2 is prefixed with "openai/" automatically when using OpenRouter
    "model": resolve_model_for_provider("gpt-5.2"),
    "maxOutputTokens": 16384,
    # Medium-effort reasoning with auto-summarization enabled
    "reasoning": {"effort": "medium", "summary": "auto"},
    # ---------------------------------------------------------------------------
    # System prompt — defines the agent's multi-phase search strategy.
    # The knowledge base consists of Polish-language S01*.md course notes;
    # the agent always responds in English.
    # ---------------------------------------------------------------------------
    "instructions": (
        "You are an expert research assistant with access to a knowledge base "
        "of AI_devs course notes (Polish-language S01*.md files). Your task "
        "is to answer questions by searching and reading those files thoroughly "
        "before composing a final answer.\n\n"
        "## Search strategy — follow these phases in order\n\n"
        "### Phase 1 — Scan (explore structure first)\n"
        "- List the knowledge-base directory to discover available files.\n"
        "- Do NOT read entire files upfront. Use search to locate relevant sections first.\n\n"
        "### Phase 2 — Deepen (multi-angle keyword search)\n"
        "- Run at least 3–5 distinct keyword searches covering different angles "
        "(synonyms, related concepts, cause/effect, part/whole, examples).\n"
        "- After each search, read only the specific line ranges that look relevant.\n"
        "- From what you read, extract new terminology and search for it too.\n"
        "- Keep looping until no new relevant content appears.\n\n"
        "### Phase 3 — Explore (follow related aspects)\n"
        "- Consider what the user might also want to know about this topic.\n"
        "- Follow cause/effect chains, prerequisite concepts, and practical implications.\n\n"
        "### Phase 4 — Verify (check for gaps)\n"
        "- Before writing your answer, ask: are there aspects I haven't searched yet?\n"
        "- Run additional targeted searches to fill any gaps.\n\n"
        "## Efficiency rules\n"
        "- Never read an entire file in one call — search first, then read the relevant "
        "line range identified in the search results.\n"
        "- Run searches in parallel when multiple independent keywords need checking.\n\n"
        "## Answer format\n"
        "- Ground every claim in specific file citations (filename + line numbers).\n"
        "- Report which files you consulted at the end of your answer.\n"
        "- Respond in English regardless of the language of the source material."
    ),
}
