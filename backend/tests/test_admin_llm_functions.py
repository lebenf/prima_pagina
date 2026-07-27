# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GET/PUT /api/v1/admin/llm-functions."""
import pytest

from app.models.llm_config import LLMConfig


@pytest.fixture
async def ollama_config(db_session):
    cfg = LLMConfig(provider="ollama", model_name="llama3.2", is_active=True)
    db_session.add(cfg)
    await db_session.commit()
    await db_session.refresh(cfg)
    return cfg


@pytest.fixture
async def inactive_config(db_session):
    cfg = LLMConfig(provider="ollama", model_name="llama3.2-old", is_active=False)
    db_session.add(cfg)
    await db_session.commit()
    await db_session.refresh(cfg)
    return cfg


async def test_list_llm_functions_returns_all_five_on_empty_db(admin_client):
    resp = await admin_client.get("/api/v1/admin/llm-functions")
    assert resp.status_code == 200
    data = resp.json()
    functions = {item["function"] for item in data}
    assert functions == {"tagging", "event_summary", "extraction_script", "related_articles", "digest"}
    for item in data:
        assert item["primary_config_id"] is None
        assert item["fallback_config_id"] is None


async def test_list_llm_functions_requires_admin(user_client):
    resp = await user_client.get("/api/v1/admin/llm-functions")
    assert resp.status_code == 403


async def test_update_llm_function_assignment(admin_client, ollama_config):
    resp = await admin_client.put(
        "/api/v1/admin/llm-functions/tagging",
        json={"primary_config_id": str(ollama_config.id), "fallback_config_id": None},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["function"] == "tagging"
    assert data["primary_config_id"] == str(ollama_config.id)

    # Persisted — a second GET reflects it
    resp2 = await admin_client.get("/api/v1/admin/llm-functions")
    row = next(item for item in resp2.json() if item["function"] == "tagging")
    assert row["primary_config_id"] == str(ollama_config.id)


async def test_update_llm_function_with_fallback(admin_client, ollama_config, db_session):
    fallback_cfg = LLMConfig(provider="claude", model_name="claude-haiku", is_active=True)
    db_session.add(fallback_cfg)
    await db_session.commit()
    await db_session.refresh(fallback_cfg)

    resp = await admin_client.put(
        "/api/v1/admin/llm-functions/digest",
        json={"primary_config_id": str(ollama_config.id), "fallback_config_id": str(fallback_cfg.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_config_id"] == str(ollama_config.id)
    assert data["fallback_config_id"] == str(fallback_cfg.id)


async def test_update_llm_function_rejects_inactive_config(admin_client, inactive_config):
    resp = await admin_client.put(
        "/api/v1/admin/llm-functions/tagging",
        json={"primary_config_id": str(inactive_config.id)},
    )
    assert resp.status_code == 422


async def test_update_llm_function_rejects_unknown_config_id(admin_client):
    import uuid
    resp = await admin_client.put(
        "/api/v1/admin/llm-functions/tagging",
        json={"primary_config_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


async def test_update_llm_function_rejects_invalid_function_name(admin_client):
    resp = await admin_client.put(
        "/api/v1/admin/llm-functions/not-a-real-function",
        json={"primary_config_id": None},
    )
    assert resp.status_code == 404


async def test_update_llm_function_requires_admin(user_client, ollama_config):
    resp = await user_client.put(
        "/api/v1/admin/llm-functions/tagging",
        json={"primary_config_id": str(ollama_config.id)},
    )
    assert resp.status_code == 403


async def test_update_llm_function_clears_assignment(admin_client, ollama_config):
    await admin_client.put(
        "/api/v1/admin/llm-functions/tagging",
        json={"primary_config_id": str(ollama_config.id)},
    )
    resp = await admin_client.put(
        "/api/v1/admin/llm-functions/tagging",
        json={"primary_config_id": None, "fallback_config_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["primary_config_id"] is None
