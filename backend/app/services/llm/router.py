# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_config import LLMConfig
from app.models.llm_function_assignment import LLMFunction, LLMFunctionAssignment
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMRouter:
    """Selects the appropriate LLM provider for a given function, via the
    explicit per-function assignment table (primary + optional fallback)."""

    async def get_provider_for(
        self,
        function: LLMFunction | str,
        db: AsyncSession,
        encryption_key: str = "",
    ) -> LLMProvider | None:
        key = function.value if isinstance(function, LLMFunction) else function
        assignment = await db.get(LLMFunctionAssignment, key)
        if assignment is None:
            return None
        config = await self._resolve_config(assignment, db)
        if config is None:
            return None
        return self._build_provider(config, encryption_key)

    async def _resolve_config(
        self, assignment: LLMFunctionAssignment, db: AsyncSession
    ) -> LLMConfig | None:
        for config_id in (assignment.primary_config_id, assignment.fallback_config_id):
            if not config_id:
                continue
            config = await db.get(LLMConfig, config_id)
            if config and config.is_active:
                return config
        return None

    def _build_provider(self, config: LLMConfig, encryption_key: str = "") -> LLMProvider:
        if config.provider == "ollama":
            from app.services.llm.ollama import OllamaProvider
            return OllamaProvider(config)
        elif config.provider == "claude":
            from app.services.llm.claude import ClaudeProvider
            return ClaudeProvider(config, encryption_key=encryption_key)
        elif config.provider == "mistral":
            from app.services.llm.mistral import MistralProvider
            return MistralProvider(config, encryption_key=encryption_key)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")


llm_router = LLMRouter()
