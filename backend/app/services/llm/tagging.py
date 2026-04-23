# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Background tagging queue: processes new articles via LLM without blocking the feed fetcher.
Uses asyncio.Queue — single coroutine worker, no DB concurrency issues.
"""
import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.article import Article, TagsSource
from app.models.category import Category
from app.services.llm.router import llm_router

logger = logging.getLogger(__name__)

tagging_queue: asyncio.Queue[UUID] = asyncio.Queue(maxsize=1000)


async def enqueue_article_for_tagging(article_id: UUID) -> None:
    try:
        tagging_queue.put_nowait(article_id)
    except asyncio.QueueFull:
        logger.warning("tagging: queue full, skipping article %s", article_id)


async def tagging_worker() -> None:
    logger.info("tagging: worker started")
    while True:
        try:
            article_id = await tagging_queue.get()
            await _tag_article(article_id)
            tagging_queue.task_done()
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("tagging: worker stopped")
            break
        except Exception as exc:
            logger.error("tagging: worker error: %s", exc, exc_info=True)


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

        settings = get_settings()
        provider = await llm_router.get_provider_for(
            "tagging", db, encryption_key=settings.encryption_key
        )
        if not provider:
            logger.debug("tagging: no provider configured, skipping article %s", article_id)
            return

        result = await provider.tag_article(
            title=article.title or "",
            excerpt=article.content_excerpt or "",
            language=article.language,
            available_categories=category_slugs,
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

        await db.commit()
        logger.debug(
            "tagging: article %s tagged: %s", article_id, result.tags
        )
