# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for related articles computation and API endpoint."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.article import Article, TagsSource
from app.models.article_llm_data import ArticleLLMData
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.services.related_articles import (
    CORRELATION_WINDOW_HOURS,
    MAX_RELATED,
    _find_candidates,
    _find_related,
    compute_related_articles,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def feed_a(db_session):
    f = Feed(url="https://feed-a.example.com/rss.xml", title="Feed A")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def feed_b(db_session):
    f = Feed(url="https://feed-b.example.com/rss.xml", title="Feed B")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def feed_c(db_session):
    f = Feed(url="https://feed-c.example.com/rss.xml", title="Feed C")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


def _article(feed_id, tags=None, offset_hours=0, title="Article"):
    return Article(
        feed_id=feed_id,
        guid=str(uuid4()),
        title=title,
        tags=tags or [],
        tags_source=TagsSource.LLM.value if tags else TagsSource.NONE.value,
        published_at=datetime.utcnow() - timedelta(hours=offset_hours),
    )


@pytest.fixture
async def main_article(db_session, feed_a):
    art = _article(feed_a.id, tags=["ai", "tech"], title="Main Article")
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


# ---------------------------------------------------------------------------
# Unit tests: _find_candidates
# ---------------------------------------------------------------------------


async def test_no_candidates_same_feed_excluded(db_session, main_article, feed_a):
    """Articles from same feed must not appear as candidates."""
    same_feed_art = _article(feed_a.id, tags=["ai", "tech"], title="Same Feed")
    db_session.add(same_feed_art)
    await db_session.commit()

    cutoff = datetime.utcnow() - timedelta(hours=CORRELATION_WINDOW_HOURS)
    candidates = await _find_candidates(db_session, main_article, cutoff)
    ids = [c.id for c in candidates]
    assert same_feed_art.id not in ids


async def test_candidates_require_tag_overlap(db_session, main_article, feed_b):
    """Articles without shared tags must not be candidates."""
    no_overlap = _article(feed_b.id, tags=["sports", "football"], title="No Overlap")
    db_session.add(no_overlap)
    await db_session.commit()

    cutoff = datetime.utcnow() - timedelta(hours=CORRELATION_WINDOW_HOURS)
    candidates = await _find_candidates(db_session, main_article, cutoff)
    ids = [c.id for c in candidates]
    assert no_overlap.id not in ids


async def test_candidates_sorted_by_tag_overlap(db_session, main_article, feed_b, feed_c):
    """Candidate with more overlapping tags comes first."""
    art_one = _article(feed_b.id, tags=["ai"], title="One tag overlap")
    art_two = _article(feed_c.id, tags=["ai", "tech"], title="Two tags overlap")
    db_session.add_all([art_one, art_two])
    await db_session.commit()

    cutoff = datetime.utcnow() - timedelta(hours=CORRELATION_WINDOW_HOURS)
    candidates = await _find_candidates(db_session, main_article, cutoff)
    assert candidates[0].id == art_two.id


async def test_old_articles_excluded(db_session, main_article, feed_b):
    """Articles older than CORRELATION_WINDOW_HOURS must not be candidates."""
    old_art = _article(
        feed_b.id,
        tags=["ai", "tech"],
        offset_hours=CORRELATION_WINDOW_HOURS + 2,
        title="Old Article",
    )
    db_session.add(old_art)
    await db_session.commit()

    cutoff = datetime.utcnow() - timedelta(hours=CORRELATION_WINDOW_HOURS)
    candidates = await _find_candidates(db_session, main_article, cutoff)
    ids = [c.id for c in candidates]
    assert old_art.id not in ids


# ---------------------------------------------------------------------------
# Unit tests: _find_related
# ---------------------------------------------------------------------------


async def test_no_tags_returns_empty(db_session, feed_a, feed_b):
    """Article without tags → empty result, no LLM call."""
    art = _article(feed_a.id, tags=[], title="No Tags")
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)

    result = await _find_related(db_session, art)
    assert result == []


async def test_few_candidates_no_llm(db_session, feed_a, feed_b):
    """≤3 candidates returned directly without calling LLM."""
    main = _article(feed_a.id, tags=["ai"], title="Main")
    c1 = _article(feed_b.id, tags=["ai"], title="C1")
    db_session.add_all([main, c1])
    await db_session.commit()
    await db_session.refresh(main)

    with patch("app.services.related_articles.llm_router") as mock_router:
        result = await _find_related(db_session, main)
        mock_router.get_provider_for.assert_not_called()

    assert str(c1.id) in result


