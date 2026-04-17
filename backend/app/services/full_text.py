import asyncio
import logging
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)

# In-memory set of article IDs currently being fetched — prevents duplicate tasks
_active_fetches: set[UUID] = set()


def is_fetch_active(article_id: UUID) -> bool:
    return article_id in _active_fetches


async def fetch_fulltext(article_id: UUID) -> None:
    """
    Background task entry point: creates its own DB session.
    Guards against duplicate concurrent fetches via _active_fetches.
    """
    if article_id in _active_fetches:
        return
    _active_fetches.add(article_id)
    try:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await process_fulltext(article_id, db)
    finally:
        _active_fetches.discard(article_id)


async def process_fulltext(article_id: UUID, db) -> None:
    """
    Core fulltext extraction logic.  Accepts an existing session so it can
    be called directly in tests without needing to mock AsyncSessionLocal.
    """
    from app.models.article import Article, FulltextStatus

    article = await db.get(Article, article_id)
    if article is None:
        return
    if article.fulltext_status == FulltextStatus.OK.value:
        return
    if article.url is None:
        article.fulltext_status = FulltextStatus.FAILED.value
        await db.commit()
        return

    try:
        loop = asyncio.get_event_loop()
        fulltext = await loop.run_in_executor(None, _extract_fulltext_sync, article.url)

        if fulltext and len(fulltext) > 200:
            article.content_fulltext = fulltext
            article.fulltext_status = FulltextStatus.OK.value
            article.fulltext_fetched_at = datetime.utcnow()
            logger.info("full_text: fetched %d chars for article %s", len(fulltext), article_id)
        else:
            article.fulltext_status = FulltextStatus.FAILED.value
            logger.info("full_text: content too short or empty for article %s", article_id)

    except Exception as exc:
        logger.warning("full_text: fetch failed for %s: %s", article.url, exc)
        article.fulltext_status = FulltextStatus.FAILED.value

    await db.commit()


def _extract_fulltext_sync(url: str) -> str | None:
    """Synchronous extraction; run in a thread pool executor."""
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    return trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        favor_recall=True,
    )
