# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.llm_config import LLMConfig
from app.services.llm.base import TaggingResult, DigestResult


VALID_TAGGING_JSON = json.dumps({
    "tags": ["economia", "mercati"],
    "category_slug": "economy",
    "language": "it",
    "confidence": 0.88,
})

ENCRYPTION_KEY = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE="


def make_config(has_api_key: bool = False) -> LLMConfig:
    cfg = LLMConfig(
        provider="claude",
        model_name="claude-haiku-4-5-20251001",
        is_active=True,
    )
    if has_api_key:
        cfg.set_api_key("sk-ant-test-key", ENCRYPTION_KEY)
    return cfg


def make_message(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


@pytest.fixture
def mock_anthropic():
    with patch("app.services.llm.claude.anthropic") as mock_module:
        mock_client = AsyncMock()
        mock_module.AsyncAnthropic.return_value = mock_client
        mock_module.APIError = Exception
        yield mock_client


async def test_tag_article_success(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    mock_anthropic.messages.create = AsyncMock(
        return_value=make_message(VALID_TAGGING_JSON)
    )

    provider = ClaudeProvider(make_config())
    result = await provider.tag_article("Mercati in calo", "Le borse europee...", "it", ["economy", "world"])

    assert result.tags == ["economia", "mercati"]
    assert result.category_slug == "economy"
    assert result.confidence == pytest.approx(0.88)


async def test_tag_article_api_error(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    mock_anthropic.messages.create = AsyncMock(side_effect=Exception("API error"))

    provider = ClaudeProvider(make_config())
    result = await provider.tag_article("Title", "Excerpt", "it", [])

    assert isinstance(result, TaggingResult)
    assert result.tags == []
    assert result.confidence == 0.0


async def test_generate_digest_success(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    digest_html = "<h2>Economia</h2><article><h3>Mercati</h3><p>...</p><cite>Il Sole 24 Ore</cite></article>"
    mock_anthropic.messages.create = AsyncMock(return_value=make_message(digest_html))

    provider = ClaudeProvider(make_config())
    articles = [
        {"title": "Mercati in calo", "excerpt": "Le borse...", "source": "Il Sole 24 Ore", "url": "https://example.com"},
    ]
    result = await provider.generate_digest(articles, "21 aprile 2026", "it")

    assert isinstance(result, DigestResult)
    assert result.article_count == 1
    assert "Economia" in result.content_html
    assert result.content_text  # stripped HTML


async def test_digest_truncates_long_articles(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    mock_anthropic.messages.create = AsyncMock(return_value=make_message("<h2>Test</h2>"))

    provider = ClaudeProvider(make_config())
    # Create many articles to hit the 60k char limit
    articles = [
        {"title": f"Article {i}", "fulltext": "x" * 2000, "source": "src", "url": "https://x.com"}
        for i in range(100)
    ]
    result = await provider.generate_digest(articles, "today", "it")

    # All articles accepted in result count (the truncation is in the prompt, not result)
    assert result.article_count == 100
    # But the prompt was built — verify messages.create was called
    mock_anthropic.messages.create.assert_called_once()
    call_kwargs = mock_anthropic.messages.create.call_args
    # The user content should NOT exceed ~65k chars
    user_content = call_kwargs.kwargs.get("messages", [{}])[0].get("content", "")
    assert len(user_content) < 65_000


async def test_generate_digest_groups_multi_source_story(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    mock_anthropic.messages.create = AsyncMock(return_value=make_message("<h2>ok</h2>"))

    provider = ClaudeProvider(make_config())
    articles = [{
        "title": "Titolo evento",
        "excerpt": "Excerpt",
        "sources": [
            {"source": "Fonte A", "url": "https://a.example.com"},
            {"source": "Fonte B", "url": "https://b.example.com"},
        ],
    }]
    await provider.generate_digest(articles, "21 aprile 2026", "it")

    call_kwargs = mock_anthropic.messages.create.call_args
    user_content = call_kwargs.kwargs["messages"][0]["content"]
    assert "Fonte A" in user_content
    assert "Fonte B" in user_content
    assert "Fonti:" in user_content


async def test_generate_text_json_mode_prefills_and_reassembles(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    # The API returns only the continuation after our "{" prefill.
    mock_anthropic.messages.create = AsyncMock(
        return_value=make_message('"event_index": 1}')
    )

    provider = ClaudeProvider(make_config())
    result = await provider.generate_text("prompt", max_tokens=600, json_mode=True)

    call_kwargs = mock_anthropic.messages.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert messages[-1] == {"role": "assistant", "content": "{"}
    assert result == '{"event_index": 1}'
    assert json.loads(result) == {"event_index": 1}


async def test_generate_text_without_json_mode_no_prefill(mock_anthropic):
    from app.services.llm.claude import ClaudeProvider

    mock_anthropic.messages.create = AsyncMock(return_value=make_message("plain text"))

    provider = ClaudeProvider(make_config())
    result = await provider.generate_text("prompt")

    call_kwargs = mock_anthropic.messages.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert len(messages) == 1
    assert result == "plain text"


async def test_api_key_not_in_response(admin_client, db_session):
    """API key must never appear in GET /admin/llm-configs responses."""
    cfg = make_config(has_api_key=True)
    db_session.add(cfg)
    await db_session.commit()

    resp = await admin_client.get("/api/v1/admin/llm-configs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    for item in data:
        assert "api_key" not in item
        assert "api_key_encrypted" not in item
        assert item["has_api_key"] is True


async def test_config_encryption_roundtrip():
    """set_api_key + get_api_key must recover the original key."""
    cfg = make_config()
    original = "sk-ant-my-secret-key"
    cfg.set_api_key(original, ENCRYPTION_KEY)
    assert cfg.api_key_encrypted is not None
    assert original not in cfg.api_key_encrypted  # stored encrypted
    recovered = cfg.get_api_key(ENCRYPTION_KEY)
    assert recovered == original
