"""Auto-scrape scheduler.

- daily Zauba+DataGov at 2 PM IST (existing)
- StartupIndia rolling scraper, ~50 startups per tick, every 3 min during
  backfill, every 60 min after we've walked the full list.
"""
import uuid
from datetime import date, datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
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


async def daily_datagov_seed_task():
    """Triggered daily at 3 PM IST. Fetches 50 companies from DataGov."""
    from app.database import AsyncSessionLocal
    from app.models.company import MatchedCompany
    from app.services.datagov_scraper import DataGovScraper
    
    log.info("datagov_seed_starting")
    try:
        scraper = DataGovScraper()
        new_companies = []
        async with AsyncSessionLocal() as db:
            async for c_data in scraper.scrape_companies(limit_per_page=50):
                cin = c_data.get("cin")
                if cin:
                    from sqlalchemy import select
                    existing = (await db.execute(select(MatchedCompany).where(MatchedCompany.cin == cin))).scalar_one_or_none()
                    if not existing:
                        mc = MatchedCompany(
                            company_name=c_data.get("company_name"),
                            cin=cin,
                            match_score=1.0,
                            match_method="auto_seed",
                            company_status=c_data.get("company_status"),
                            roc_code=c_data.get("roc_code"),
                            company_category=c_data.get("company_category"),
                            date_of_incorporation=c_data.get("date_of_incorporation"),
                            state=c_data.get("state"),
                            authorised_capital=c_data.get("authorised_capital"),
                            paid_up_capital=c_data.get("paid_up_capital"),
                            is_startup=False,
                            incorporation_year=c_data.get("date_of_incorporation").year if c_data.get("date_of_incorporation") else None,
                        )
                        db.add(mc)
                        new_companies.append(mc)
            
            if new_companies:
                await db.commit()
                log.info("datagov_seed_completed", count=len(new_companies))
            else:
                log.info("datagov_seed_no_new_records")
    except Exception as e:
        log.error("datagov_seed_failed", error=str(e))

STARTUPINDIA_SOURCE = "startupindia"
STARTUPINDIA_PAGE_SIZE = 50
STARTUPINDIA_BACKFILL_INTERVAL_S = 180   # 3 minutes during backfill
STARTUPINDIA_STEADY_INTERVAL_S = 3600    # 60 minutes after backfill complete

# Contact enricher: walk un-enriched startups in the background so user
# clicks land on fully-populated rows.
ENRICH_BATCH_SIZE = 4
ENRICH_INTERVAL_S = 90      # one batch every 90 seconds — polite + steady

_startupindia_running = False
_enrich_running = False


