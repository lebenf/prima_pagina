import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.article import Article, TagsSource
from app.models.category import Category
from app.models.feed import Feed
from app.services.llm.base import TaggingResult
from app.services.llm.tagging import (
    _tag_article,
    enqueue_article_for_tagging,
    tagging_queue,
)


@pytest.fixture
async def feed(db_session):
    f = Feed(url="https://example.com/rss.xml", title="Test Feed")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def article(db_session, feed):
    art = Article(
        feed_id=feed.id,
        guid="guid-test-001",
        title="AI rivoluziona la tecnologia",
        content_excerpt="L'intelligenza artificiale...",
        language="it",
        tags=[],
        tags_source=TagsSource.NONE.value,
    )
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


@pytest.fixture
async def tagged_article(db_session, feed):
    art = Article(
        feed_id=feed.id,
        guid="guid-tagged-001",
        title="Already tagged",
        tags=["tech"],
        tags_source=TagsSource.LLM.value,
    )
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


@pytest.fixture
async def category(db_session):
    cat = Category(slug="technology", name={"it": "Tecnologia", "en": "Technology"})
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


async def test_enqueue_article():
    # Drain queue first
    while not tagging_queue.empty():
        tagging_queue.get_nowait()

    art_id = uuid.uuid4()
    await enqueue_article_for_tagging(art_id)
    assert not tagging_queue.empty()
    assert tagging_queue.get_nowait() == art_id


async def test_queue_full_no_exception():
    """put_nowait on a full queue must NOT raise — just log warning."""
    small_queue: asyncio.Queue[uuid.UUID] = asyncio.Queue(maxsize=1)
    small_queue.put_nowait(uuid.uuid4())  # fill it

    with patch("app.services.llm.tagging.tagging_queue", small_queue):
        # This should not raise
        await enqueue_article_for_tagging(uuid.uuid4())


async def test_worker_processes_article(db_session, article, category):
    mock_result = TaggingResult(
        tags=["ai", "tech"],
        category_slug="technology",
        language="it",
        confidence=0.95,
    )
    mock_provider = AsyncMock()
    mock_provider.tag_article = AsyncMock(return_value=mock_result)

    with patch("app.services.llm.tagging.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=mock_provider)
        with patch("app.services.llm.tagging.AsyncSessionLocal") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _tag_article(article.id)

    await db_session.refresh(article)
    assert article.tags == ["ai", "tech"]
    assert article.tags_source == TagsSource.LLM.value


async def test_worker_skips_already_tagged(db_session, tagged_article):
    mock_provider = AsyncMock()

    with patch("app.services.llm.tagging.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=mock_provider)
        with patch("app.services.llm.tagging.AsyncSessionLocal") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _tag_article(tagged_article.id)

    # Provider must NOT be called for already-tagged articles
    mock_provider.tag_article.assert_not_called()


async def test_worker_continues_on_error(db_session, article):
    """Worker must survive single-article errors and keep running."""
    call_count = 0

    async def failing_provider(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("LLM exploded")

    mock_provider = AsyncMock()
    mock_provider.tag_article = failing_provider

    with patch("app.services.llm.tagging.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=mock_provider)
        with patch("app.services.llm.tagging.AsyncSessionLocal") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            try:
                await _tag_article(article.id)
            except RuntimeError:
                pass  # _tag_article itself may propagate but tagging_worker catches it

    # Article should still be untagged (error before commit)
    await db_session.refresh(article)
    assert article.tags_source == TagsSource.NONE.value


async def test_no_provider_configured(db_session, article):
    """If no LLM provider is configured, article stays untagged."""
    with patch("app.services.llm.tagging.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=None)
        with patch("app.services.llm.tagging.AsyncSessionLocal") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _tag_article(article.id)

    await db_session.refresh(article)
    assert article.tags_source == TagsSource.NONE.value


async def test_category_assigned_high_confidence(db_session, article, feed, category):
    """High-confidence result with matching category slug should set feed.category_id."""
    mock_result = TaggingResult(
        tags=["ai"],
        category_slug="technology",
        language="it",
        confidence=0.95,
    )
    mock_provider = AsyncMock()
    mock_provider.tag_article = AsyncMock(return_value=mock_result)

    with patch("app.services.llm.tagging.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=mock_provider)
        with patch("app.services.llm.tagging.AsyncSessionLocal") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _tag_article(article.id)

    await db_session.refresh(feed)
    assert feed.category_id == category.id
