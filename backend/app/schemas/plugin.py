import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PluginConfigCreate(BaseModel):
    plugin_type: str
    label: str | None = None
    config_json: dict
    user_id: uuid.UUID | None = None
    is_active: bool = True

    @field_validator("config_json")
    @classmethod
    def validate_plugin_config(cls, v: dict, info) -> dict:
        from app.plugins.manager import PLUGIN_REGISTRY
        plugin_type = info.data.get("plugin_type")
        plugin_class = PLUGIN_REGISTRY.get(plugin_type)
        if not plugin_class:
            raise ValueError(f"Plugin type non supportato: {plugin_type}")
        errors = plugin_class.validate_config(v)
        if errors:
            raise ValueError(f"Config non valido: {'; '.join(errors)}")
        return v


class PluginConfigUpdate(BaseModel):
    label: str | None = None
    config_json: dict | None = None
    is_active: bool | None = None


class PluginConfigResponse(BaseModel):
    id: uuid.UUID
    plugin_type: str
    label: str | None
    user_id: uuid.UUID | None
    is_active: bool
    has_config: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PluginAvailable(BaseModel):
    plugin_type: str
    label: str
    description: str
    config_schema: dict


class PluginTestResponse(BaseModel):
    ok: bool
    message: str
    latency_ms: int
