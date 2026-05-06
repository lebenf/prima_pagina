# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# In-memory set of article IDs currently being fetched — prevents duplicate tasks
_active_fetches: set[UUID] = set()

_ALLOWED_TAGS = [
    "p", "br", "strong", "em", "b", "i", "u", "s",
    "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "pre", "code",
    "a", "table", "thead", "tbody", "tr", "th", "td",
    "figure", "figcaption", "div", "section", "article",
]
_ALLOWED_TAGS_WITH_IMAGES = _ALLOWED_TAGS + ["img"]

_ALLOWED_ATTRS: dict = {
    "a": ["href", "title", "rel"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}
_ALLOWED_ATTRS_WITH_IMAGES: dict = {
    **_ALLOWED_ATTRS,
    "img": ["src", "alt", "width", "height", "loading"],
}

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_BROWSER_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}


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
    Core fulltext extraction logic. Dispatches based on feed.fulltext_mode.
    Accepts an existing session so it can be called directly in tests.
    """
    from app.models.article import Article, FulltextStatus
    from app.models.feed import Feed
    from sqlalchemy import select

    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(
            selectinload(Article.feed).selectinload(Feed.extraction_script)
        )
    )
    article = result.scalar_one_or_none()

    if article is None:
        return
    if article.fulltext_status == FulltextStatus.OK.value:
        return
    if article.url is None:
        article.fulltext_status = FulltextStatus.FAILED.value
        await db.commit()
        return

    feed = article.feed

    # Skip enrichment when disabled for this feed
    if not feed or not feed.fulltext_enabled:
        article.fulltext_status = FulltextStatus.BLOCKED.value
        await db.commit()
        return

    mode = feed.fulltext_mode
    include_images = feed.fulltext_include_images

    if mode == "trafilatura":
        await _fetch_with_trafilatura(db, article, include_images)

    elif mode == "script":
        script = feed.extraction_script
        if script and script.is_active:
            await _fetch_with_script(db, article, feed, script)
        else:
            await _fetch_with_trafilatura(db, article, include_images)

    elif mode == "auto":
        script = feed.extraction_script
        if script and script.is_active:
            success = await _fetch_with_script(db, article, feed, script)
            if not success:
                await _fetch_with_trafilatura(db, article, include_images)
        else:
            await _fetch_with_trafilatura(db, article, include_images)
            if article.url:
                asyncio.create_task(
                    _try_generate_script_for_feed(feed.id, article.url)
                )
    else:
        await _fetch_with_trafilatura(db, article, include_images)


async def _fetch_with_trafilatura(db, article, include_images: bool = False) -> None:
    """Standard trafilatura extraction outputting sanitized HTML."""
    from app.models.article import FulltextStatus

    try:
        loop = asyncio.get_event_loop()
        fulltext = await loop.run_in_executor(
            None, _extract_fulltext_sync, article.url, include_images
        )

        if fulltext and len(fulltext) > 200:
            article.content_fulltext = fulltext
            article.fulltext_status = FulltextStatus.OK.value
            article.fulltext_fetched_at = datetime.utcnow()
            article.fulltext_method = "trafilatura"
            logger.info("full_text: trafilatura fetched %d chars for %s", len(fulltext), article.id)
        else:
            article.fulltext_status = FulltextStatus.FAILED.value
            logger.info("full_text: content too short or empty for %s", article.id)

    except Exception as exc:
        logger.warning("full_text: trafilatura failed for %s: %s", article.url, exc)
        article.fulltext_status = FulltextStatus.FAILED.value

    await db.commit()


async def _fetch_with_script(db, article, feed, script) -> bool:
    """
    Download HTML and apply CSS selectors.
    Updates success_rate and consecutive_failures.
    Returns True if extraction succeeded.
    """
    from app.models.article import FulltextStatus
    from app.services.extraction_script import apply_extraction_script, _hash_body

    if not article.url:
        return False

    try:
        loop = asyncio.get_event_loop()
        html = await asyncio.wait_for(
            loop.run_in_executor(None, _download_html, article.url),
            timeout=20.0,
        )
    except Exception:
        return False

    # Layout change detection
    current_hash = _hash_body(html)
    if script.sample_html_hash and current_hash != script.sample_html_hash:
        logger.info("layout change detected for feed %s", feed.id)
        script.consecutive_failures += 2

    result = apply_extraction_script(
        script, html,
        fallback_title=article.title,
        fallback_author=article.author,
    )
    content = result.get("content", "")

    if content and len(content) > 100:
        article.content_fulltext = content
        article.fulltext_status = FulltextStatus.OK.value
        article.fulltext_fetched_at = datetime.utcnow()
        article.fulltext_method = "script"
        script.success_rate = script.success_rate * 0.95 + 0.05
        script.consecutive_failures = 0
        await db.commit()
        return True
    else:
        script.success_rate = script.success_rate * 0.95
        script.consecutive_failures += 1
        if script.consecutive_failures >= 5:
            logger.warning("deactivating extraction script for feed %s", feed.id)
            script.is_active = False
            if article.url:
                asyncio.create_task(
                    _try_generate_script_for_feed(feed.id, article.url)
                )
        await db.commit()
        return False


async def _try_generate_script_for_feed(feed_id: UUID, sample_url: str) -> None:
    """Background task: download page and generate extraction script."""
    from app.database import AsyncSessionLocal
    from app.models.feed import Feed
    from app.services.extraction_script import generate_extraction_script

    async with AsyncSessionLocal() as db:
        feed = await db.get(Feed, feed_id)
        if not feed:
            return
        try:
            loop = asyncio.get_event_loop()
            html = await asyncio.wait_for(
                loop.run_in_executor(None, _download_html, sample_url),
                timeout=20.0,
            )
            await generate_extraction_script(feed, sample_url, html, db)
        except Exception as exc:
            logger.error("script generation failed for feed %s: %s", feed_id, exc)


def _download_html(url: str) -> str:
    """Synchronous HTML download; run in thread pool executor."""
    import httpx

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        r = client.get(url, headers=_BROWSER_HEADERS)
        r.raise_for_status()
        return r.text


def _sanitize_html(html: str, include_images: bool) -> str:
    """Strip disallowed tags/attributes; preserve safe formatting."""
    import bleach

    tags = _ALLOWED_TAGS_WITH_IMAGES if include_images else _ALLOWED_TAGS
    attrs = _ALLOWED_ATTRS_WITH_IMAGES if include_images else _ALLOWED_ATTRS
    return bleach.clean(html, tags=tags, attributes=attrs, strip=True)


def _extract_fulltext_sync(url: str, include_images: bool = False) -> str | None:
    """Synchronous trafilatura extraction; run in a thread pool executor."""
    import httpx
    import trafilatura

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            r = client.get(url, headers=_BROWSER_HEADERS)
            r.raise_for_status()
            html = r.text
    except Exception:
        # Fall back to trafilatura's own fetcher
        html = trafilatura.fetch_url(url)

    if not html:
        return None

    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_formatting=True,
        no_fallback=False,
        favor_recall=True,
        output_format="html",
        include_images=include_images,
    )

    if not extracted:
        return None

    return _sanitize_html(extracted, include_images)
