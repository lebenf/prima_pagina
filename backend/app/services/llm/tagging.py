# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Background tagging queue: processes new articles via LLM without blocking the feed fetcher.
Uses asyncio.Queue — N concurrent workers based on LLMConfig.max_concurrent.
"""
import asyncio
import logging
from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.article import Article, TagsSource
from app.models.category import Category
from app.models.llm_function_assignment import LLMFunction
from app.services.llm.router import llm_router

logger = logging.getLogger(__name__)

tagging_queue: asyncio.Queue[UUID] = asyncio.Queue(maxsize=2000)


async def enqueue_article_for_tagging(article_id: UUID) -> None:
    try:
        tagging_queue.put_nowait(article_id)
    except asyncio.QueueFull:
        logger.warning("tagging: queue full, skipping article %s", article_id)


async def tagging_worker(worker_id: int = 0) -> None:
    logger.info("tagging: worker %d started", worker_id)
    while True:
        try:
            article_id = await tagging_queue.get()
            await _tag_article(article_id)
            tagging_queue.task_done()
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("tagging: worker %d stopped", worker_id)
            break
        except Exception as exc:
            logger.error("tagging: worker %d error: %s", worker_id, exc, exc_info=True)


async def start_tagging_workers(n: int = 1) -> list[asyncio.Task]:
    """Spawn n tagging worker tasks. Called from main.py lifespan."""
    n = max(1, n)
    logger.info("tagging: starting %d worker(s)", n)
    return [asyncio.create_task(tagging_worker(worker_id=i)) for i in range(n)]


async def get_tagging_concurrency() -> int:
    """Read max_concurrent from the LLM config assigned to the tagging function."""
    from app.models.llm_function_assignment import LLMFunctionAssignment

    async with AsyncSessionLocal() as db:
        assignment = await db.get(LLMFunctionAssignment, LLMFunction.TAGGING.value)
        config = await llm_router._resolve_config(assignment, db) if assignment else None
        return config.max_concurrent if config else 1


async def _fetch_top_existing_tags(db, limit: int = 80) -> list[str]:
    """Return the most-used tags across all articles to guide LLM reuse."""
    result = await db.execute(select(Article.tags).where(Article.tags.isnot(None)))
    counter: Counter = Counter()
    for (tags,) in result:
        if tags:
            counter.update(tags)
    return [tag for tag, _ in counter.most_common(limit)]


async def _tag_article(article_id: UUID) -> None:
    from app.config import get_settings

    async with AsyncSessionLocal() as db:
        article = await db.get(
            Article, article_id, options=[selectinload(Article.feed)]
        )
        if not article:
            return
        if article.tags_source != TagsSource.NONE.value:
            return  # already tagged

        categories_result = await db.execute(select(Category.slug))
        category_slugs = [row[0] for row in categories_result]

        existing_tags = await _fetch_top_existing_tags(db)

        settings = get_settings()
        provider = await llm_router.get_provider_for(
            LLMFunction.TAGGING, db, encryption_key=settings.encryption_key
        )
        if not provider:
            logger.debug("tagging: no provider configured, skipping article %s", article_id)
            return

        tagging_language = getattr(provider.config, "tagging_language", "it") or "it"

        result = await provider.tag_article(
            title=article.title or "",
            excerpt=article.content_excerpt or "",
            language=article.language,
            available_categories=category_slugs,
            tagging_language=tagging_language,
            existing_tags=existing_tags,
        )

        article.tags = result.tags
        article.tags_source = TagsSource.LLM.value
        if result.language and not article.language:
            article.language = result.language

        if result.category_slug and result.confidence > 0.7:
            if article.feed and not article.feed.category_id:
                cat_result = await db.execute(
                    select(Category).where(Category.slug == result.category_slug)
                )
                category = cat_result.scalar_one_or_none()
                if category:
                    article.feed.category_id = category.id

        from app.services.event_clustering import attach_or_create_event

        # Event matching is a harder editorial judgment than tagging — prefer
        # the model assigned to EVENT_SUMMARY (also event-related editorial
        # work), falling back to the tagging provider if unconfigured so
        # clustering doesn't silently stop working on upgrade.
        event_matching_provider = await llm_router.get_provider_for(
            LLMFunction.EVENT_SUMMARY, db, encryption_key=settings.encryption_key
        ) or provider
        event, should_regenerate_summary = await attach_or_create_event(
            db, article, event_matching_provider
        )

        await db.commit()
        logger.debug(
            "tagging: article %s tagged: %s (lang=%s)", article_id, result.tags, tagging_language
        )

    if should_regenerate_summary:
        from app.services.event_summary_service import regenerate_event_summary
        asyncio.create_task(regenerate_event_summary(event.id))

    from app.services.related_articles import compute_related_articles
    asyncio.create_task(compute_related_articles(article_id))
