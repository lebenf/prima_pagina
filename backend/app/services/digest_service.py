# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article, FulltextStatus
from app.models.digest import Digest
from app.models.feed import Feed
from app.models.user import User
from app.models.user_feed import UserFeed
from app.schemas.digest import DigestGenerateOptions
from app.services.full_text import _extract_fulltext_sync
from app.services.llm.router import llm_router

logger = logging.getLogger(__name__)


class DigestError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def generate_digest(
    db: AsyncSession,
    user: User,
    options: DigestGenerateOptions,
) -> Digest:
    articles = await _select_articles(db, user, options)

    if not articles:
        raise DigestError("no_articles", "Nessun articolo trovato nel periodo selezionato")

    if options.force_fulltext:
        articles = list(await _ensure_fulltexts(articles))

    if options.llm_config_id:
        from app.models.llm_config import LLMConfig
        config = await db.get(LLMConfig, options.llm_config_id)
        if not config:
            raise DigestError("no_provider", "LLM config not found")
        from app.config import get_settings
        provider = llm_router._build_provider(config, get_settings().encryption_key)
    else:
        from app.config import get_settings
        provider = await llm_router.get_provider_for("digest", db, get_settings().encryption_key)

    if not provider:
        raise DigestError("no_provider", "Nessun provider LLM configurato per la generazione digest")

    articles_data = [_prepare_article_for_digest(a) for a in articles[:options.max_articles]]
    articles_data = [a for a in articles_data if a.get("excerpt") or a.get("fulltext")]

    if not articles_data:
        raise DigestError("no_articles", "Nessun articolo con contenuto disponibile")

    period_label = _format_period_label(options.period_start, options.period_end, user.preferred_lang)

    digest = Digest(
        user_id=user.id,
        title=None,
        period_start=options.period_start,
        period_end=options.period_end,
        content_html=None,
        content_text=None,
        virtual_feed_id=options.virtual_feed_id,
        llm_provider=provider.config.provider,
        llm_model=provider.config.model_name,
        article_count=len(articles_data),
        status="ok",
        generation_error=None,
    )

    try:
        result = await provider.generate_digest(
            articles=articles_data,
            period_label=period_label,
            output_language=user.preferred_lang,
        )
        content_html = _sanitize_digest_html(result.content_html)
        content_text = result.content_text or _html_to_text(content_html)
        digest.title = result.title
        digest.content_html = content_html
        digest.content_text = content_text
        digest.status = "ok"
    except asyncio.TimeoutError:
        timeout = getattr(provider.config, "timeout_sec", 300)
        digest.status = "failed"
        digest.generation_error = (
            f"Timeout: la generazione ha superato il limite configurato ({timeout}s)"
        )
    except Exception as e:
        digest.status = "failed"
        digest.generation_error = f"Errore generazione: {str(e)[:200]}"

    db.add(digest)
    await db.commit()
    await db.refresh(digest)

    if digest.status == "ok":
        logger.info(
            "digest generated for user %s: %d articles, provider=%s",
            user.id, len(articles_data), provider.config.provider,
        )
        asyncio.create_task(_dispatch_digest_notification(digest, user))
    else:
        logger.warning(
            "digest failed for user %s: %s", user.id, digest.generation_error
        )

    return digest


async def _dispatch_digest_notification(digest: Digest, user: "User") -> None:
    try:
        from app.config import get_settings
        from app.database import AsyncSessionLocal
        from app.plugins.base import NotificationEvent, NotificationPayload
        from app.plugins.manager import plugin_manager

        settings = get_settings()
        url = f"{settings.app_base_url}/digests/{digest.id}" if settings.app_base_url else None

        payload = NotificationPayload(
            event=NotificationEvent.DIGEST_READY,
            user_id=str(user.id),
            title=digest.title or "Rassegna Stampa",
            body=digest.content_text[:500] if digest.content_text else "",
            body_html=digest.content_html,
            url=url,
            metadata={"digest_id": str(digest.id), "article_count": digest.article_count},
        )
        async with AsyncSessionLocal() as db:
            await plugin_manager.dispatch(NotificationEvent.DIGEST_READY, payload, db)
    except Exception as e:
        logger.debug("digest notification dispatch error: %s", e)


