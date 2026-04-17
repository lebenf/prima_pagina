import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _feed_fetcher_job() -> None:
    from app.database import AsyncSessionLocal
    from app.services.feed_fetcher import fetch_all_due_feeds

    async with AsyncSessionLocal() as db:
        scheduled = await fetch_all_due_feeds(db)
        if scheduled:
            logger.info("scheduler: queued %d feed(s) for fetching", len(scheduled))


async def _cleanup_sessions_job() -> None:
    from app.database import AsyncSessionLocal
    from app.services.auth_service import cleanup_expired_sessions

    async with AsyncSessionLocal() as db:
        count = await cleanup_expired_sessions(db)
        logger.info("scheduler: cleaned up %d expired/revoked sessions", count)


def setup_scheduler() -> AsyncIOScheduler:
    """Register jobs and start the scheduler. Called from main.py lifespan."""
    scheduler.add_job(
        _feed_fetcher_job,
        trigger=IntervalTrigger(minutes=1),
        id="feed_fetcher",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        _cleanup_sessions_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="cleanup_sessions",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("scheduler: started (%d jobs registered)", len(scheduler.get_jobs()))
    return scheduler
