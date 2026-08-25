# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the per-function LLM provider router."""
import pytest

from app.models.llm_config import LLMConfig
from app.models.llm_function_assignment import LLMFunction, LLMFunctionAssignment
from app.services.llm.ollama import OllamaProvider
from app.services.llm.router import LLMRouter


def make_config(**kwargs) -> LLMConfig:
    cfg = LLMConfig(
        provider=kwargs.get("provider", "ollama"),
        model_name=kwargs.get("model_name", "llama3.2"),
        is_active=kwargs.get("is_active", True),
    )
    return cfg


def make_assignment(function: str, primary=None, fallback=None) -> LLMFunctionAssignment:
    return LLMFunctionAssignment(
        function=function,
        primary_config_id=primary.id if primary else None,
        fallback_config_id=fallback.id if fallback else None,
    )


async def test_get_provider_for_returns_primary(db_session):
    config = make_config()
    db_session.add(config)
    await db_session.flush()
    assignment = make_assignment(LLMFunction.TAGGING.value, primary=config)
    db_session.add(assignment)
    await db_session.commit()

    router = LLMRouter()
    provider = await router.get_provider_for(LLMFunction.TAGGING, db_session)
    assert isinstance(provider, OllamaProvider)


async def test_get_provider_for_uses_fallback_when_primary_inactive(db_session):
    primary = make_config(is_active=False)
    fallback = make_config(model_name="llama3.2-fallback")
    db_session.add_all([primary, fallback])
    await db_session.flush()
    assignment = make_assignment(LLMFunction.DIGEST.value, primary=primary, fallback=fallback)
    db_session.add(assignment)
    await db_session.commit()

    router = LLMRouter()
    provider = await router.get_provider_for(LLMFunction.DIGEST, db_session)
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama3.2-fallback"


async def test_get_provider_for_uses_fallback_when_primary_missing(db_session):
    fallback = make_config(model_name="llama3.2-fallback")
    db_session.add(fallback)
    await db_session.flush()
    assignment = make_assignment(LLMFunction.DIGEST.value, primary=None, fallback=fallback)
    db_session.add(assignment)
    await db_session.commit()

    router = LLMRouter()
    provider = await router.get_provider_for(LLMFunction.DIGEST, db_session)
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama3.2-fallback"


async def test_get_provider_for_returns_none_when_both_empty(db_session):
    assignment = make_assignment(LLMFunction.RELATED_ARTICLES.value)
    db_session.add(assignment)
    await db_session.commit()

    router = LLMRouter()
    provider = await router.get_provider_for(LLMFunction.RELATED_ARTICLES, db_session)
    assert provider is None


async def test_get_provider_for_returns_none_when_both_inactive(db_session):
    primary = make_config(is_active=False)
    fallback = make_config(is_active=False)
    db_session.add_all([primary, fallback])
    await db_session.flush()
    assignment = make_assignment(LLMFunction.EXTRACTION_SCRIPT.value, primary=primary, fallback=fallback)
    db_session.add(assignment)
    await db_session.commit()

    router = LLMRouter()
    provider = await router.get_provider_for(LLMFunction.EXTRACTION_SCRIPT, db_session)
    assert provider is None


async def test_get_provider_for_unassigned_function_returns_none(db_session):
    router = LLMRouter()
    provider = await router.get_provider_for(LLMFunction.EVENT_SUMMARY, db_session)
    assert provider is None


async def test_get_provider_for_accepts_plain_string(db_session):
    config = make_config()
    db_session.add(config)
    await db_session.flush()
    assignment = make_assignment("tagging", primary=config)
    db_session.add(assignment)
    await db_session.commit()

    router = LLMRouter()
    provider = await router.get_provider_for("tagging", db_session)
    assert isinstance(provider, OllamaProvider)


async def test_build_provider_mistral(db_session):
    from app.services.llm.mistral import MistralProvider

    config = make_config(provider="mistral", model_name="mistral-large-latest")
    router = LLMRouter()
    provider = router._build_provider(config, encryption_key="")
    assert isinstance(provider, MistralProvider)


async def test_build_provider_hostyourai(db_session):
    from app.services.llm.hostyourai import HostYourAIProvider

    config = make_config(provider="hostyourai", model_name="qwen3.5-397b-a17b")
    router = LLMRouter()
    provider = router._build_provider(config, encryption_key="")
    assert isinstance(provider, HostYourAIProvider)


async def test_build_provider_unknown_raises():
    config = make_config(provider="unknown-provider")
    router = LLMRouter()
    with pytest.raises(ValueError):
        router._build_provider(config)