async def enrich_tick():
    """Pick the next batch of un-enriched startups and run scraper-2 on each."""
    global _enrich_running
    if _enrich_running:
        return
    _enrich_running = True
    try:
        from sqlalchemy import select, text, or_, and_
        from datetime import datetime
        from app.database import AsyncSessionLocal
        from app.models.startup import StartupIndiaCompany
        from app.services.contact_enricher import enrich_contact

        async with AsyncSessionLocal() as db:
            # Postgres advisory lock so we don't double-run with multiple workers
            ENRICH_LOCK_KEY = 909_002
            got_lock = (await db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": ENRICH_LOCK_KEY})).scalar()
            if not got_lock:
                return

            try:
                # Pick rows that have never been enriched, oldest scraped first.
                rows = (await db.execute(
                    select(StartupIndiaCompany)
                    .where(StartupIndiaCompany.contact_enriched_at.is_(None))
                    .order_by(StartupIndiaCompany.scraped_at.asc())
                    .limit(ENRICH_BATCH_SIZE)
                )).scalars().all()
                if not rows:
                    log.info("enrich_tick.idle")
                    return

                for row in rows:
                    try:
                        info = await enrich_contact(row.company_name)
                    except Exception as e:
                        log.warning("enrich_tick.row_failed", cin=row.profile_id, error=str(e))
                        # Mark enriched_at anyway so we don't loop forever on a bad name
                        row.contact_enriched_at = datetime.utcnow()
                        continue

                    if info.get("email"): row.contact_email = info["email"]
                    if info.get("phone"): row.contact_phone = info["phone"]
                    if info.get("address"): row.contact_address = info["address"]
                    if info.get("linkedin"): row.linkedin_url = info["linkedin"]
                    if info.get("twitter"): row.twitter_url = info["twitter"]
                    if info.get("facebook"): row.facebook_url = info["facebook"]
                    if info.get("cin"): row.cin_real = info["cin"]
                    if info.get("gst"): row.gst = info["gst"]
                    if info.get("extras"):
                        merged_extras = dict(row.extras or {})
                        merged_extras.update({k: v for k, v in info["extras"].items() if v})
                        if merged_extras: row.extras = merged_extras
                    if info.get("source"):
                        row.source_url = info["source"]
                        row.website = (
                            info["source"].split("/contact")[0].rstrip("/") + "/"
                            if "/contact" in info["source"] else info["source"]
                        )
                    row.contact_enriched_at = datetime.utcnow()

                await db.commit()
                log.info("enrich_tick.done", processed=len(rows))
            finally:
                await db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": ENRICH_LOCK_KEY})
                await db.commit()
    finally:
        _enrich_running = False


async def startupindia_tick():
    """One scrape cycle: pull the next 50 startups, persist, advance cursor."""
    global _startupindia_running
    if _startupindia_running:
        log.info("startupindia.skip_overlap")
        return
    _startupindia_running = True
    try:
        from sqlalchemy import select, text
        from app.database import AsyncSessionLocal
        from app.models.startup import StartupIndiaCompany, ScrapeCursor
        from app.models.company import MatchedCompany
        from app.services.startupindia_scraper import StartupIndiaScraper

        async with AsyncSessionLocal() as db:
            # Postgres advisory lock — only one worker can hold this concurrently,
            # so multi-worker uvicorn doesn't double-tick the scraper.
            STARTUPINDIA_LOCK_KEY = 909_001
            got_lock = (await db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": STARTUPINDIA_LOCK_KEY})).scalar()
            if not got_lock:
                log.info("startupindia.skip_locked")
                return

            cursor = (
                await db.execute(select(ScrapeCursor).where(ScrapeCursor.source == STARTUPINDIA_SOURCE))
            ).scalar_one_or_none()
            if cursor is None:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                await db.execute(
                    pg_insert(ScrapeCursor)
                    .values(source=STARTUPINDIA_SOURCE, page=0, exhausted=False, last_count=0)
                    .on_conflict_do_nothing(index_elements=["source"])
                )
                await db.flush()
                cursor = (
                    await db.execute(select(ScrapeCursor).where(ScrapeCursor.source == STARTUPINDIA_SOURCE))
                ).scalar_one()

            # In steady-state we re-scan page 0 to pick up newly added startups
            target_page = 0 if cursor.exhausted else cursor.page
            log.info("startupindia.tick_start", page=target_page, exhausted=cursor.exhausted)

            scraper = StartupIndiaScraper(page_size=STARTUPINDIA_PAGE_SIZE)
            try:
                items = await scraper.scrape_page(target_page)
            except Exception as e:
                log.error("startupindia.scrape_failed", page=target_page, error=str(e))
                cursor.last_run_at = datetime.utcnow()
                cursor.notes = f"error: {str(e)[:400]}"
                await db.commit()
                return

            from app.services.startup_persist import upsert_startups
            new_count = await upsert_startups(db, items)

            # Advance cursor
            if not items:
                # No results at this page — backfill is complete
                cursor.exhausted = True
                cursor.notes = "backfill_complete"
            elif not cursor.exhausted:
                cursor.page = target_page + 1
            cursor.last_run_at = datetime.utcnow()
            cursor.last_count = len(items)
            cursor.notes = None
            await db.commit()
            log.info(
                "startupindia.tick_done",
                page=target_page,
                fetched=len(items),
                new=new_count,
                exhausted=cursor.exhausted,
            )

            # If we just finished backfill, reschedule to steady-state cadence
            if cursor.exhausted:
                _reschedule_startupindia(steady=True)
    finally:
        _startupindia_running = False


def _reschedule_startupindia(steady: bool):
    """Swap the interval between backfill (3 min) and steady-state (60 min)."""
    global scheduler
    if not scheduler:
        return
    interval = STARTUPINDIA_STEADY_INTERVAL_S if steady else STARTUPINDIA_BACKFILL_INTERVAL_S
    scheduler.reschedule_job(
        job_id="startupindia_tick",
        trigger=IntervalTrigger(seconds=interval),
    )
    log.info("startupindia.rescheduled", interval_s=interval, steady=steady)


def start_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        return

    ist = pytz.timezone("Asia/Kolkata")
    scheduler = AsyncIOScheduler(timezone=ist)
    scheduler.add_job(
        daily_scrape_task,
        CronTrigger(hour=14, minute=0, timezone=ist),
        id="daily_scrape",
        replace_existing=True,
    )
    scheduler.add_job(
        daily_datagov_seed_task,
        CronTrigger(hour=14, minute=0, timezone=ist),
        id="daily_scrape_2pm_ist",
        name="Daily Zauba+DataGov scrape at 2:00 PM IST",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        startupindia_tick,
        IntervalTrigger(seconds=STARTUPINDIA_BACKFILL_INTERVAL_S),
        id="startupindia_tick",
        name=f"StartupIndia rolling scrape (every {STARTUPINDIA_BACKFILL_INTERVAL_S}s in backfill)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
        next_run_time=datetime.utcnow() + timedelta(seconds=15),
    )
    scheduler.add_job(
        enrich_tick,
        IntervalTrigger(seconds=ENRICH_INTERVAL_S),
        id="enrich_tick",
        name=f"Contact enrichment sweep (every {ENRICH_INTERVAL_S}s, {ENRICH_BATCH_SIZE} per batch)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
        next_run_time=datetime.utcnow() + timedelta(seconds=30),
    )
    scheduler.start()
    log.info("scheduler_started", next_run=str(scheduler.get_job("daily_scrape_2pm_ist").next_run_time))


def stop_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
