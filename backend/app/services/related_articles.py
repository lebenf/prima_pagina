# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Computes related articles for a given article.
Run as background task after tagging.
Result shared in article_llm_data — computed once per article.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.article import Article
from app.models.article_llm_data import ArticleLLMData
from app.services.llm.router import llm_router

logger = logging.getLogger(__name__)

CORRELATION_WINDOW_HOURS = 72
MAX_CANDIDATES = 20
MAX_RELATED = 5
MIN_TAG_OVERLAP = 1


async def compute_related_articles(article_id: UUID) -> None:
    """Entry point: run as background task after tagging. Skips if already computed."""
    try:
        async with AsyncSessionLocal() as db:
            article = await db.get(
                Article, article_id,
                options=[selectinload(Article.llm_data)]
            )
            if not article:
                return

            if article.llm_data and article.llm_data.related_article_ids:
                return

            related_ids = await _find_related(db, article)

            if article.llm_data:
                article.llm_data.related_article_ids = related_ids
                article.llm_data.computed_at = datetime.utcnow()
            else:
                db.add(ArticleLLMData(
                    article_id=article_id,
                    related_article_ids=related_ids,
                    computed_at=datetime.utcnow(),
                ))

            await db.commit()
            logger.debug(
                "related articles computed for %s: %d found",
                article_id, len(related_ids)
            )
    except Exception as exc:
        logger.error("related articles computation failed for %s: %s", article_id, exc, exc_info=True)


async def _find_related(db: AsyncSession, article: Article) -> list[str]:
    if not article.tags:
        return []

    cutoff = datetime.utcnow() - timedelta(hours=CORRELATION_WINDOW_HOURS)
    candidates = await _find_candidates(db, article, cutoff)

    if not candidates:
        return []

    if len(candidates) <= 3:
        return [str(c.id) for c in candidates]

    from app.config import get_settings
    settings = get_settings()
    provider = await llm_router.get_provider_for(
        "tagging", db, encryption_key=settings.encryption_key
    )
    if not provider:
        return [str(c.id) for c in candidates[:MAX_RELATED]]

    return await _select_related_with_llm(provider, article, candidates)


async def _find_candidates(
    db: AsyncSession,
    article: Article,
    cutoff: datetime,
) -> list[Article]:
    result = await db.execute(
        select(Article)
        .where(
            Article.id != article.id,
            Article.feed_id != article.feed_id,
            Article.published_at >= cutoff,
        )
        .limit(200)
    )
    candidates_all = result.scalars().all()

    article_tags = set(article.tags)

    scored = []
    for c in candidates_all:
        if not c.tags:
            continue
        overlap = len(article_tags & set(c.tags))
        if overlap >= MIN_TAG_OVERLAP:
            scored.append((c, overlap))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:MAX_CANDIDATES]]


async def _select_related_with_llm(
    provider,
    article: Article,
    candidates: list[Article],
) -> list[str]:
    candidates_text = "\n".join(
        f"[{i + 1}] {c.title or '(senza titolo)'} — tag: {', '.join(c.tags or [])}"
        for i, c in enumerate(candidates)
    )

    prompt = (
        f"Hai letto questo articolo:\n"
        f"Titolo: {article.title or '(senza titolo)'}\n"
        f"Tag: {', '.join(article.tags or [])}\n\n"
        f"Tra i seguenti articoli, scegli i {MAX_RELATED} più correlati per argomento:\n"
        f"{candidates_text}\n\n"
        f"Rispondi SOLO con un array JSON dei numeri degli articoli scelti (es: [1, 3, 5]).\n"
        f"Scegli quelli che trattano lo stesso argomento o evento specifico, "
        f"non solo lo stesso tema generico."
    )

    try:
        if hasattr(provider, '_client'):
            # Claude provider
            message = await provider._client.messages.create(
                model=provider.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
                system="Rispondi solo con JSON. Nessun testo aggiuntivo.",
            )
            raw = message.content[0].text
        else:
            # Ollama provider
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{provider.base_url}/api/generate",
                    json={
                        "model": provider.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.1, "num_predict": 50},
                    },
                )
            raw = res.json()["response"]

        indices = json.loads(raw.strip())
        if not isinstance(indices, list):
            raise ValueError("not a list")

        selected = []
        for idx in indices:
            if isinstance(idx, int) and 1 <= idx <= len(candidates):
                selected.append(str(candidates[idx - 1].id))
        return selected[:MAX_RELATED]

    except Exception as exc:
        logger.warning("related articles LLM selection failed: %s", exc)
        return [str(c.id) for c in candidates[:MAX_RELATED]]
