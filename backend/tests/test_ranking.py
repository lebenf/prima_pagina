# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/ranking.py"""
import math
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.article import Article, FulltextStatus
from app.models.article_user_state import ArticleUserState
from app.models.category import Category
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.services.ranking import (
    compute_category_affinity,
    recency_score,
    score_article,
)


# ---------------------------------------------------------------------------
# recency_score
# ---------------------------------------------------------------------------


def test_recency_new_article():
    """An article published now should have a score close to 1.0."""
    s = recency_score(datetime.utcnow())
    assert 0.99 <= s <= 1.0


def test_recency_half_life_12h():
    """An article published 12 hours ago should have score ~0.5."""
    published = datetime.utcnow() - timedelta(hours=12)
    s = recency_score(published)
    assert abs(s - 0.5) < 0.01


def test_recency_48h_decay():
    """An article 48 hours old should have a much lower score."""
    published = datetime.utcnow() - timedelta(hours=48)
    s = recency_score(published)
    expected = math.exp(-48 * math.log(2) / 12)  # ≈ 0.063
    assert abs(s - expected) < 0.01


def test_recency_none_published_at():
    """None published_at returns 0.0."""
    assert recency_score(None) == 0.0


# ---------------------------------------------------------------------------
# score_article
# ---------------------------------------------------------------------------


def test_read_penalty():
    """A read article gets 0.1× penalty."""
    published = datetime.utcnow() - timedelta(hours=1)
    unread_score = score_article(published_at=published)
    read_score = score_article(published_at=published, is_read=True)
    assert abs(read_score / unread_score - 0.1) < 0.001


def test_source_weight():
    """source_weight scales the score linearly."""
    published = datetime.utcnow() - timedelta(hours=1)
    s1 = score_article(published_at=published, source_weight=1.0)
    s2 = score_article(published_at=published, source_weight=2.0)
    assert abs(s2 / s1 - 2.0) < 0.001


def test_category_affinity_scaling():
    """category_affinity scales the score linearly."""
    published = datetime.utcnow() - timedelta(hours=1)
    s1 = score_article(published_at=published, category_affinity=1.0)
    s2 = score_article(published_at=published, category_affinity=2.0)
    assert abs(s2 / s1 - 2.0) < 0.001


# ---------------------------------------------------------------------------
# compute_category_affinity
# ---------------------------------------------------------------------------


async def test_category_affinity_no_history(db_session, regular_user):
    """User with no reading history returns empty dict."""
    affinity = await compute_category_affinity(db_session, regular_user.id)
    assert affinity == {}


async def test_category_affinity_with_reads(db_session, regular_user):
    """User who reads mainly from one category gets high affinity for it."""
    cat_a = Category(slug="cat-a", name={"en": "Cat A"})
    cat_b = Category(slug="cat-b", name={"en": "Cat B"})
    db_session.add_all([cat_a, cat_b])
    await db_session.flush()

    feed_a = Feed(url="https://a.example.com/feed.xml", category_id=cat_a.id)
    feed_b = Feed(url="https://b.example.com/feed.xml", category_id=cat_b.id)
    db_session.add_all([feed_a, feed_b])
    await db_session.flush()

    # 4 articles in A, 1 in B → user reads all 5
    articles_a = [
        Article(
            feed_id=feed_a.id, guid=str(uuid4()), fulltext_status="pending",
            tags=[], tags_source="none",
            published_at=datetime.utcnow() - timedelta(days=1),
        )
        for _ in range(4)
    ]
    article_b = Article(
        feed_id=feed_b.id, guid=str(uuid4()), fulltext_status="pending",
        tags=[], tags_source="none",
        published_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add_all(articles_a + [article_b])
    await db_session.flush()

    now = datetime.utcnow()
    states = [
        ArticleUserState(
            user_id=regular_user.id, article_id=a.id,
            is_read=True, read_at=now,
        )
        for a in articles_a + [article_b]
    ]
    db_session.add_all(states)
    await db_session.commit()

    affinity = await compute_category_affinity(db_session, regular_user.id)

    # cat_a has 4/5 reads → higher affinity than cat_b (1/5)
    assert cat_a.id in affinity
    assert cat_b.id in affinity
    assert affinity[cat_a.id] > affinity[cat_b.id]
    # All values clamped to [0.5, 2.0]
    for v in affinity.values():
        assert 0.5 <= v <= 2.0


async def test_frontpage_ordering(db_session, regular_user):
    """Higher-scored articles appear before lower-scored ones in the front page."""
    feed = Feed(url="https://fp.example.com/feed.xml", title="FP Feed")
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.flush()

    new_art = Article(
        feed_id=feed.id, guid=str(uuid4()), title="New Article",
        fulltext_status="pending", tags=[], tags_source="none",
        published_at=datetime.utcnow() - timedelta(hours=1),
    )
    old_art = Article(
        feed_id=feed.id, guid=str(uuid4()), title="Old Article",
        fulltext_status="pending", tags=[], tags_source="none",
        published_at=datetime.utcnow() - timedelta(hours=40),
    )
    db_session.add_all([new_art, old_art])
    await db_session.commit()

    from app.services.article_service import get_frontpage_articles
    result = await get_frontpage_articles(db_session, regular_user.id, "en")

    # The most recent article should be the hero
    assert result.hero is not None
    assert result.hero.title == "New Article"
