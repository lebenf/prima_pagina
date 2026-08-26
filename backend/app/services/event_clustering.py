# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Event clustering: attaches a newly-tagged article to an existing open event
(same specific real-world occurrence) or creates a new one.

Precision over recall: a wrong merge (two distinct facts under one event) is a
visible editorial error, worse than an extra event (a false negative). When in
doubt, create a new event.
"""
import json
import logging
import math
from collections import Counter
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.article import Article
from app.models.event import Event, EventStatus, TitleSource

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 10
REGEN_EVERY_N_ARTICLES = 3

# An event's tags are derived from its members, not accumulated forever: a tag
# survives only if it covers this share of member articles, capped in size.
# Without this, an event's tag-set is a monotonic union that never shrinks —
# as it absorbs diverse articles it becomes an ever-more-generic superset,
# attracting more unrelated articles (self-reinforcing merge).
EVENT_TAG_MIN_SHARE = 0.3
MAX_EVENT_TAGS = 12

# Above this size, an event needs a strong tag-overlap ratio to keep absorbing
# articles — stops a grab-bag event from growing via marginal/generic signals.
EVENT_LARGE_SIZE_THRESHOLD = 8
LARGE_EVENT_MIN_OVERLAP_RATIO = 0.5


async def find_candidate_events(
    db: AsyncSession, article: Article, category_id: UUID | None
) -> list[Event]:
    """Open events in the clustering window, same category. Below
    EVENT_LARGE_SIZE_THRESHOLD, any same-category event in the window is a
    candidate regardless of tag overlap (the LLM match step, already biased
    towards "null" on doubt, is the real filter) — this is what lets two
    differently-tagged articles about the same real story still get merged.
    At/above the threshold, an event needs a strong overlap ratio against its
    own (already share-pruned) tags to remain eligible, so a grab-bag event
    can't keep absorbing unrelated articles on weak/generic signals.
    """
    cutoff = datetime.utcnow() - timedelta(hours=get_settings().event_clustering_window_hours)

    stmt = (
        select(Event)
        .where(Event.status == EventStatus.OPEN.value)
        .where(Event.last_activity_at >= cutoff)
        .where(Event.category_id == category_id)
        .order_by(Event.last_activity_at.desc())
    )
    events = (await db.execute(stmt)).scalars().all()

    article_tags = set(article.tags or [])
    if not article_tags:
        return []

    scored = []
    for event in events:
        overlap = len(article_tags & set(event.tags or []))
        if event.article_count >= EVENT_LARGE_SIZE_THRESHOLD:
            if overlap / len(article_tags) < LARGE_EVENT_MIN_OVERLAP_RATIO:
                continue
        scored.append((event, overlap))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [event for event, _ in scored[:MAX_CANDIDATES]]


def _derive_event_tags(tag_counts: Counter, article_count: int) -> list[str]:
    """Tags that cover at least EVENT_TAG_MIN_SHARE of member articles,
    capped to MAX_EVENT_TAGS, most-common first."""
    threshold = max(1, math.ceil(article_count * EVENT_TAG_MIN_SHARE))
    kept = sorted(
        ((tag, count) for tag, count in tag_counts.items() if count >= threshold),
        key=lambda pair: (-pair[1], pair[0]),
    )
    return [tag for tag, _ in kept[:MAX_EVENT_TAGS]]


async def _recompute_event_tags(db: AsyncSession, event_id: UUID, article_count: int) -> list[str]:
    result = await db.execute(select(Article.tags).where(Article.event_id == event_id))
    counts: Counter = Counter()
    for (tags,) in result:
        counts.update(tags or [])
    return _derive_event_tags(counts, article_count)


def _build_event_match_prompt(article: Article, candidates: list[Event]) -> str:
    candidates_text = "\n".join(
        f"[{i + 1}] {c.title} — tag: {', '.join(c.tags or [])}"
        f"{' — sintesi: ' + c.synopsis if c.synopsis else ''}"
        for i, c in enumerate(candidates)
    )
    return (
        "Rispondi solo con JSON. Nessun testo aggiuntivo.\n\n"
        "Sei un classificatore editoriale. Hai un nuovo articolo e una lista di eventi "
        "già aperti (titolo, tag, sintesi). Determina se l'articolo copre LO STESSO "
        "accadimento specifico di uno degli eventi elencati (stessa data, stesso "
        "luogo/soggetto, stesso fatto puntuale), NON semplicemente lo stesso tema generale.\n\n"
        "Esempio: un bombardamento a Kharkiv il 15 marzo e uno a Odessa il 16 marzo, anche "
        "se entrambi parte dello stesso conflitto, sono eventi DIVERSI. Due articoli sulla "
        "stessa conferenza stampa di un politico sono lo STESSO evento anche se scritti da "
        "fonti diverse con enfasi diversa.\n\n"
        f"Nuovo articolo:\nTitolo: {article.title or '(senza titolo)'}\n"
        f"Tag: {', '.join(article.tags or [])}\n"
        f"Estratto: {(article.content_excerpt or '')[:300]}\n\n"
        f"Eventi candidati:\n{candidates_text}\n\n"
        "Se nessun evento corrisponde con sicurezza, rispondi con event_index: null "
        "(creerà un nuovo evento). In caso di dubbio, preferisci null.\n\n"
        'Rispondi in JSON: {"event_index": <numero 1-based> | null}'
    )


async def _match_candidate_with_llm(provider, article: Article, candidates: list[Event]) -> Event | None:
    prompt = _build_event_match_prompt(article, candidates)
    try:
        raw = await provider.generate_text(prompt, max_tokens=50)
        data = json.loads(raw.strip())
        idx = data.get("event_index")
        if isinstance(idx, int) and 1 <= idx <= len(candidates):
            return candidates[idx - 1]
        return None
    except Exception as exc:
        logger.warning("event_clustering: LLM match selection failed: %s", exc)
        # Fail-safe: only auto-pick when exactly one unambiguous candidate exists
        return candidates[0] if len(candidates) == 1 else None


async def _recompute_source_count(db: AsyncSession, event_id: UUID) -> int:
    result = await db.execute(
        select(func.count(func.distinct(Article.feed_id))).where(Article.event_id == event_id)
    )
    return result.scalar_one() or 0


async def attach_or_create_event(
    db: AsyncSession, article: Article, provider
) -> tuple[Event, bool]:
    """Attach `article` to a matching open event, or create a new one.

    Returns (event, should_regenerate_summary). Runs inline (not backgrounded) —
    it needs the article's own tags and is cheap (a few queries + optionally one
    lightweight LLM call), so event membership stays immediately consistent.
    """
    category_id = article.feed.category_id if article.feed else None
    candidates = await find_candidate_events(db, article, category_id)

    matched_event: Event | None = None
    if candidates and provider:
        matched_event = await _match_candidate_with_llm(provider, article, candidates)

    if matched_event is not None:
        event = matched_event
        existing_from_feed = await db.execute(
            select(func.count()).where(
                Article.event_id == event.id, Article.feed_id == article.feed_id
            )
        )
        is_new_source = existing_from_feed.scalar_one() == 0

        article.event_id = event.id
        article.event_role = "member"
        event.article_count += 1
        if article.published_at and article.published_at > event.last_activity_at:
            event.last_activity_at = article.published_at
        else:
            event.last_activity_at = datetime.utcnow()

        await db.flush()
        event.source_count = await _recompute_source_count(db, event.id)
        event.tags = await _recompute_event_tags(db, event.id, event.article_count)

        should_regenerate = is_new_source or event.article_count % REGEN_EVERY_N_ARTICLES == 0
        return event, should_regenerate

    event = Event(
        title=article.title or "(senza titolo)",
        title_source=TitleSource.REPRESENTATIVE.value,
        synopsis=article.content_excerpt,
        tags=article.tags or [],
        category_id=category_id,
        status=EventStatus.OPEN.value,
        article_count=1,
        source_count=1,
        opened_at=article.published_at or datetime.utcnow(),
        last_activity_at=article.published_at or datetime.utcnow(),
    )
    db.add(event)
    await db.flush()
    article.event_id = event.id
    article.event_role = "seed"
    return event, False


async def close_stale_events(db: AsyncSession) -> int:
    """Daily job: close open events with no activity within the clustering window."""
    cutoff = datetime.utcnow() - timedelta(hours=get_settings().event_clustering_window_hours)
    result = await db.execute(
        update(Event)
        .where(Event.status == EventStatus.OPEN.value)
        .where(Event.last_activity_at < cutoff)
        .values(status=EventStatus.CLOSED.value, closed_at=datetime.utcnow())
    )
    await db.commit()
    return result.rowcount
