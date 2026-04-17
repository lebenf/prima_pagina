import asyncio
import calendar
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bleach
import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, FulltextStatus, TagsSource
from app.models.feed import Feed

logger = logging.getLogger(__name__)

_USER_AGENT = "PrimaPagina/0.1 (+https://github.com/prima-pagina/prima-pagina)"

_ALLOWED_TAGS = ["p", "a", "br", "strong", "em", "ul", "ol", "li"]
_EXCERPT_MAX_LEN = 2000

# Max backoff: 24 hours
_MAX_BACKOFF_MIN = 1440
# Disable feed after this many consecutive errors
_MAX_ERRORS = 10


def _sanitize_html(html: str) -> str:
    cleaned = bleach.clean(html, tags=_ALLOWED_TAGS, strip=True)
    return cleaned[:_EXCERPT_MAX_LEN]


def _struct_to_utc(struct_time) -> datetime | None:
    """Convert feedparser's time.struct_time (UTC) to datetime."""
    if struct_time is None:
        return None
    try:
        ts = calendar.timegm(struct_time)
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def _detect_language(text: str) -> str | None:
    if not text or len(text.strip()) < 50:
        return None
    try:
        from langdetect import detect, LangDetectException
        return detect(text)
    except Exception:
        return None


def _compute_guid(entry) -> str:
    """Extract or synthesise a stable GUID for a feed entry."""
    guid = getattr(entry, "id", None) or getattr(entry, "guid", None)
    if guid:
        return str(guid)[:2048]
    link = getattr(entry, "link", "") or ""
    title = getattr(entry, "title", "") or ""
    return hashlib.sha256(f"{link}{title}".encode()).hexdigest()[:64]


def _entry_content(entry) -> str | None:
    """Extract and sanitise HTML excerpt from a feedparser entry."""
    raw = None
    content_list = getattr(entry, "content", None)
    if content_list:
        raw = content_list[0].get("value", "")
    if not raw:
        raw = getattr(entry, "summary", None) or getattr(entry, "description", None)
    if not raw:
        return None
    return _sanitize_html(raw)


async def _process_entry(
    entry, feed_language: str | None, feed_id: UUID, db: AsyncSession
) -> Article | None:
    """Upsert a single feed entry. Returns the Article if it was newly created."""
    guid = _compute_guid(entry)

    # Check for existing article
    existing = await db.scalar(
        select(Article).where(Article.feed_id == feed_id, Article.guid == guid)
    )
    if existing is not None:
        # Update mutable fields if the feed edits articles
        changed = False
        title = getattr(entry, "title", None)
        url = getattr(entry, "link", None)
        if title and existing.title != title:
            existing.title = title
            changed = True
        if url and existing.url != url:
            existing.url = url
            changed = True
        if changed:
            await db.commit()
        return None

    # Extract fields
    excerpt = _entry_content(entry)

    author = (
        getattr(entry, "author", None)
        or (getattr(entry, "author_detail", None) or {}).get("name")
    )

    published_at = _struct_to_utc(getattr(entry, "published_parsed", None))
    if published_at is None:
        published_at = datetime.utcnow()

    # Language: prefer feed-level, then detect from excerpt
    language = feed_language or _detect_language(excerpt or "")

    article = Article(
        feed_id=feed_id,
        guid=guid,
        title=getattr(entry, "title", None),
        url=getattr(entry, "link", None),
        author=author,
        content_excerpt=excerpt,
        fulltext_status=FulltextStatus.PENDING.value,
        language=language,
        tags=[],
        tags_source=TagsSource.NONE.value,
        published_at=published_at,
    )
    db.add(article)
    try:
        await db.flush()
        await db.commit()
        logger.debug("feed_fetcher: new article: %s", article.title)
        return article
    except IntegrityError:
        await db.rollback()
        return None


