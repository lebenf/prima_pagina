# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Background regeneration of an event's LLM title/synopsis. Fire-and-forget:
failures are logged and leave the current title/synopsis untouched — no
exception ever propagates to the caller (the tagging worker)."""
import logging
from uuid import UUID

from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.event import Event, TitleSource
from app.models.llm_function_assignment import LLMFunction

logger = logging.getLogger(__name__)

MAX_MEMBERS_IN_PROMPT = 10


def _build_event_summary_prompt(event: Event, members: list) -> str:
    members = sorted(members, key=lambda a: a.published_at or a.fetched_at, reverse=True)
    members_text = "\n".join(
        f"- {m.title or '(senza titolo)'}: {(m.content_excerpt or '')[:300]}"
        for m in members[:MAX_MEMBERS_IN_PROMPT]
    )
    return (
        "Rispondi solo con JSON. Nessun testo aggiuntivo.\n\n"
        "Sei un redattore. Scrivi un titolo breve e una sintesi (2-3 frasi) per un evento "
        "coperto dai seguenti articoli, provenienti da fonti diverse. Il titolo e la sintesi "
        "devono descrivere il fatto in modo neutro, senza attribuirlo a una singola fonte.\n\n"
        f"Tag dell'evento: {', '.join(event.tags or [])}\n\n"
        f"Articoli:\n{members_text}\n\n"
        'Rispondi in JSON: {"title": "...", "synopsis": "..."}'
    )


async def regenerate_event_summary(event_id: UUID) -> None:
    from app.services.llm.router import llm_router

    try:
        async with AsyncSessionLocal() as db:
            from app.config import get_settings

            event = await db.get(Event, event_id, options=[selectinload(Event.articles)])
            if not event:
                return

            provider = await llm_router.get_provider_for(
                LLMFunction.EVENT_SUMMARY, db, encryption_key=get_settings().encryption_key
            )
            if not provider:
                return

            from app.services.llm.base import LLMProvider

            prompt = _build_event_summary_prompt(event, event.articles)
            raw = await provider.generate_text(prompt, max_tokens=600, json_mode=True)
            data = LLMProvider._parse_json_object(raw)
            if data is None:
                raise ValueError(f"unparseable JSON response: {raw[:300]!r}")
            title = data.get("title")
            synopsis = data.get("synopsis")
            if not title or not synopsis:
                raise ValueError("missing title/synopsis in LLM response")

            event.title = title
            event.synopsis = synopsis
            event.title_source = TitleSource.LLM.value
            await db.commit()
    except Exception as exc:
        logger.warning("event_summary: regeneration failed for event %s: %s", event_id, exc)