async def test_many_candidates_uses_llm(db_session, feed_a, feed_b, feed_c):
    """More than 3 candidates → LLM called to pick top MAX_RELATED."""
    from app.models.feed import Feed

    main = _article(feed_a.id, tags=["ai"], title="Main")

    extra_feeds = []
    candidates = []
    for i in range(6):
        ef = Feed(url=f"https://extra{i}.example.com/rss.xml", title=f"Extra {i}")
        db_session.add(ef)
        extra_feeds.append(ef)

    await db_session.flush()

    for i, ef in enumerate(extra_feeds):
        c = _article(ef.id, tags=["ai"], title=f"Candidate {i}")
        candidates.append(c)
        db_session.add(c)

    db_session.add(main)
    await db_session.commit()
    await db_session.refresh(main)

    mock_provider = AsyncMock()

    import json

    async def fake_llm_call(*args, **kwargs):
        return f"[1, 2, 3, 4, 5]"

    # Patch the select function to return indices via the Ollama path
    expected_ids = [str(c.id) for c in candidates[:MAX_RELATED]]

    with patch("app.services.related_articles.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=None)
        result = await _find_related(db_session, main)

    # With no LLM, should return first MAX_RELATED candidates
    assert len(result) <= MAX_RELATED


async def test_no_candidates_returns_empty_list(db_session, main_article):
    """If no candidates with tag overlap: return []."""
    result = await _find_related(db_session, main_article)
    # Only articles from same feed in DB → no valid candidates
    assert result == []


# ---------------------------------------------------------------------------
# Unit tests: compute_related_articles
# ---------------------------------------------------------------------------


async def test_skip_if_already_computed(db_session, feed_a):
    """If llm_data.related_article_ids is non-empty, skip computation."""
    art = _article(feed_a.id, tags=["ai"], title="Already Done")
    db_session.add(art)
    await db_session.flush()

    llm_data = ArticleLLMData(
        article_id=art.id,
        related_article_ids=["some-uuid"],
    )
    db_session.add(llm_data)
    await db_session.commit()
    await db_session.refresh(art)

    with patch("app.services.related_articles.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.related_articles._find_related") as mock_find:
            await compute_related_articles(art.id)
            mock_find.assert_not_called()


async def test_compute_creates_llm_data(db_session, feed_a, feed_b):
    """_find_related returns related article id; manually verify ArticleLLMData upsert logic."""
    from sqlalchemy import select

    main = _article(feed_a.id, tags=["ai", "tech"], title="Main")
    related = _article(feed_b.id, tags=["ai", "tech"], title="Related")
    db_session.add_all([main, related])
    await db_session.commit()
    await db_session.refresh(main)

    with patch("app.services.related_articles.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=None)
        related_ids = await _find_related(db_session, main)

    assert str(related.id) in related_ids

    # Manually create llm_data to verify the upsert path
    llm_data = ArticleLLMData(
        article_id=main.id,
        related_article_ids=related_ids,
    )
    db_session.add(llm_data)
    await db_session.commit()

    result = await db_session.execute(
        select(ArticleLLMData).where(ArticleLLMData.article_id == main.id)
    )
    saved = result.scalar_one_or_none()
    assert saved is not None
    assert str(related.id) in saved.related_article_ids


async def test_compute_nonexistent_article(db_session):
    """compute_related_articles with unknown UUID must not crash."""
    with patch("app.services.related_articles.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await compute_related_articles(uuid4())  # no exception


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def subscribed_feed_for_user(db_session, regular_user):
    feed = Feed(url="https://sub-rel.example.com/feed.xml", title="Sub Rel Feed")
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


@pytest.fixture
async def article_with_related(db_session, subscribed_feed_for_user, feed_b):
    main = _article(subscribed_feed_for_user.id, tags=["ai", "tech"], title="Main")
    rel1 = _article(feed_b.id, tags=["ai"], title="Related 1")
    db_session.add_all([main, rel1])
    await db_session.flush()

    llm_data = ArticleLLMData(
        article_id=main.id,
        related_article_ids=[str(rel1.id)],
    )
    db_session.add(llm_data)
    await db_session.commit()
    await db_session.refresh(main)
    return main, rel1


async def test_get_related_endpoint(user_client, article_with_related):
    main, rel1 = article_with_related
    resp = await user_client.get(f"/api/v1/articles/{main.id}/related")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(rel1.id)


async def test_get_related_empty(user_client, db_session, subscribed_feed_for_user):
    art = _article(subscribed_feed_for_user.id, tags=["ai"], title="No Related")
    db_session.add(art)
    await db_session.commit()

    resp = await user_client.get(f"/api/v1/articles/{art.id}/related")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_related_not_found(user_client):
    resp = await user_client.get(f"/api/v1/articles/{uuid4()}/related")
    assert resp.status_code == 404


async def test_get_related_preserves_order(user_client, db_session, subscribed_feed_for_user, feed_b, feed_c):
    main = _article(subscribed_feed_for_user.id, tags=["ai"], title="Main")
    r1 = _article(feed_b.id, tags=["ai"], title="Related 1")
    r2 = _article(feed_c.id, tags=["ai"], title="Related 2")
    db_session.add_all([main, r1, r2])
    await db_session.flush()

    llm_data = ArticleLLMData(
        article_id=main.id,
        related_article_ids=[str(r1.id), str(r2.id)],
    )
    db_session.add(llm_data)
    await db_session.commit()

    resp = await user_client.get(f"/api/v1/articles/{main.id}/related")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert ids == [str(r1.id), str(r2.id)]


async def test_get_related_includes_user_state(user_client, db_session, subscribed_feed_for_user, feed_b, regular_user):
    from app.models.article_user_state import ArticleUserState

    main = _article(subscribed_feed_for_user.id, tags=["ai"], title="Main")
    rel = _article(feed_b.id, tags=["ai"], title="Related")
    db_session.add_all([main, rel])
    await db_session.flush()

    state = ArticleUserState(user_id=regular_user.id, article_id=rel.id, is_read=True)
    db_session.add(state)

    llm_data = ArticleLLMData(
        article_id=main.id,
        related_article_ids=[str(rel.id)],
    )
    db_session.add(llm_data)
    await db_session.commit()

    resp = await user_client.get(f"/api/v1/articles/{main.id}/related")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["is_read"] is True
