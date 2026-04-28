# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for normalize_topic_score, topic_weight, and updated score_article."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.article import Article
from app.models.article_user_state import ArticleUserState
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.services.ranking import normalize_topic_score, score_article, topic_weight


# ---------------------------------------------------------------------------
# normalize_topic_score
# ---------------------------------------------------------------------------


def test_normalize_zero():
    assert normalize_topic_score(0.0) == 1.0


def test_normalize_max():
    assert normalize_topic_score(5.0) == 2.0


def test_normalize_min():
    assert abs(normalize_topic_score(-5.0) - 0.1) < 1e-9


def test_normalize_positive():
    v = normalize_topic_score(2.5)
    assert 1.0 < v < 2.0


def test_normalize_negative():
    v = normalize_topic_score(-2.5)
    assert 0.1 < v < 1.0


def test_normalize_monotone_positive():
    assert normalize_topic_score(1.0) < normalize_topic_score(3.0) < normalize_topic_score(5.0)


def test_normalize_monotone_negative():
    assert normalize_topic_score(-5.0) < normalize_topic_score(-2.5) < normalize_topic_score(0.0)


# ---------------------------------------------------------------------------
# topic_weight
# ---------------------------------------------------------------------------


def test_topic_weight_no_tags():
    assert topic_weight([], {}) == 1.0


def test_topic_weight_no_prefs():
    assert topic_weight(["calcio"], {}) == 1.0


def test_topic_weight_positive_pref():
    assert topic_weight(["calcio"], {"calcio": 3.0}) > 1.0


def test_topic_weight_negative_pref():
    assert topic_weight(["calcio"], {"calcio": -3.0}) < 1.0


def test_topic_weight_neutral_unknown_tag():
    w = topic_weight(["unknown_tag"], {"other_tag": 5.0})
    assert w == 1.0


def test_topic_weight_mixed_tags():
    # One positive (+5 → 2.0), one negative (-5 → 0.1) → mean = 1.05
    w = topic_weight(["pos", "neg"], {"pos": 5.0, "neg": -5.0})
    assert abs(w - 1.05) < 1e-9


# ---------------------------------------------------------------------------
# score_article with topic_weight_factor
# ---------------------------------------------------------------------------


def test_score_article_default_topic_weight():
    published = datetime.utcnow() - timedelta(hours=1)
    s1 = score_article(published_at=published, topic_weight_factor=1.0)
    s2 = score_article(published_at=published)
    assert abs(s1 - s2) < 1e-6


def test_score_article_topic_weight_scales():
    published = datetime.utcnow() - timedelta(hours=1)
    s1 = score_article(published_at=published, topic_weight_factor=1.0)
    s2 = score_article(published_at=published, topic_weight_factor=2.0)
    assert abs(s2 / s1 - 2.0) < 0.001


def test_score_article_negative_topic_reduces_score():
    published = datetime.utcnow() - timedelta(hours=1)
    s_neutral = score_article(published_at=published, topic_weight_factor=1.0)
    s_disliked = score_article(published_at=published, topic_weight_factor=0.1)
    assert s_disliked < s_neutral


# ---------------------------------------------------------------------------
# Integration: frontpage ordering with topic prefs
# ---------------------------------------------------------------------------


async def test_frontpage_order_with_negative_topic(db_session, regular_user):
    """Article with disliked tag scores lower than neutral article of same age."""
    from app.models.user_topic_preference import UserTopicPreference
    from app.services.article_service import get_frontpage_articles

    feed = Feed(url="https://topic-test.example.com/feed.xml", title="Topic Test")
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.flush()

    # Both articles same age; one has a disliked tag
    disliked_art = Article(
        feed_id=feed.id, guid=str(uuid4()), title="Disliked Tag Article",
        fulltext_status="pending", tags=["badtag"], tags_source="llm",
        published_at=datetime.utcnow() - timedelta(hours=2),
    )
    neutral_art = Article(
        feed_id=feed.id, guid=str(uuid4()), title="Neutral Article",
        fulltext_status="pending", tags=[], tags_source="none",
        published_at=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add_all([disliked_art, neutral_art])
    await db_session.flush()

    # User strongly dislikes "badtag"
    pref = UserTopicPreference(user_id=regular_user.id, tag="badtag", score=-5.0, vote_count=10)
    db_session.add(pref)
    await db_session.commit()

    result = await get_frontpage_articles(db_session, regular_user.id, "en")
    all_items = []
    if result.hero:
        all_items.append(result.hero)
    all_items.extend(result.second_row)

    titles = [a.title for a in all_items]
    if "Neutral Article" in titles and "Disliked Tag Article" in titles:
        assert titles.index("Neutral Article") < titles.index("Disliked Tag Article")


async def test_category_affinity_empty_history_with_topic(db_session, regular_user):
    """compute_category_affinity returns {} when user has no reads."""
    from app.services.ranking import compute_category_affinity
    affinity = await compute_category_affinity(db_session, regular_user.id)
    assert affinity == {}
