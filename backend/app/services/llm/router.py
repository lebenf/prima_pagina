import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_config import LLMConfig
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMRouter:
    """Selects the appropriate LLM provider based on DB configuration."""

    async def get_provider_for(
        self,
        use_case: Literal["tagging", "digest"],
        db: AsyncSession,
        encryption_key: str = "",
    ) -> LLMProvider | None:
        result = await db.execute(
            select(LLMConfig)
            .where(LLMConfig.is_active == True)  # noqa: E712
            .order_by(LLMConfig.is_default.desc(), LLMConfig.priority.desc())
        )
        configs = result.scalars().all()

        matching = [c for c in configs if use_case in (c.use_for or [])]
        if not matching:
            return None

        # Prefer is_default=True, then first in priority order
        chosen = next((c for c in matching if c.is_default), matching[0])
        return self._build_provider(chosen, encryption_key)

    def _build_provider(self, config: LLMConfig, encryption_key: str = "") -> LLMProvider:
        if config.provider == "ollama":
            from app.services.llm.ollama import OllamaProvider
            return OllamaProvider(config)
        elif config.provider == "claude":
            from app.services.llm.claude import ClaudeProvider
            return ClaudeProvider(config, encryption_key=encryption_key)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")


llm_router = LLMRouter()