async def fetch_feed(feed_id: UUID, db: AsyncSession) -> int:
    """Fetch and parse a single feed. Returns number of new articles inserted."""
    feed = await db.scalar(
        select(Feed).where(Feed.id == feed_id).with_for_update(skip_locked=True)
    )
    if feed is None:
        logger.warning("feed_fetcher: feed %s not found or locked", feed_id)
        return 0

    logger.info("feed_fetcher: fetching %s (%s)", feed.title or feed.id, feed.url)

    headers = {"User-Agent": _USER_AGENT}
    if feed.last_etag:
        headers["If-None-Match"] = feed.last_etag
    if feed.last_modified:
        headers["If-Modified-Since"] = feed.last_modified

    status_code = 0
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0)) as client:
            resp = await client.get(feed.url, headers=headers, follow_redirects=True)
        status_code = resp.status_code

        if resp.status_code == 304:
            feed.last_fetched_at = datetime.utcnow()
            feed.error_count = 0
            feed.next_fetch_at = None
            await db.commit()
            logger.info("feed_fetcher: 304 Not Modified for %s", feed.url)
            return 0

        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}", request=resp.request, response=resp
            )

        content = resp.text

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        return await _handle_fetch_error(feed, db, status_code, str(exc))
    except Exception as exc:
        logger.error("feed_fetcher: unexpected error for %s: %s", feed.url, exc, exc_info=True)
        return await _handle_fetch_error(feed, db, 0, str(exc))

    # Parse with feedparser in thread pool (it's a sync library)
    loop = asyncio.get_running_loop()
    parsed = await loop.run_in_executor(None, feedparser.parse, content)

    # Update feed metadata from parsed feed
    feed_data = parsed.get("feed", {})
    if not feed.title and feed_data.get("title"):
        feed.title = feed_data["title"][:500]
    if not feed.site_url and feed_data.get("link"):
        feed.site_url = feed_data["link"][:2048]

    feed_language: str | None = feed_data.get("language")
    if feed_language:
        feed_language = feed_language[:2].lower()
        if not feed.language:
            feed.language = feed_language

    # Update caching headers
    etag = resp.headers.get("ETag")
    last_modified = resp.headers.get("Last-Modified")
    if etag:
        feed.last_etag = etag
    if last_modified:
        feed.last_modified = last_modified

    # Process entries
    new_count = 0
    for entry in parsed.get("entries", []):
        article = await _process_entry(entry, feed_language, feed.id, db)
        if article is not None:
            new_count += 1

    feed.last_fetched_at = datetime.utcnow()
    feed.last_status = status_code
    feed.error_count = 0
    feed.next_fetch_at = None
    await db.commit()

    logger.info("feed_fetcher: %s → %d new articles", feed.url, new_count)
    return new_count


async def _handle_fetch_error(feed: Feed, db: AsyncSession, status_code: int, msg: str) -> int:
    feed.error_count += 1
    feed.last_status = status_code
    feed.last_fetched_at = datetime.utcnow()

    backoff_min = min(feed.fetch_interval_min * (2 ** feed.error_count), _MAX_BACKOFF_MIN)
    feed.next_fetch_at = datetime.utcnow() + timedelta(minutes=backoff_min)

    if feed.error_count >= _MAX_ERRORS:
        feed.is_active = False
        logger.error(
            "feed_fetcher: %s disabled after %d errors", feed.url, feed.error_count
        )
    else:
        logger.warning(
            "feed_fetcher: %s returned %s, error_count=%d, next in %dm",
            feed.url, status_code, feed.error_count, backoff_min,
        )

    await db.commit()
    return 0


async def _fetch_feed_with_session(feed_id: UUID) -> None:
    """Wrapper used by the scheduler: creates its own DB session."""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await fetch_feed(feed_id, db)


def _is_feed_due(feed: Feed, now: datetime) -> bool:
    """Return True if this feed should be fetched now."""
    # Backoff overrides normal schedule
    if feed.next_fetch_at is not None:
        return feed.next_fetch_at <= now
    # Never fetched → due immediately
    if feed.last_fetched_at is None:
        return True
    # Regular interval check
    return feed.last_fetched_at + timedelta(minutes=feed.fetch_interval_min) <= now


async def fetch_all_due_feeds(db: AsyncSession) -> list[UUID]:
    """
    Find feeds that are due for polling and schedule them as background tasks.
    Returns the list of feed IDs that were scheduled.
    Processes at most 10 feeds per call to avoid overwhelming the event loop.
    """
    now = datetime.utcnow()

    result = await db.execute(
        select(Feed).where(Feed.is_active == True)  # noqa: E712
    )
    active_feeds = result.scalars().all()

    due = [f for f in active_feeds if _is_feed_due(f, now)][:10]
    feed_ids = [f.id for f in due]

    for feed_id in feed_ids:
        asyncio.create_task(_fetch_feed_with_session(feed_id))

    return feed_ids