async def _select_articles(
    db: AsyncSession,
    user: User,
    options: DigestGenerateOptions,
) -> list[Article]:
    from app.models.article_user_state import ArticleUserState
    from app.services.ranking import compute_category_affinity, score_article

    if options.virtual_feed_id:
        from app.models.virtual_feed import VirtualFeed
        from app.services.virtual_feed_service import get_virtual_feed_articles

        vf = await db.get(VirtualFeed, options.virtual_feed_id)
        if not vf:
            return []
        articles = await get_virtual_feed_articles(db, vf, limit=options.max_articles * 2)
        articles = [
            a for a in articles
            if _in_period(a.published_at or a.fetched_at, options.period_start, options.period_end)
        ]
        return articles

    # Subscribed feeds
    stmt = (
        select(Article)
        .join(Feed, Article.feed_id == Feed.id)
        .join(UserFeed, UserFeed.feed_id == Feed.id)
        .where(
            UserFeed.user_id == user.id,
            _period_condition(options.period_start, options.period_end),
        )
        .options(selectinload(Article.feed))
    )

    if options.category_ids:
        stmt = stmt.where(Feed.category_id.in_(options.category_ids))

    # Exclude archived articles
    archived_subq = (
        select(ArticleUserState.article_id)
        .where(
            ArticleUserState.user_id == user.id,
            ArticleUserState.is_archived == True,  # noqa: E712
        )
        .scalar_subquery()
    )
    stmt = stmt.where(Article.id.not_in(archived_subq))

    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    if not articles:
        return []

    # Score and sort
    affinity = await compute_category_affinity(db, user.id)
    read_ids = await _get_read_ids(db, user.id, [a.id for a in articles])

    def _score(a: Article) -> float:
        cat_id = a.feed.category_id if a.feed else None
        return score_article(
            published_at=a.published_at,
            source_weight=a.feed.source_weight if a.feed else 1.0,
            category_affinity=affinity.get(cat_id, 1.0) if cat_id else 1.0,
            is_read=a.id in read_ids,
        )

    articles.sort(key=_score, reverse=True)
    return articles[: options.max_articles * 2]


def _in_period(dt: datetime | None, start: datetime, end: datetime) -> bool:
    if dt is None:
        return False
    return start <= dt <= end


def _period_condition(start: datetime, end: datetime):
    from sqlalchemy import or_
    return or_(
        and_(Article.published_at >= start, Article.published_at <= end),
        and_(Article.published_at.is_(None), Article.fetched_at >= start, Article.fetched_at <= end),
    )


async def _get_read_ids(db: AsyncSession, user_id: UUID, article_ids: list[UUID]) -> set[UUID]:
    from app.models.article_user_state import ArticleUserState

    if not article_ids:
        return set()
    result = await db.execute(
        select(ArticleUserState.article_id)
        .where(
            ArticleUserState.user_id == user_id,
            ArticleUserState.article_id.in_(article_ids),
            ArticleUserState.is_read == True,  # noqa: E712
        )
    )
    return {row[0] for row in result.all()}


async def _ensure_fulltexts(
    articles: list[Article],
    timeout_per_article: float = 15.0,
) -> list[Article]:
    from app.services.full_text import _extract_fulltext_sync

    semaphore = asyncio.Semaphore(5)

    async def fetch_one(article: Article) -> Article:
        if article.content_fulltext:
            return article
        async with semaphore:
            try:
                loop = asyncio.get_event_loop()
                fulltext = await asyncio.wait_for(
                    loop.run_in_executor(None, _extract_fulltext_sync, article.url),  # patched in tests
                    timeout=timeout_per_article,
                )
                if fulltext and len(fulltext) > 200:
                    article.content_fulltext = fulltext
                    asyncio.create_task(_save_fulltext(article.id, fulltext))
            except (asyncio.TimeoutError, Exception) as e:
                logger.debug("fulltext fetch error for %s: %s", article.url, e)
        return article

    return list(await asyncio.gather(*[fetch_one(a) for a in articles]))


async def _save_fulltext(article_id: UUID, fulltext: str) -> None:
    try:
        from app.database import AsyncSessionLocal
        from app.models.article import FulltextStatus

        async with AsyncSessionLocal() as db:
            article = await db.get(Article, article_id)
            if article:
                article.content_fulltext = fulltext
                article.fulltext_status = FulltextStatus.OK.value
                article.fulltext_fetched_at = datetime.utcnow()
                await db.commit()
    except Exception as e:
        logger.debug("_save_fulltext background error for %s: %s", article_id, e)


def _prepare_article_for_digest(article: Article) -> dict:
    return {
        "title": article.title or "(senza titolo)",
        "source": article.feed.title if article.feed else "Fonte sconosciuta",
        "url": article.url or "",
        "author": article.author,
        "published": article.published_at.isoformat() if article.published_at else None,
        "tags": article.tags or [],
        "fulltext": article.content_fulltext,
        "excerpt": article.content_excerpt,
    }


def _sanitize_digest_html(html: str) -> str:
    import bleach

    allowed_tags = [
        "h1", "h2", "h3", "p", "a", "strong", "em",
        "ul", "ol", "li", "article", "cite", "blockquote", "br",
    ]
    allowed_attrs = {"a": ["href", "title", "target"]}
    clean = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    clean = clean.replace("<a ", '<a target="_blank" rel="noopener noreferrer" ')
    return clean


def _html_to_text(html: str) -> str:
    import bleach
    return bleach.clean(html, tags=[], strip=True)


def _format_period_label(start: datetime, end: datetime, lang: str) -> str:
    from babel.dates import format_date

    locale_map = {
        "it": "it_IT", "en": "en_US", "fr": "fr_FR",
        "de": "de_DE", "es": "es_ES", "pt": "pt_BR",
    }
    locale = locale_map.get(lang, "en_US")
    if start.date() == end.date():
        return format_date(start, format="long", locale=locale)
    return (
        f"{format_date(start, format='d MMMM', locale=locale)}"
        f" – {format_date(end, format='long', locale=locale)}"
    )


async def get_recent_digest(db: AsyncSession, user_id: UUID, hours: int = 20) -> Digest | None:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(Digest)
        .where(Digest.user_id == user_id, Digest.created_at >= cutoff)
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
