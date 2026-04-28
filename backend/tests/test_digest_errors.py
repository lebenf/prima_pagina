# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
async def subscribed_feed(db_session, admin_user):
    from app.models.feed import Feed
    from app.models.user_feed import UserFeed
    feed = Feed(url="https://example.com/feed.xml", title="Test Feed")
    db_session.add(feed)
    await db_session.flush()
    sub = UserFeed(user_id=admin_user.id, feed_id=feed.id)
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


@pytest.fixture
async def articles_in_feed(db_session, subscribed_feed):
    from app.models.article import Article
    articles = []
    now = datetime.utcnow()
    for i in range(3):
        a = Article(
            feed_id=subscribed_feed.id,
            guid=f"guid-{i}",
            title=f"Article {i}",
            url=f"https://example.com/article{i}",
            published_at=now - timedelta(hours=i),
            content_excerpt=f"Excerpt {i}",
            tags=[],
        )
        db_session.add(a)
        articles.append(a)
    await db_session.commit()
    return articles


async def test_digest_failure_saves_error(db_session, admin_user, articles_in_feed):
    from app.models.llm_config import LLMConfig
    from app.schemas.digest import DigestGenerateOptions
    from app.services.digest_service import generate_digest

    config = LLMConfig(
        label="test",
        provider="ollama",
        model_name="llama3",
        is_active=True,
        use_for=["digest"],
        is_default=True,
        timeout_sec=60,
    )
    db_session.add(config)
    await db_session.commit()

    with patch(
        "app.services.llm.router.LLMRouter.get_provider_for",
        new_callable=AsyncMock,
    ) as mock_provider_fn:
        mock_provider = AsyncMock()
        mock_provider.config = config
        mock_provider.generate_digest = AsyncMock(side_effect=Exception("LLM error"))
        mock_provider_fn.return_value = mock_provider

        now = datetime.utcnow()
        options = DigestGenerateOptions(
            period_start=now - timedelta(hours=24),
            period_end=now,
        )
        digest = await generate_digest(db_session, admin_user, options)

    assert digest.status == "failed"
    assert digest.generation_error is not None
    assert "LLM error" in digest.generation_error


async def test_digest_failure_status_in_response(admin_client, articles_in_feed):
    with patch(
        "app.services.llm.router.LLMRouter.get_provider_for",
        new_callable=AsyncMock,
    ) as mock_provider_fn:
        from unittest.mock import MagicMock
        mock_config = MagicMock()
        mock_config.provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.timeout_sec = 60

        mock_provider = AsyncMock()
        mock_provider.config = mock_config
        mock_provider.generate_digest = AsyncMock(side_effect=RuntimeError("boom"))
        mock_provider_fn.return_value = mock_provider

        resp = await admin_client.post("/api/v1/digests/generate", json={})

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "failed"
    assert data["generation_error"] is not None


async def test_digest_success_status_ok(admin_client, articles_in_feed):
    with patch(
        "app.services.llm.router.LLMRouter.get_provider_for",
        new_callable=AsyncMock,
    ) as mock_provider_fn:
        from unittest.mock import MagicMock
        mock_config = MagicMock()
        mock_config.provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.timeout_sec = 60

        mock_result = MagicMock()
        mock_result.title = "Test Digest"
        mock_result.content_html = "<p>Content</p>"
        mock_result.content_text = "Content"

        mock_provider = AsyncMock()
        mock_provider.config = mock_config
        mock_provider.generate_digest = AsyncMock(return_value=mock_result)
        mock_provider_fn.return_value = mock_provider

        resp = await admin_client.post("/api/v1/digests/generate", json={})

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ok"
    assert data["generation_error"] is None
