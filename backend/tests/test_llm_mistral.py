# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json

import httpx
import pytest
import respx

from app.models.llm_config import LLMConfig
from app.services.llm.base import TaggingResult
from app.services.llm.mistral import MistralProvider

ENCRYPTION_KEY = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE="


def make_config(**kwargs) -> LLMConfig:
    cfg = LLMConfig(
        provider="mistral",
        model_name=kwargs.get("model_name", "mistral-large-latest"),
        endpoint_url=kwargs.get("endpoint_url"),
        is_active=True,
    )
    if kwargs.get("has_api_key", True):
        cfg.set_api_key("test-mistral-key", ENCRYPTION_KEY)
    return cfg


VALID_TAGGING_RESPONSE = json.dumps({
    "tags": ["intelligenza artificiale", "tecnologia"],
    "category_slug": "technology",
    "language": "it",
    "confidence": 0.9,
})

CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
MODELS_URL = "https://api.mistral.ai/v1/models"


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


@respx.mock
async def test_tag_article_valid_response():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_chat_response(VALID_TAGGING_RESPONSE))
    )
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.tag_article(
        "AI rivoluziona il settore tech",
        "L'intelligenza artificiale...",
        "it",
        ["technology", "science"],
    )
    assert result.tags == ["intelligenza artificiale", "tecnologia"]
    assert result.category_slug == "technology"
    assert result.confidence == pytest.approx(0.9)


@respx.mock
async def test_tag_article_invalid_json():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_chat_response("not valid json"))
    )
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.tag_article("Title", "Excerpt", "it", ["tech"])
    assert isinstance(result, TaggingResult)
    assert result.tags == []


@respx.mock
async def test_tag_article_timeout():
    respx.post(CHAT_URL).mock(side_effect=httpx.TimeoutException("timeout"))
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.tag_article("Title", "Excerpt", "it", ["tech"])
    assert result.tags == []


@respx.mock
async def test_generate_text():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_chat_response("hello world"))
    )
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.generate_text("some prompt", max_tokens=50)
    assert result == "hello world"


@respx.mock
async def test_generate_text_error_returns_empty_string():
    respx.post(CHAT_URL).mock(return_value=httpx.Response(500))
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.generate_text("some prompt")
    assert result == ""


@respx.mock
async def test_health_check_ok():
    respx.get(MODELS_URL).mock(return_value=httpx.Response(200, json={"data": []}))
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    assert await provider.health_check() is True


@respx.mock
async def test_health_check_down():
    respx.get(MODELS_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    assert await provider.health_check() is False


@respx.mock
async def test_custom_endpoint():
    endpoint = "https://my-mistral-proxy.example.com"
    respx.post(f"{endpoint}/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_response(VALID_TAGGING_RESPONSE))
    )
    provider = MistralProvider(make_config(endpoint_url=endpoint), encryption_key=ENCRYPTION_KEY)
    result = await provider.tag_article("Title", "Excerpt", "it", [])
    assert result.tags == ["intelligenza artificiale", "tecnologia"]


async def test_no_api_key_resolves_to_empty_string():
    provider = MistralProvider(make_config(has_api_key=False), encryption_key=ENCRYPTION_KEY)
    assert provider.api_key == ""


@respx.mock
async def test_generate_digest_strips_chat_preamble():
    raw = (
        "Ecco un **press digest professionale** in italiano per le date "
        "30-31 luglio 2026, strutturato in HTML con sezioni tematiche.\n\n"
        "```html\n<h2>Italia</h2><article><h3>Titolo</h3><p>Riassunto</p></article>\n```"
    )
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, json=_chat_response(raw)))
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.generate_digest(
        [{"source": "Test", "title": "Titolo", "excerpt": "Excerpt"}],
        "30-31 luglio 2026",
        "it",
    )
    assert result.content_html.startswith("<h2>Italia</h2>")
    assert "Ecco un" not in result.content_html
    assert "```" not in result.content_html


@respx.mock
async def test_generate_digest_no_fence_still_strips_preamble():
    raw = "Certo, ecco la rassegna richiesta:\n<h2>Italia</h2><p>Testo</p>"
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, json=_chat_response(raw)))
    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.generate_digest(
        [{"source": "Test", "title": "Titolo", "excerpt": "Excerpt"}],
        "30-31 luglio 2026",
        "it",
    )
    assert result.content_html == "<h2>Italia</h2><p>Testo</p>"


@respx.mock
async def test_generate_digest_includes_article_url():
    captured = {}

    async def capture(request, route):
        body = json.loads(request.content)
        captured["content"] = body["messages"][0]["content"]
        return httpx.Response(200, json=_chat_response("<h2>ok</h2>"))

    respx.post(CHAT_URL).mock(side_effect=capture)

    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    await provider.generate_digest(
        [{"source": "Test", "title": "Titolo", "excerpt": "Excerpt", "url": "https://example.com/a"}],
        "30-31 luglio 2026",
        "it",
    )
    assert "https://example.com/a" in captured["content"]


@respx.mock
async def test_generate_digest_groups_multi_source_story():
    captured = {}

    async def capture(request, route):
        body = json.loads(request.content)
        captured["content"] = body["messages"][0]["content"]
        return httpx.Response(200, json=_chat_response("<h2>ok</h2>"))

    respx.post(CHAT_URL).mock(side_effect=capture)

    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    await provider.generate_digest(
        [{
            "title": "Titolo evento",
            "excerpt": "Excerpt",
            "sources": [
                {"source": "Fonte A", "url": "https://a.example.com"},
                {"source": "Fonte B", "url": "https://b.example.com"},
            ],
        }],
        "30-31 luglio 2026",
        "it",
    )
    assert "Fonte A" in captured["content"]
    assert "Fonte B" in captured["content"]
    assert "Fonti:" in captured["content"]


@respx.mock
async def test_generate_text_json_mode_sets_response_format():
    captured = {}

    async def capture(request, route):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_chat_response('{"event_index": 1}'))

    respx.post(CHAT_URL).mock(side_effect=capture)

    provider = MistralProvider(make_config(), encryption_key=ENCRYPTION_KEY)
    result = await provider.generate_text("prompt", max_tokens=600, json_mode=True)

    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert result == '{"event_index": 1}'
