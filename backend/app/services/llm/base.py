# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
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
    async def health_check(self) -> bool: ...

    @staticmethod
    def _build_tagging_prompt(
        title: str,
        excerpt: str,
        language: str | None,
        available_categories: list[str],
    ) -> str:
        cats = ", ".join(available_categories) if available_categories else "none"
        return f"""Analyze this article and respond ONLY with a valid JSON object.

Title: {title}
Detected language: {language or 'unknown'}
Excerpt: {excerpt[:500]}

Available categories: {cats}

Reply with this EXACT JSON format:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "category_slug": "one-of-the-available-categories-or-null",
  "language": "BCP47-language-code",
  "confidence": 0.9
}}

Rules:
- tags: 2-5 lowercase tags, preferably in Italian
- category_slug: MUST be one of the available categories above, or null
- language: ISO 639-1 code (it, en, fr, de, es, pt)
- confidence: classification confidence 0.0-1.0
"""

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
