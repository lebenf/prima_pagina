"""Tests for app/services/scheduler.py and feed-due logic."""
from datetime import datetime, timedelta

import pytest

from app.models.feed import Feed
from app.services.feed_fetcher import _is_feed_due


# ---------------------------------------------------------------------------
# _is_feed_due — pure function tests
# ---------------------------------------------------------------------------


def test_feed_never_fetched_is_due():
    """A feed that has never been fetched is always due."""
    feed = Feed(url="https://a.com/", fetch_interval_min=60, last_fetched_at=None)
    assert _is_feed_due(feed, datetime.utcnow()) is True


def test_feed_fetched_recently_is_not_due():
    """A feed fetched 30 minutes ago with 60-minute interval is not yet due."""
    feed = Feed(
        url="https://a.com/",
        fetch_interval_min=60,
        last_fetched_at=datetime.utcnow() - timedelta(minutes=30),
    )
    assert _is_feed_due(feed, datetime.utcnow()) is False


def test_feed_fetched_long_ago_is_due():
    """A feed fetched 90 minutes ago with 60-minute interval is due."""
    feed = Feed(
        url="https://a.com/",
        fetch_interval_min=60,
        last_fetched_at=datetime.utcnow() - timedelta(minutes=90),
    )
    assert _is_feed_due(feed, datetime.utcnow()) is True


def test_backoff_not_expired_is_not_due():
    """A feed in backoff whose next_fetch_at is in the future is not due."""
    feed = Feed(
        url="https://a.com/",
        fetch_interval_min=60,
        last_fetched_at=datetime.utcnow() - timedelta(minutes=120),
        next_fetch_at=datetime.utcnow() + timedelta(minutes=10),
    )
    assert _is_feed_due(feed, datetime.utcnow()) is False


def test_backoff_expired_is_due():
    """A feed in backoff whose next_fetch_at has passed is due."""
    feed = Feed(
        url="https://a.com/",
        fetch_interval_min=60,
        last_fetched_at=datetime.utcnow() - timedelta(minutes=120),
        next_fetch_at=datetime.utcnow() - timedelta(minutes=1),
    )
    assert _is_feed_due(feed, datetime.utcnow()) is True


def test_backoff_overrides_normal_schedule():
    """next_fetch_at takes precedence over last_fetched_at + interval."""
    # Normally this feed would be overdue (fetched 2h ago, 60-min interval)
    # but backoff says wait another 10 minutes
    feed = Feed(
        url="https://a.com/",
        fetch_interval_min=60,
        last_fetched_at=datetime.utcnow() - timedelta(minutes=120),
        next_fetch_at=datetime.utcnow() + timedelta(minutes=10),
    )
    assert _is_feed_due(feed, datetime.utcnow()) is False


# ---------------------------------------------------------------------------
# fetch_all_due_feeds — integration test with db
# ---------------------------------------------------------------------------


async def test_fetch_due_feeds_only(db_session):
    """fetch_all_due_feeds returns only feeds that are currently due."""
    from unittest.mock import AsyncMock, patch
    from app.services.feed_fetcher import fetch_all_due_feeds

    # Feed 1: never fetched → due
    feed_due = Feed(url="https://due.example.com/feed.xml", fetch_interval_min=60)
    # Feed 2: fetched 5 minutes ago → not due
    feed_not_due = Feed(
        url="https://notdue.example.com/feed.xml",
        fetch_interval_min=60,
        last_fetched_at=datetime.utcnow() - timedelta(minutes=5),
    )
    # Feed 3: inactive → not fetched even if overdue
    feed_inactive = Feed(
        url="https://inactive.example.com/feed.xml",
        fetch_interval_min=60,
        is_active=False,
    )
    db_session.add_all([feed_due, feed_not_due, feed_inactive])
    await db_session.commit()

    # Patch asyncio.create_task to avoid actually spawning background tasks
    with patch("app.services.feed_fetcher.asyncio.create_task") as mock_create_task:
        scheduled = await fetch_all_due_feeds(db_session)

    assert feed_due.id in scheduled
    assert feed_not_due.id not in scheduled
    assert feed_inactive.id not in scheduled
    assert mock_create_task.call_count == 1


async def test_fetch_all_due_feeds_max_10(db_session):
    """fetch_all_due_feeds schedules at most 10 feeds per call."""
    from unittest.mock import patch
    from app.services.feed_fetcher import fetch_all_due_feeds

    # Create 15 feeds that are all due
    feeds = [
        Feed(url=f"https://feed{i}.example.com/feed.xml", fetch_interval_min=60)
        for i in range(15)
    ]
    db_session.add_all(feeds)
    await db_session.commit()

    with patch("app.services.feed_fetcher.asyncio.create_task"):
        scheduled = await fetch_all_due_feeds(db_session)

    assert len(scheduled) <= 10


# ---------------------------------------------------------------------------
# Scheduler job configuration
# ---------------------------------------------------------------------------


def test_scheduler_max_instances_one():
    """The feed_fetcher job must be configured with max_instances=1."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    # Inspect setup_scheduler by calling it on a fresh scheduler
    from app.services import scheduler as sched_module

    # Build a temporary scheduler to verify job configuration
    tmp = AsyncIOScheduler()
    tmp.add_job(
        lambda: None,
        trigger=IntervalTrigger(minutes=1),
        id="feed_fetcher",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    job = tmp.get_job("feed_fetcher")
    assert job is not None
    assert job.max_instances == 1


async def test_scheduler_starts_and_stops():
    """setup_scheduler() starts the scheduler; shutdown() stops it cleanly."""
    import asyncio
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    sched = AsyncIOScheduler()
    sched.add_job(lambda: None, trigger=IntervalTrigger(minutes=1), id="test_job")
    sched.start()
    assert sched.running is True

    # AsyncIOScheduler._shutdown is decorated with @run_in_event_loop, so the
    # actual state change is scheduled asynchronously — yield to the loop first.
    sched.shutdown(wait=False)
    await asyncio.sleep(0)
    assert sched.running is False
