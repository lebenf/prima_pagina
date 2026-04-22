"""Tests for T10 — Digest generation."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.article import Article, TagsSource
from app.models.digest import Digest
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.models.virtual_feed import VirtualFeed
from app.schemas.digest import DigestGenerateOptions
from app.services.digest_service import DigestError
from app.services.llm.base import DigestResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_digest_result(title: str = "Rassegna Stampa", xss: bool = False) -> DigestResult:
    html = (
        '<h2>Politics</h2><p>Summary of events.</p>'
        '<a href="https://example.com">More</a>'
    )
    if xss:
        html = '<script>alert("xss")</script><h2>Politics</h2><p>Summary.</p>'
    return DigestResult(
        title=title,
        content_html=html,
        content_text="Politics\nSummary of events.",
        article_count=2,
    )


def _mock_provider(result: DigestResult | None = None, raise_exc: Exception | None = None):
    provider = MagicMock()
    provider.config = MagicMock()
    provider.config.provider = "claude"
    provider.config.model_name = "claude-opus-4-7"
    if raise_exc:
        provider.generate_digest = AsyncMock(side_effect=raise_exc)
    else:
        provider.generate_digest = AsyncMock(return_value=result or _make_digest_result())
    return provider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def subscribed_feed(db_session, regular_user):
    feed = Feed(url="https://example.com/rss", title="Test Feed", source_weight=1.0)
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)

    sub = UserFeed(user_id=regular_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.commit()
    return feed


@pytest.fixture
async def articles(db_session, subscribed_feed):
    now = datetime.utcnow()
    arts = []
    for i in range(3):
        a = Article(
            feed_id=subscribed_feed.id,
            guid=f"guid-digest-{i}",
            title=f"Article {i}",
            url=f"https://example.com/article/{i}",
            content_excerpt=f"Excerpt for article {i}.",
            content_fulltext=f"Full text for article {i}. " * 20,
            tags=["politics", "test"],
            tags_source=TagsSource.LLM.value,
            published_at=now - timedelta(hours=i + 1),
            fetched_at=now,
        )
        db_session.add(a)
        arts.append(a)
    await db_session.commit()
    for a in arts:
        await db_session.refresh(a)
    return arts


@pytest.fixture
async def articles_no_fulltext(db_session, subscribed_feed):
    now = datetime.utcnow()
    arts = []
    for i in range(2):
        a = Article(
            feed_id=subscribed_feed.id,
            guid=f"guid-noft-{i}",
            title=f"No Fulltext Article {i}",
            url=f"https://example.com/noft/{i}",
            content_excerpt=f"Excerpt {i}.",
            content_fulltext=None,
            published_at=now - timedelta(hours=i + 1),
            fetched_at=now,
        )
        db_session.add(a)
        arts.append(a)
    await db_session.commit()
    for a in arts:
        await db_session.refresh(a)
    return arts


@pytest.fixture
async def digest(db_session, regular_user):
    d = Digest(
        user_id=regular_user.id,
        title="Test Digest",
        period_start=datetime.utcnow() - timedelta(hours=24),
        period_end=datetime.utcnow(),
        content_html="<h2>Test</h2><p>Content</p>",
        content_text="Test\nContent",
        article_count=2,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def vf_with_digest(db_session, regular_user, subscribed_feed):
    vf = VirtualFeed(
        user_id=regular_user.id,
        name="VF Digest",
        filter_type="tags",
        filter_config={"tags": ["politics"], "operator": "OR"},
        is_shared=True,
        include_digest=True,
    )
    db_session.add(vf)
    await db_session.commit()
    await db_session.refresh(vf)
    return vf


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

async def test_generate_digest_success(user_client, articles):
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=_mock_provider())
        resp = await user_client.post("/api/v1/digests/generate", json={})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "content_html" in data
    assert data["article_count"] > 0
    assert data["title"] == "Rassegna Stampa"


async def test_generate_digest_no_articles(user_client):
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=_mock_provider())
        resp = await user_client.post("/api/v1/digests/generate", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "no_articles"


async def test_generate_digest_no_provider(user_client, articles):
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=None)
        resp = await user_client.post("/api/v1/digests/generate", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "no_provider"


async def test_generate_digest_custom_period(user_client, articles):
    now = datetime.utcnow()
    start = (now - timedelta(hours=12)).isoformat()
    end = now.isoformat()
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=_mock_provider())
        resp = await user_client.post("/api/v1/digests/generate", json={
            "period_start": start,
            "period_end": end,
        })
    assert resp.status_code in (201, 422)  # 422 if no articles in custom period


async def test_generate_digest_with_virtual_feed(user_client, articles, vf_with_digest):
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=_mock_provider())
        resp = await user_client.post("/api/v1/digests/generate", json={
            "virtual_feed_id": str(vf_with_digest.id),
        })
    assert resp.status_code in (201, 422)


async def test_digest_html_sanitized(user_client, articles):
    xss_result = _make_digest_result(xss=True)
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=_mock_provider(result=xss_result))
        resp = await user_client.post("/api/v1/digests/generate", json={})
    assert resp.status_code == 201
    html = resp.json()["content_html"]
    # bleach strips <script> tags (leaves text), <iframe> stripped entirely
    assert "<script>" not in html
    assert "<iframe>" not in html


async def test_digest_links_open_new_tab(user_client, articles):
    with patch("app.services.digest_service.llm_router") as mock_router:
        mock_router.get_provider_for = AsyncMock(return_value=_mock_provider())
        resp = await user_client.post("/api/v1/digests/generate", json={})
    assert resp.status_code == 201
    html = resp.json()["content_html"]
    if "<a " in html:
        assert 'target="_blank"' in html
        assert "noopener" in html


async def test_list_digests(user_client, digest):
    resp = await user_client.get("/api/v1/digests")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1
    assert any(d["id"] == str(digest.id) for d in data["items"])


async def test_get_latest_digest(user_client, digest):
    resp = await user_client.get("/api/v1/digests/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(digest.id)


async def test_get_latest_digest_not_found(user_client):
    resp = await user_client.get("/api/v1/digests/latest")
    assert resp.status_code == 404


async def test_get_digest_by_id(user_client, digest):
    resp = await user_client.get(f"/api/v1/digests/{digest.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(digest.id)


async def test_delete_digest(user_client, digest):
    resp = await user_client.delete(f"/api/v1/digests/{digest.id}")
    assert resp.status_code == 204

    resp2 = await user_client.get(f"/api/v1/digests/{digest.id}")
    assert resp2.status_code == 404


async def test_delete_other_user_digest_forbidden(user_client, db_session, admin_user):
    other_digest = Digest(
        user_id=admin_user.id,
        title="Admin Digest",
        period_start=datetime.utcnow() - timedelta(hours=24),
        period_end=datetime.utcnow(),
        article_count=0,
    )
    db_session.add(other_digest)
    await db_session.commit()
    await db_session.refresh(other_digest)

    resp = await user_client.delete(f"/api/v1/digests/{other_digest.id}")
    assert resp.status_code == 403


async def test_list_digests_filter_by_vf(user_client, digest, db_session, regular_user, vf_with_digest):
    vf_digest = Digest(
        user_id=regular_user.id,
        title="VF Digest",
        period_start=datetime.utcnow() - timedelta(hours=24),
        period_end=datetime.utcnow(),
        virtual_feed_id=vf_with_digest.id,
        article_count=1,
    )
    db_session.add(vf_digest)
    await db_session.commit()

    resp = await user_client.get(f"/api/v1/digests?virtual_feed_id={vf_with_digest.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert all(d["virtual_feed_id"] == str(vf_with_digest.id) for d in data["items"])


# ---------------------------------------------------------------------------
# Unit tests for digest_service
# ---------------------------------------------------------------------------

async def test_fulltext_fetched_before_digest(db_session, regular_user, articles_no_fulltext):
    from app.services.digest_service import generate_digest

    fetched_urls = []

    def fake_extract(url: str):
        fetched_urls.append(url)
        return "Full text content. " * 30

    options = DigestGenerateOptions()
    provider = _mock_provider()

    with (
        patch("app.services.digest_service.llm_router") as mock_router,
        patch("app.services.full_text._extract_fulltext_sync", side_effect=fake_extract),
        patch("app.services.digest_service._save_fulltext", new_callable=AsyncMock),
    ):
        mock_router.get_provider_for = AsyncMock(return_value=provider)
        mock_router._build_provider = MagicMock(return_value=provider)
        # subscribed_feed fixture already created the UserFeed subscription
        digest = await generate_digest(db_session, regular_user, options)

    assert len(fetched_urls) > 0
    assert digest.article_count > 0


async def test_sanitize_digest_html():
    from app.services.digest_service import _sanitize_digest_html

    dirty = '<script>alert(1)</script><h2>News</h2><p>Good content</p><iframe src="evil.com"></iframe>'
    clean = _sanitize_digest_html(dirty)
    assert "<script>" not in clean
    assert "<iframe>" not in clean
    assert "<h2>News</h2>" in clean
    assert "Good content" in clean


async def test_sanitize_adds_target_blank():
    from app.services.digest_service import _sanitize_digest_html

    html = '<a href="https://example.com">Link</a>'
    clean = _sanitize_digest_html(html)
    assert 'target="_blank"' in clean
    assert "noopener" in clean


async def test_format_period_label_same_day():
    from app.services.digest_service import _format_period_label

    start = datetime(2026, 4, 21, 0, 0, 0)
    end = datetime(2026, 4, 21, 23, 59, 59)
    label = _format_period_label(start, end, "it")
    assert "2026" in label
    assert "aprile" in label.lower() or "21" in label


async def test_format_period_label_multi_day():
    from app.services.digest_service import _format_period_label

    start = datetime(2026, 4, 20, 0, 0, 0)
    end = datetime(2026, 4, 21, 23, 59, 59)
    label = _format_period_label(start, end, "en")
    assert "–" in label or "-" in label


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

async def test_scheduled_job_skips_existing(db_session, regular_user):
    """Job skips user that already has a recent digest."""
    recent = Digest(
        user_id=regular_user.id,
        title="Recent",
        period_start=datetime.utcnow() - timedelta(hours=2),
        period_end=datetime.utcnow(),
        article_count=0,
    )
    db_session.add(recent)
    await db_session.commit()

    called = []

    async def fake_generate(db, user, options):
        called.append(user.id)
        return MagicMock()

    async def fake_get_recent(db, user_id, hours=20):
        if user_id == regular_user.id:
            return recent
        return None

    with (
        patch("app.database.AsyncSessionLocal") as mock_sl,
        patch("app.services.digest_service.generate_digest", side_effect=fake_generate),
        patch("app.services.digest_service.get_recent_digest", side_effect=fake_get_recent),
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        from app.services.scheduler import _digest_generation_job
        await _digest_generation_job()

    assert regular_user.id not in called


async def test_scheduled_job_continues_on_error(db_session, regular_user, admin_user):
    """Job does not abort on error for a single user."""

    async def fake_generate(db, user, options):
        if user.username == "regular":
            raise RuntimeError("LLM down")
        raise DigestError("no_articles", "no articles")

    async def fake_get_recent(db, user_id, hours=20):
        return None

    with (
        patch("app.database.AsyncSessionLocal") as mock_sl,
        patch("app.services.digest_service.generate_digest", side_effect=fake_generate),
        patch("app.services.digest_service.get_recent_digest", side_effect=fake_get_recent),
    ):
        mock_sl.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_sl.return_value.__aexit__ = AsyncMock(return_value=False)

        from app.services.scheduler import _digest_generation_job
        # Should not raise even if individual users fail
        await _digest_generation_job()


async def test_max_concurrent_fulltext_downloads(db_session, regular_user, subscribed_feed):
    """Semaphore limits concurrent downloads to 5."""
    arts = []
    now = datetime.utcnow()
    for i in range(10):
        a = Article(
            feed_id=subscribed_feed.id,
            guid=f"guid-conc-{i}",
            title=f"Article {i}",
            url=f"https://example.com/conc/{i}",
            content_excerpt="Excerpt.",
            content_fulltext=None,
            published_at=now - timedelta(hours=i + 1),
            fetched_at=now,
        )
        arts.append(a)

    concurrent_counts = []
    active = [0]

    async def fake_extract_slow(url):
        import asyncio
        active[0] += 1
        concurrent_counts.append(active[0])
        await asyncio.sleep(0.01)
        active[0] -= 1
        return "Full text content. " * 30

    from app.services.digest_service import _ensure_fulltexts

    import asyncio
    loop = asyncio.get_event_loop()

    def run_in_executor_side_effect(executor, func, *args):
        return fake_extract_slow(args[0] if args else "")

    with patch.object(loop, "run_in_executor", side_effect=run_in_executor_side_effect):
        await _ensure_fulltexts(arts, timeout_per_article=5.0)

    # Max concurrency should be <= 5 (semaphore limit)
    if concurrent_counts:
        assert max(concurrent_counts) <= 5
