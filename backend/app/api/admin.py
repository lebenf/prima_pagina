# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.config import get_settings
from app.models.llm_config import LLMConfig
from app.models.plugin_config import PluginConfig
from app.models.user import User
from app.plugins.manager import PLUGIN_DESCRIPTIONS, PLUGIN_LABELS, PLUGIN_REGISTRY
from app.schemas.llm import (
    HealthCheckResponse,
    LLMConfigCreate,
    LLMConfigResponse,
    LLMConfigUpdate,
)
from app.schemas.plugin import (
    PluginAvailable,
    PluginConfigCreate,
    PluginConfigResponse,
    PluginConfigUpdate,
    PluginTestResponse,
)
from app.services.llm.router import llm_router

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def _to_response(config: LLMConfig) -> LLMConfigResponse:
    return LLMConfigResponse(
        id=config.id,
        provider=config.provider,
        label=config.label,
        model_name=config.model_name,
        endpoint_url=config.endpoint_url,
        has_api_key=config.api_key_encrypted is not None,
        use_for=config.use_for or [],
        is_default=config.is_default,
        is_active=config.is_active,
        priority=config.priority,
        created_at=config.created_at,
    )


@router.get("/llm-configs", response_model=list[LLMConfigResponse])
async def list_llm_configs(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(
        select(LLMConfig).order_by(LLMConfig.priority.desc(), LLMConfig.created_at)
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.post("/llm-configs", response_model=LLMConfigResponse, status_code=201)
async def create_llm_config(
    body: LLMConfigCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    settings = get_settings()

    if body.is_default:
        await _clear_defaults(db, body.use_for)

    config = LLMConfig(
        provider=body.provider,
        label=body.label,
        model_name=body.model_name,
        endpoint_url=body.endpoint_url,
        use_for=body.use_for,
        is_default=body.is_default,
        is_active=body.is_active,
        priority=body.priority,
    )
    if body.api_key:
        config.set_api_key(body.api_key, settings.encryption_key)

    db.add(config)
    await db.commit()
    await db.refresh(config)
    return _to_response(config)


@router.put("/llm-configs/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: UUID,
    body: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    config = await db.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")

    settings = get_settings()

    if body.is_default is True:
        use_for = body.use_for if body.use_for is not None else config.use_for
        await _clear_defaults(db, use_for, exclude_id=config_id)

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "api_key":
            if value:
                config.set_api_key(value, settings.encryption_key)
        else:
            setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return _to_response(config)


@router.delete("/llm-configs/{config_id}", status_code=204)
async def delete_llm_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    config = await db.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    await db.delete(config)
    await db.commit()


@router.post("/llm-configs/{config_id}/health-check", response_model=HealthCheckResponse)
async def health_check_llm_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    config = await db.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")

    settings = get_settings()
    provider = llm_router._build_provider(config, settings.encryption_key)

    start = time.monotonic()
    try:
        ok = await provider.health_check()
        latency_ms = int((time.monotonic() - start) * 1000)
        return HealthCheckResponse(ok=ok, latency_ms=latency_ms)
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return HealthCheckResponse(ok=False, latency_ms=latency_ms, error=str(exc))


# ---------------------------------------------------------------------------
# Plugin config endpoints
# ---------------------------------------------------------------------------

def _plugin_to_response(cfg: PluginConfig) -> PluginConfigResponse:
    return PluginConfigResponse(
        id=cfg.id,
        plugin_type=cfg.plugin_type,
        label=cfg.label,
        user_id=cfg.user_id,
        is_active=cfg.is_active,
        has_config=bool(cfg.config_json_encrypted),
        created_at=cfg.created_at,
    )


# /available must be before /{plugin_id} to avoid routing conflict
@router.get("/plugins/available", response_model=list[PluginAvailable])
async def list_available_plugins(
    _admin: User = Depends(require_admin),
):
    return [
        PluginAvailable(
            plugin_type=pt,
            label=PLUGIN_LABELS.get(pt, pt),
            description=PLUGIN_DESCRIPTIONS.get(pt, ""),
            config_schema=cls.config_schema,
        )
        for pt, cls in PLUGIN_REGISTRY.items()
    ]


@router.get("/plugins", response_model=list[PluginConfigResponse])
async def list_plugins(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(select(PluginConfig).order_by(PluginConfig.created_at))
    return [_plugin_to_response(c) for c in result.scalars().all()]


@router.post("/plugins", response_model=PluginConfigResponse, status_code=201)
async def create_plugin(
    body: PluginConfigCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    cfg = PluginConfig(
        plugin_type=body.plugin_type,
        label=body.label,
        user_id=body.user_id,
        is_active=body.is_active,
        config_json_encrypted="",  # placeholder, overwritten below
    )
    cfg.set_config(body.config_json)
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return _plugin_to_response(cfg)


@router.put("/plugins/{plugin_id}", response_model=PluginConfigResponse)
async def update_plugin(
    plugin_id: UUID,
    body: PluginConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    cfg = await db.get(PluginConfig, plugin_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Plugin config not found")

    if body.label is not None:
        cfg.label = body.label
    if body.is_active is not None:
        cfg.is_active = body.is_active
    if body.config_json is not None:
        # Validate before saving
        plugin_class = PLUGIN_REGISTRY.get(cfg.plugin_type)
        if plugin_class:
            errors = plugin_class.validate_config(body.config_json)
            if errors:
                raise HTTPException(status_code=422, detail=f"Config non valido: {'; '.join(errors)}")
        cfg.set_config(body.config_json)

    await db.commit()
    await db.refresh(cfg)
    return _plugin_to_response(cfg)


@router.delete("/plugins/{plugin_id}", status_code=204)
async def delete_plugin(
    plugin_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    cfg = await db.get(PluginConfig, plugin_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Plugin config not found")
    await db.delete(cfg)
    await db.commit()


@router.post("/plugins/{plugin_id}/test", response_model=PluginTestResponse)
async def test_plugin(
    plugin_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    cfg = await db.get(PluginConfig, plugin_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Plugin config not found")

    plugin_class = PLUGIN_REGISTRY.get(cfg.plugin_type)
    if not plugin_class:
        raise HTTPException(status_code=400, detail=f"Plugin type not supported: {cfg.plugin_type}")

    plugin = plugin_class(cfg)
    start = time.monotonic()
    ok, message = await plugin.test_connection()
    latency_ms = int((time.monotonic() - start) * 1000)
    return PluginTestResponse(ok=ok, message=message, latency_ms=latency_ms)


# ---------------------------------------------------------------------------

async def _clear_defaults(db, use_for: list[str], exclude_id: UUID | None = None) -> None:
    result = await db.execute(
        select(LLMConfig).where(LLMConfig.is_default == True)  # noqa: E712
    )
    for cfg in result.scalars().all():
        if exclude_id and cfg.id == exclude_id:
            continue
        if any(u in (cfg.use_for or []) for u in use_for):
            cfg.is_default = False
    await db.flush()
