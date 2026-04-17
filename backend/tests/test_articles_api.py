"""Tests for GET/PATCH /api/v1/articles/* endpoints."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.article import Article, FulltextStatus
from app.models.article_user_state import ArticleUserState
from app.models.category import Category
from app.models.feed import Feed
from app.models.user_feed import UserFeed


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def subscribed_feed(db_session, regular_user):
    feed = Feed(url="https://sub.example.com/feed.xml", title="Subscribed Feed")
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


@pytest.fixture
async def unsubscribed_feed(db_session):
    feed = Feed(url="https://unsub.example.com/feed.xml", title="Unsubscribed Feed")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


def _make_article(feed_id, *, title="Article", offset_hours=0, tags=None):
    return Article(
        feed_id=feed_id,
        guid=str(uuid4()),
        title=title,
        url=f"https://example.com/{uuid4()}",
        published_at=datetime.utcnow() - timedelta(hours=offset_hours),
        fulltext_status=FulltextStatus.PENDING.value,
        tags=tags or [],
        tags_source="none",
    )


@pytest.fixture
async def articles(db_session, subscribed_feed, unsubscribed_feed):
    """3 subscribed + 1 unsubscribed article."""
    arts = [
        _make_article(subscribed_feed.id, title="Sub Article 1", offset_hours=2),
        _make_article(subscribed_feed.id, title="Sub Article 2", offset_hours=1),
        _make_article(subscribed_feed.id, title="Sub Article 3", offset_hours=0),
        _make_article(unsubscribed_feed.id, title="Unsub Article"),
    ]
    db_session.add_all(arts)
    await db_session.commit()
    return arts


@pytest.fixture
async def articles_with_tags(db_session, subscribed_feed):
    arts = [
        _make_article(subscribed_feed.id, title="Economy Article", tags=["economia", "finanza"]),
        _make_article(subscribed_feed.id, title="Finance Only", tags=["finanza"]),
        _make_article(subscribed_feed.id, title="No Tags"),
    ]
    db_session.add_all(arts)
    await db_session.commit()
    return arts


@pytest.fixture
async def articles_mixed_read(db_session, subscribed_feed, regular_user):
    read_art = _make_article(subscribed_feed.id, title="Read Article")
    unread_art = _make_article(subscribed_feed.id, title="Unread Article")
    db_session.add_all([read_art, unread_art])
    await db_session.flush()
    state = ArticleUserState(
        user_id=regular_user.id,
        article_id=read_art.id,
        is_read=True,
        read_at=datetime.utcnow(),
    )
    db_session.add(state)
    await db_session.commit()
    return {"read": read_art, "unread": unread_art}


@pytest.fixture
async def starred_articles(db_session, subscribed_feed, regular_user):
    starred = _make_article(subscribed_feed.id, title="Starred Article")
    plain = _make_article(subscribed_feed.id, title="Plain Article")
    db_session.add_all([starred, plain])
    await db_session.flush()
    state = ArticleUserState(
        user_id=regular_user.id,
        article_id=starred.id,
        is_starred=True,
    )
    db_session.add(state)
    await db_session.commit()
    return {"starred": starred, "plain": plain}


@pytest.fixture
async def one_article(db_session, subscribed_feed):
    art = _make_article(subscribed_feed.id, title="Single Article")
    art.url = "https://example.com/single"
    db_session.add(art)
    await db_session.commit()
    await db_session.refresh(art)
    return art


@pytest.fixture
async def feed_with_articles(db_session, subscribed_feed):
    arts = [_make_article(subscribed_feed.id, title=f"Art {i}") for i in range(5)]
    db_session.add_all(arts)
    await db_session.commit()
    return subscribed_feed


@pytest.fixture
async def many_articles(db_session, subscribed_feed):
    arts = [_make_article(subscribed_feed.id, title=f"Article {i}", offset_hours=i) for i in range(25)]
    db_session.add_all(arts)
    await db_session.commit()
    return arts


@pytest.fixture
async def category_with_feed(db_session, regular_user):
    cat = Category(slug="tech", name={"it": "Tecnologia", "en": "Technology"})
    db_session.add(cat)
    await db_session.flush()
    feed = Feed(url="https://tech.example.com/feed.xml", title="Tech Feed", category_id=cat.id)
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.flush()
    arts = [
        _make_article(feed.id, title=f"Tech {i}", offset_hours=i)
        for i in range(3)
    ]
    db_session.add_all(arts)
    await db_session.commit()
    return {"category": cat, "feed": feed, "articles": arts}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_list_articles_subscribed_only(user_client, articles):
    """Default: only articles from subscribed feeds are returned."""
    resp = await user_client.get("/api/v1/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    titles = {a["title"] for a in data["items"]}
    assert "Unsub Article" not in titles


async def test_list_articles_all(user_client, articles):
    """subscribed_only=false returns articles from all feeds."""
    resp = await user_client.get("/api/v1/articles", params={"subscribed_only": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4


async def test_filter_by_feed(user_client, articles, subscribed_feed):
    """feed_id filter returns only that feed's articles."""
    resp = await user_client.get(
        "/api/v1/articles", params={"feed_id": str(subscribed_feed.id), "subscribed_only": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for a in data["items"]:
        assert a["feed_id"] == str(subscribed_feed.id)


async def test_filter_by_tag(user_client, articles_with_tags):
    """tags filter returns articles containing ALL specified tags."""
    resp = await user_client.get(
        "/api/v1/articles", params={"tags": ["economia", "finanza"], "subscribed_only": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Economy Article"


async def test_filter_unread(user_client, articles_mixed_read):
    """is_read=false returns only unread articles."""
    resp = await user_client.get(
        "/api/v1/articles", params={"is_read": False, "subscribed_only": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    titles = [a["title"] for a in data["items"]]
    assert "Unread Article" in titles
    assert "Read Article" not in titles


async def test_filter_starred(user_client, starred_articles):
    """is_starred=true returns only starred articles."""
    resp = await user_client.get(
        "/api/v1/articles", params={"is_starred": True, "subscribed_only": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Starred Article"


async def test_article_detail_triggers_fulltext(user_client, one_article):
    """GET /articles/{id} triggers fulltext fetch and returns fulltext_loading=True."""
    from unittest.mock import patch

    with patch("app.services.article_service._schedule_fulltext") as mock_schedule:
        with patch("app.services.article_service.fulltext_svc.is_fetch_active", return_value=False):
            resp = await user_client.get(f"/api/v1/articles/{one_article.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["fulltext_loading"] is True
    mock_schedule.assert_called_once_with(one_article.id)


async def test_article_detail_no_double_fetch(user_client, one_article):
    """A second GET on the same article does not start another fetch if one is active."""
    from unittest.mock import patch

    with patch("app.services.article_service._schedule_fulltext") as mock_schedule:
        with patch("app.services.article_service.fulltext_svc.is_fetch_active", return_value=True):
            resp = await user_client.get(f"/api/v1/articles/{one_article.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["fulltext_loading"] is True
    mock_schedule.assert_not_called()


async def test_mark_article_read(user_client, one_article):
    """PATCH /articles/{id}/state marks article as read and sets read_at."""
    resp = await user_client.patch(
        f"/api/v1/articles/{one_article.id}/state",
        json={"is_read": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


async def test_mark_article_starred(user_client, one_article):
    """PATCH /articles/{id}/state can star an article."""
    resp = await user_client.patch(
        f"/api/v1/articles/{one_article.id}/state",
        json={"is_starred": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_starred"] is True


async def test_mark_feed_read(user_client, feed_with_articles, subscribed_feed):
    """POST /articles/mark-read marks all articles in the feed as read."""
    resp = await user_client.post(
        "/api/v1/articles/mark-read",
        json={"feed_id": str(subscribed_feed.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 5

    # Verify they're now read
    list_resp = await user_client.get(
        "/api/v1/articles",
        params={"is_read": False, "subscribed_only": False},
    )
    list_data = list_resp.json()
    assert list_data["total"] == 0


async def test_frontpage_structure(user_client, category_with_feed):
    """GET /articles/frontpage returns hero + second_row + columns."""
    resp = await user_client.get("/api/v1/articles/frontpage")
    assert resp.status_code == 200
    data = resp.json()
    assert "hero" in data
    assert "second_row" in data
    assert "columns" in data
    assert "digest_available" in data


async def test_frontpage_hero_highest_score(user_client, subscribed_feed, db_session):
    """The hero article is the highest-scored one (most recent)."""
    arts = [
        _make_article(subscribed_feed.id, title="New Article", offset_hours=1),
        _make_article(subscribed_feed.id, title="Old Article", offset_hours=30),
    ]
    db_session.add_all(arts)
    await db_session.commit()

    resp = await user_client.get("/api/v1/articles/frontpage")
    assert resp.status_code == 200
    data = resp.json()
    if data["hero"] is not None:
        assert data["hero"]["title"] == "New Article"


async def test_frontpage_excludes_unsubscribed(user_client, unsubscribed_feed, db_session):
    """Front page does not include articles from unsubscribed feeds."""
    art = _make_article(unsubscribed_feed.id, title="Unsubscribed Article")
    db_session.add(art)
    await db_session.commit()

    resp = await user_client.get("/api/v1/articles/frontpage")
    assert resp.status_code == 200
    data = resp.json()

    all_titles = set()
    if data["hero"]:
        all_titles.add(data["hero"]["title"])
    for a in data["second_row"]:
        all_titles.add(a["title"])
    for col in data["columns"]:
        for a in col["articles"]:
            all_titles.add(a["title"])

    assert "Unsubscribed Article" not in all_titles


async def test_fulltext_status_polling(user_client, one_article):
    """GET /articles/{id}/fulltext-status returns current status."""
    resp = await user_client.get(f"/api/v1/articles/{one_article.id}/fulltext-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == FulltextStatus.PENDING.value
    assert data["fulltext_available"] is False


async def test_pagination(user_client, many_articles):
    """Pagination returns correct page/total/pages metadata."""
    resp = await user_client.get("/api/v1/articles", params={"page": 1, "size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert data["pages"] == 3
    assert len(data["items"]) == 10

    resp2 = await user_client.get("/api/v1/articles", params={"page": 3, "size": 10})
    data2 = resp2.json()
    assert len(data2["items"]) == 5


async def test_unread_count(user_client, articles_mixed_read):
    """unread_count reflects total unread articles, not just those on the current page."""
    resp = await user_client.get(
        "/api/v1/articles", params={"subscribed_only": False, "page": 1, "size": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    # 1 read + 1 unread; total=2, unread_count should be 1
    assert data["unread_count"] == 1
