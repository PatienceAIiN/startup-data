"""Daily auto-scrape scheduler — runs at 2:00 PM IST every day."""
import uuid
from datetime import date, datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import structlog

log = structlog.get_logger()

scheduler: AsyncIOScheduler | None = None


async def daily_scrape_task():
    """Triggered daily at 2 PM IST. Runs full scrape for last 365 days."""
    from app.database import AsyncSessionLocal
    from app.models.scrape_job import ScrapeJob
    from app.models.user import User
    from sqlalchemy import select
    from app.routers.scraper import run_full_scrape

    log.info("daily_scrape_starting")
    async with AsyncSessionLocal() as db:
        admin_result = await db.execute(
            select(User).where(User.is_admin == True).limit(1)
        )
        admin = admin_result.scalar_one_or_none()
        if not admin:
            log.warning("daily_scrape_no_admin")
            return

        date_from = date.today() - timedelta(days=365)
        date_to = date.today()

        job = ScrapeJob(
            triggered_by=admin.id,
            source="both",
            status="pending",
        )
        db.add(job)
        await db.flush()
        await db.commit()
        job_id = str(job.id)

    try:
        await run_full_scrape(job_id, date_from, date_to)
        log.info("daily_scrape_completed", job_id=job_id)
    except Exception as e:
        log.error("daily_scrape_failed", error=str(e))


def start_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        return

    ist = pytz.timezone("Asia/Kolkata")
    scheduler = AsyncIOScheduler(timezone=ist)
    scheduler.add_job(
        daily_scrape_task,
        CronTrigger(hour=14, minute=0, timezone=ist),
        id="daily_scrape_2pm_ist",
        name="Daily Zauba+DataGov scrape at 2:00 PM IST",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    log.info("scheduler_started", next_run=str(scheduler.get_job("daily_scrape_2pm_ist").next_run_time))


def stop_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
