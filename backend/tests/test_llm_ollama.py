# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import uuid

import httpx
import pytest
import respx

from app.models.llm_config import LLMConfig
from app.services.llm.ollama import OllamaProvider
from app.services.llm.base import TaggingResult


def make_config(**kwargs) -> LLMConfig:
    cfg = LLMConfig(
        provider="ollama",
        model_name=kwargs.get("model_name", "llama3.2"),
        endpoint_url=kwargs.get("endpoint_url", "http://localhost:11434"),
        use_for=["tagging", "digest"],
        is_default=True,
        is_active=True,
        priority=0,
    )
    return cfg


VALID_TAGGING_RESPONSE = json.dumps({
    "tags": ["intelligenza artificiale", "tecnologia", "machine learning"],
    "category_slug": "technology",
    "language": "it",
    "confidence": 0.92,
})

GENERATE_URL = "http://localhost:11434/api/generate"
TAGS_URL = "http://localhost:11434/api/tags"


@respx.mock
async def test_tag_article_valid_response():
    respx.post(GENERATE_URL).mock(
        return_value=httpx.Response(200, json={"response": VALID_TAGGING_RESPONSE})
    )
    provider = OllamaProvider(make_config())
    result = await provider.tag_article(
        "AI rivoluziona il settore tech",
        "L'intelligenza artificiale sta trasformando il mondo del lavoro.",
        "it",
        ["technology", "science", "economy"],
    )
    assert result.tags == ["intelligenza artificiale", "tecnologia", "machine learning"]
    assert result.category_slug == "technology"
    assert result.language == "it"
    assert result.confidence == pytest.approx(0.92)


@respx.mock
async def test_tag_article_invalid_json():
    respx.post(GENERATE_URL).mock(
        return_value=httpx.Response(200, json={"response": "not valid json at all"})
    )
    provider = OllamaProvider(make_config())
    result = await provider.tag_article("Title", "Excerpt", "it", ["tech"])
    # Bad JSON → empty TaggingResult, no exception
    assert result.tags == []
    assert result.category_slug is None
    assert result.confidence == 0.0


@respx.mock
async def test_tag_article_timeout():
    respx.post(GENERATE_URL).mock(side_effect=httpx.TimeoutException("timeout"))
    provider = OllamaProvider(make_config())
    result = await provider.tag_article("Title", "Excerpt", "it", ["tech"])
    assert isinstance(result, TaggingResult)
    assert result.tags == []


@respx.mock
async def test_health_check_ok():
    respx.get(TAGS_URL).mock(return_value=httpx.Response(200, json={"models": []}))
    provider = OllamaProvider(make_config())
    assert await provider.health_check() is True


@respx.mock
async def test_health_check_down():
    respx.get(TAGS_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    provider = OllamaProvider(make_config())
    assert await provider.health_check() is False


@respx.mock
async def test_prompt_contains_categories():
    captured = {}

    async def capture(request, route):
        body = json.loads(request.content)
        captured["prompt"] = body["prompt"]
        return httpx.Response(200, json={"response": VALID_TAGGING_RESPONSE})

    respx.post(GENERATE_URL).mock(side_effect=capture)

    provider = OllamaProvider(make_config())
    categories = ["technology", "science", "world"]
    await provider.tag_article("Title", "Excerpt", "it", categories)

    assert "technology" in captured["prompt"]
    assert "science" in captured["prompt"]
    assert "world" in captured["prompt"]


@respx.mock
async def test_tag_article_tags_capped_at_five():
    many_tags = json.dumps({
        "tags": ["a", "b", "c", "d", "e", "f", "g"],
        "category_slug": None,
        "language": "it",
        "confidence": 0.8,
    })
    respx.post(GENERATE_URL).mock(
        return_value=httpx.Response(200, json={"response": many_tags})
    )
    provider = OllamaProvider(make_config())
    result = await provider.tag_article("T", "E", "it", [])
    assert len(result.tags) == 5


@respx.mock
async def test_tag_article_custom_endpoint():
    endpoint = "http://my-ollama:11434"
    generate_url = f"{endpoint}/api/generate"
    respx.post(generate_url).mock(
        return_value=httpx.Response(200, json={"response": VALID_TAGGING_RESPONSE})
    )
    provider = OllamaProvider(make_config(endpoint_url=endpoint))
    result = await provider.tag_article("Title", "Excerpt", "it", [])
    assert result.tags != [] or result.confidence == pytest.approx(0.92)
