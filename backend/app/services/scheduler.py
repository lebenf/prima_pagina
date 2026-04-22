import asyncio
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


async def _digest_generation_job() -> None:
    from datetime import datetime, timedelta

    from sqlalchemy import select

    # Lazy imports keep startup fast; also allows patching in tests
    from app.database import AsyncSessionLocal
    from app.models.user import User
    from app.schemas.digest import DigestGenerateOptions
    from app.services.digest_service import DigestError, generate_digest, get_recent_digest

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.is_active == True))  # noqa: E712
        users = result.scalars().all()

        for user in users:
            try:
                recent = await get_recent_digest(db, user.id, hours=20)
                if recent:
                    logger.debug("skipping digest for %s: recent digest exists", user.username)
                    continue

                now = datetime.utcnow()
                options = DigestGenerateOptions(
                    period_start=now - timedelta(hours=24),
                    period_end=now,
                    max_articles=30,
                    force_fulltext=True,
                )
                await generate_digest(db, user, options)
                logger.info("scheduled digest generated for %s", user.username)
                await asyncio.sleep(2)

            except DigestError as e:
                logger.info("digest skipped for %s: %s — %s", user.username, e.code, e.message)
            except Exception as e:
                logger.error("digest generation failed for %s: %s", user.username, e, exc_info=True)


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

    from app.config import get_settings
    settings = get_settings()
    scheduler.add_job(
        _digest_generation_job,
        trigger=CronTrigger.from_crontab(settings.digest_cron),
        id="digest_generation",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("scheduler: started (%d jobs registered)", len(scheduler.get_jobs()))
    return scheduler
