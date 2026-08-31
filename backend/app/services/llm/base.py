# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.llm_config import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class TaggingResult:
    tags: list[str] = field(default_factory=list)
    category_slug: str | None = None
    language: str | None = None
    confidence: float = 0.0


@dataclass
class DigestResult:
    title: str = ""
    content_html: str = ""
    content_text: str = ""
    article_count: int = 0


class LLMProvider(ABC):
    def __init__(self, config: "LLMConfig"):
        self.config = config
        self.model = config.model_name

    @abstractmethod
    async def tag_article(
        self,
        title: str,
        excerpt: str,
        language: str | None,
        available_categories: list[str],
        tagging_language: str = "it",
        existing_tags: list[str] | None = None,
    ) -> TaggingResult: ...

    @abstractmethod
    async def generate_digest(
        self,
        articles: list[dict],
        period_label: str,
        output_language: str,
        style_hints: str = "",
    ) -> DigestResult: ...

    @abstractmethod
    async def generate_text(self, prompt: str, max_tokens: int = 500, json_mode: bool = False) -> str:
        """Generic text generation for custom prompts (e.g. CSS selector extraction).

        `json_mode` asks the provider to constrain output to a JSON object where
        it natively supports it (Ollama `format: "json"`, OpenAI-compatible
        `response_format`, Claude assistant-turn prefill) — always parse the
        result with `_parse_json_object`, which tolerates providers where this
        is a best-effort hint rather than a hard guarantee.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @staticmethod
    def _build_tagging_prompt(
        title: str,
        excerpt: str,
        language: str | None,
        available_categories: list[str],
        tagging_language: str = "it",
        existing_tags: list[str] | None = None,
    ) -> str:
        lang_names = {
            "it": "Italian", "en": "English", "fr": "French",
            "de": "German", "es": "Spanish", "pt": "Portuguese",
        }
        lang_name = lang_names.get(tagging_language, tagging_language)
        cats = ", ".join(available_categories) if available_categories else "none"
        existing_hint = ""
        if existing_tags:
            existing_hint = (
                f"\nExisting tags already in use (reuse these FIRST if applicable): "
                f"{', '.join(existing_tags[:60])}"
            )
        return f"""Analyze this article and respond ONLY with a valid JSON object.

Title: {title}
Article language: {language or 'unknown'}
Excerpt: {excerpt[:500]}

Available categories: {cats}
{existing_hint}

Reply with this EXACT JSON format:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "category_slug": "one-of-the-available-categories-or-null",
  "language": "BCP47-language-code",
  "confidence": 0.9
}}

Rules:
- tags: 2-5 lowercase tags WRITTEN IN {lang_name.upper()} (mandatory, regardless of article language)
- tags: reuse existing tags listed above when they fit; create new ones only if no existing tag is suitable
- category_slug: pick the BEST matching category from the list above, or null only if none fit at all
- language: ISO 639-1 code of the article (it, en, fr, de, es, pt)
- confidence: classification confidence 0.0-1.0
"""

    @staticmethod
    def _clean_html_response(raw: str) -> str:
        """Strip markdown code fences and chat-style preamble/trailing prose that
        some models add before/after the requested HTML despite instructions not to."""
        text = raw.strip()
        fence = re.search(r"```(?:html)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()
        tag_start = text.find("<")
        if tag_start > 0:
            text = text[tag_start:]
        return text

    @staticmethod
    def _parse_tagging_json(raw: str) -> TaggingResult:
        try:
            data = json.loads(raw)
            tags = [t.lower().strip() for t in data.get("tags", []) if isinstance(t, str)][:5]
            return TaggingResult(
                tags=tags,
                category_slug=data.get("category_slug") or None,
                language=data.get("language") or None,
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.warning("llm: failed to parse tagging JSON: %s", raw[:200])
            return TaggingResult()

    @staticmethod
    def _parse_json_object(raw: str) -> dict | None:
        """Parse a JSON object out of raw LLM output, tolerating markdown code
        fences and leading/trailing prose some models add despite being told
        not to. Returns None (never raises) when no object can be recovered —
        callers decide the fallback."""
        text = (raw or "").strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(text[start : i + 1])
                        return data if isinstance(data, dict) else None
                    except json.JSONDecodeError:
                        return None
        return None
