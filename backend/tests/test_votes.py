# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for vote endpoints and vote_service."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.article import Article
from app.models.article_vote import ArticleVote
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.models.user_topic_preference import UserTopicPreference
from app.services.vote_service import (
    SCORE_MAX,
    SCORE_MIN,
    VOTE_DELTA,
    cast_vote,
    get_topic_preferences,
    get_user_vote,
    load_user_votes_bulk,
    remove_vote,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def feed_with_sub(db_session, regular_user):
    feed = Feed(url="https://vote-test.example.com/feed.xml", title="Vote Feed")
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


def _make_article(feed_id, tags=None):
    return Article(
        feed_id=feed_id,
        guid=str(uuid4()),
        fulltext_status="pending",
        tags=tags or [],
        tags_source="llm" if tags else "none",
        published_at=datetime.utcnow() - timedelta(hours=1),
    )


@pytest.fixture
async def article_with_tags(db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["calcio", "sport"])
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


@pytest.fixture
async def article_no_tags(db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=[])
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


async def test_cast_vote_up(db_session, regular_user, article_with_tags):
    resp = await cast_vote(db_session, regular_user.id, article_with_tags.id, 1)
    assert resp.vote == 1
    assert set(resp.topic_scores_updated) == {"calcio", "sport"}

    vote = await db_session.get(ArticleVote, (regular_user.id, article_with_tags.id))
    assert vote is not None
    assert vote.vote == 1


async def test_cast_vote_down(db_session, regular_user, article_with_tags):
    resp = await cast_vote(db_session, regular_user.id, article_with_tags.id, -1)
    assert resp.vote == -1

    pref_calcio = await db_session.get(UserTopicPreference, (regular_user.id, "calcio"))
    assert pref_calcio is not None
    assert pref_calcio.score < 0


async def test_vote_upsert_changes_direction(db_session, regular_user, article_with_tags):
    await cast_vote(db_session, regular_user.id, article_with_tags.id, 1)
    await cast_vote(db_session, regular_user.id, article_with_tags.id, -1)

    vote = await db_session.get(ArticleVote, (regular_user.id, article_with_tags.id))
    assert vote.vote == -1

    # Only one row must exist
    from sqlalchemy import select
    result = await db_session.execute(
        select(ArticleVote).where(
            ArticleVote.user_id == regular_user.id,
            ArticleVote.article_id == article_with_tags.id,
        )
    )
    assert len(result.scalars().all()) == 1


async def test_remove_vote(db_session, regular_user, article_with_tags):
    await cast_vote(db_session, regular_user.id, article_with_tags.id, 1)
    resp = await remove_vote(db_session, regular_user.id, article_with_tags.id)
    assert resp.vote == 0

    vote = await db_session.get(ArticleVote, (regular_user.id, article_with_tags.id))
    assert vote is None


async def test_remove_nonexistent_vote(db_session, regular_user, article_no_tags):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await remove_vote(db_session, regular_user.id, article_no_tags.id)
    assert exc_info.value.status_code == 404


async def test_vote_updates_topic_prefs(db_session, regular_user, article_with_tags):
    await cast_vote(db_session, regular_user.id, article_with_tags.id, 1)

    prefs = await get_topic_preferences(db_session, regular_user.id)
    assert "calcio" in prefs
    assert "sport" in prefs
    assert prefs["calcio"] == VOTE_DELTA
    assert prefs["sport"] == VOTE_DELTA


async def test_vote_delta_correct_on_direction_change(db_session, regular_user, article_with_tags):
    # Start at +1 → delta = +0.5
    await cast_vote(db_session, regular_user.id, article_with_tags.id, 1)
    prefs_after_up = await get_topic_preferences(db_session, regular_user.id)
    assert prefs_after_up["calcio"] == pytest.approx(VOTE_DELTA)

    # Flip to -1 → net delta from (+1 to -1) = (-2) * 0.5 = -1.0
    await cast_vote(db_session, regular_user.id, article_with_tags.id, -1)
    prefs_after_flip = await get_topic_preferences(db_session, regular_user.id)
    assert prefs_after_flip["calcio"] == pytest.approx(VOTE_DELTA + (-2) * VOTE_DELTA)


async def test_score_clamped_at_max(db_session, regular_user, feed_with_sub):
    """Many upvotes on same tag must not exceed SCORE_MAX."""
    tag = "calcio"
    for i in range(30):
        art = _make_article(feed_with_sub.id, tags=[tag])
        db_session.add(art)
        await db_session.flush()
        await cast_vote(db_session, regular_user.id, art.id, 1)

    prefs = await get_topic_preferences(db_session, regular_user.id)
    assert prefs[tag] <= SCORE_MAX


async def test_score_clamped_at_min(db_session, regular_user, feed_with_sub):
    """Many downvotes on same tag must not go below SCORE_MIN."""
    tag = "calcio"
    for i in range(30):
        art = _make_article(feed_with_sub.id, tags=[tag])
        db_session.add(art)
        await db_session.flush()
        await cast_vote(db_session, regular_user.id, art.id, -1)

    prefs = await get_topic_preferences(db_session, regular_user.id)
    assert prefs[tag] >= SCORE_MIN


async def test_get_user_vote_no_vote(db_session, regular_user, article_no_tags):
    v = await get_user_vote(db_session, regular_user.id, article_no_tags.id)
    assert v == 0


async def test_load_user_votes_bulk(db_session, regular_user, feed_with_sub):
    art1 = _make_article(feed_with_sub.id)
    art2 = _make_article(feed_with_sub.id)
    art3 = _make_article(feed_with_sub.id)
    db_session.add_all([art1, art2, art3])
    await db_session.flush()

    await cast_vote(db_session, regular_user.id, art1.id, 1)
    await cast_vote(db_session, regular_user.id, art2.id, -1)

    bulk = await load_user_votes_bulk(db_session, regular_user.id, [art1.id, art2.id, art3.id])
    assert bulk[art1.id] == 1
    assert bulk[art2.id] == -1
    assert art3.id not in bulk


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


async def test_api_cast_vote_up(user_client, db_session, regular_user, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    db_session.add(art)
    await db_session.commit()

    resp = await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["vote"] == 1
    assert "tech" in data["topic_scores_updated"]


async def test_api_cast_vote_down(user_client, db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    db_session.add(art)
    await db_session.commit()

    resp = await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": -1})
    assert resp.status_code == 200
    assert resp.json()["vote"] == -1


async def test_api_vote_upsert(user_client, db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    db_session.add(art)
    await db_session.commit()

    await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": 1})
    resp = await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": -1})
    assert resp.status_code == 200
    assert resp.json()["vote"] == -1


async def test_api_remove_vote(user_client, db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    db_session.add(art)
    await db_session.commit()

    await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": 1})
    resp = await user_client.delete(f"/api/v1/articles/{art.id}/vote")
    assert resp.status_code == 200
    assert resp.json()["vote"] == 0


async def test_api_remove_nonexistent_vote(user_client, db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id)
    db_session.add(art)
    await db_session.commit()

    resp = await user_client.delete(f"/api/v1/articles/{art.id}/vote")
    assert resp.status_code == 404


async def test_article_vote_in_list_response(user_client, db_session, regular_user, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    db_session.add(art)
    await db_session.commit()

    await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": 1})

    resp = await user_client.get("/api/v1/articles", params={"subscribed_only": True})
    assert resp.status_code == 200
    items = resp.json()["items"]
    voted = next((i for i in items if i["id"] == str(art.id)), None)
    assert voted is not None
    assert voted["user_vote"] == 1


async def test_article_vote_in_detail_response(user_client, db_session, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    art.url = "https://example.com/tech-article"
    db_session.add(art)
    await db_session.commit()

    await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": -1})

    from unittest.mock import patch
    with patch("app.services.article_service._schedule_fulltext"):
        with patch("app.services.article_service.fulltext_svc.is_fetch_active", return_value=True):
            resp = await user_client.get(f"/api/v1/articles/{art.id}")
    assert resp.status_code == 200
    assert resp.json()["user_vote"] == -1


async def test_article_vote_in_frontpage(user_client, db_session, regular_user, feed_with_sub):
    art = _make_article(feed_with_sub.id, tags=["tech"])
    db_session.add(art)
    await db_session.commit()

    await user_client.post(f"/api/v1/articles/{art.id}/vote", json={"vote": 1})

    resp = await user_client.get("/api/v1/articles/frontpage")
    assert resp.status_code == 200
    data = resp.json()

    all_items = []
    if data["hero"]:
        all_items.append(data["hero"])
    all_items.extend(data["second_row"])
    for col in data["columns"]:
        all_items.extend(col["articles"])

    voted = next((i for i in all_items if i["id"] == str(art.id)), None)
    if voted is not None:
        assert voted["user_vote"] == 1
