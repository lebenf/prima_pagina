# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/event_summary_service.py — same fragile-JSON-parsing
bug class as event_clustering.py (tiny max_tokens + bare json.loads), same
provider assignment (EVENT_SUMMARY), fixed the same way."""
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.article import Article
from app.models.event import Event, EventStatus, TitleSource
from app.models.feed import Feed
from app.services.event_summary_service import regenerate_event_summary


@pytest.fixture
async def feed(db_session):
    f = Feed(url="https://event-summary-feed.example.com/rss.xml", title="Feed")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def event_with_members(db_session, feed):
    event = Event(
        title="Old title",
        title_source=TitleSource.REPRESENTATIVE.value,
        synopsis="Old synopsis",
        tags=["ai"],
        status=EventStatus.OPEN.value,
        article_count=1,
        source_count=1,
        opened_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
    )
    db_session.add(event)
    await db_session.flush()

    article = Article(
        feed_id=feed.id,
        guid=str(uuid4()),
        title="Member article",
        tags=["ai"],
        tags_source="llm",
        published_at=datetime.utcnow(),
        event_id=event.id,
    )
    db_session.add(article)
    await db_session.commit()
    # Force-load the relationship: regenerate_event_summary reuses this same
    # session (identity-mapped), so a plain db.get() won't trigger the
    # selectinload for an already-present object — pre-populate it here to
    # avoid a lazy-load outside the async greenlet context.
    await db_session.refresh(event, attribute_names=["articles"])
    return event


def _mock_provider(raw_response: str) -> AsyncMock:
    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value=raw_response)
    return mock_provider


async def _run_regenerate(db_session, monkeypatch, mock_provider, event_id) -> None:
    from app.services.llm.router import llm_router

    monkeypatch.setattr(llm_router, "get_provider_for", AsyncMock(return_value=mock_provider))
    with patch("app.services.event_summary_service.AsyncSessionLocal") as mock_session_factory:
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await regenerate_event_summary(event_id)


async def test_regenerate_updates_title_and_synopsis(monkeypatch, event_with_members, db_session):
    mock_provider = _mock_provider('{"title": "New title", "synopsis": "New synopsis"}')

    await _run_regenerate(db_session, monkeypatch, mock_provider, event_with_members.id)

    await db_session.refresh(event_with_members)
    assert event_with_members.title == "New title"
    assert event_with_members.synopsis == "New synopsis"
    assert event_with_members.title_source == TitleSource.LLM.value

    call_kwargs = mock_provider.generate_text.call_args.kwargs
    assert call_kwargs["max_tokens"] == 600
    assert call_kwargs["json_mode"] is True


async def test_regenerate_tolerates_fenced_json(monkeypatch, event_with_members, db_session):
    mock_provider = _mock_provider(
        '```json\n{"title": "Fenced title", "synopsis": "Fenced synopsis"}\n```'
    )

    await _run_regenerate(db_session, monkeypatch, mock_provider, event_with_members.id)

    await db_session.refresh(event_with_members)
    assert event_with_members.title == "Fenced title"
    assert event_with_members.synopsis == "Fenced synopsis"


async def test_regenerate_leaves_event_untouched_on_unparseable_response(
    monkeypatch, event_with_members, db_session
):
    mock_provider = _mock_provider("not valid json")

    await _run_regenerate(db_session, monkeypatch, mock_provider, event_with_members.id)

    await db_session.refresh(event_with_members)
    assert event_with_members.title == "Old title"
    assert event_with_members.synopsis == "Old synopsis"
    assert event_with_members.title_source == TitleSource.REPRESENTATIVE.value
