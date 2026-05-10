import uuid
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.models.company import ZaubaCompany, DataGovCompany, MatchedCompany
from app.models.scrape_job import ScrapeJob
from app.services.zauba_scraper import ZaubaScraper
from app.services.datagov_scraper import DataGovScraper
from app.services.matcher_service import batch_match
from app.services.auth_service import get_current_user
from app.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/scraper", tags=["scraper"])
limiter = Limiter(key_func=get_remote_address)


async def run_full_scrape(job_id: str, date_from: date, date_to: date):
    from app.database import AsyncSessionLocal
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with AsyncSessionLocal() as db:
        try:
            await db.execute(
                update(ScrapeJob).where(ScrapeJob.id == uuid.UUID(job_id)).values(status="running")
            )
            await db.commit()

            zauba_scraper = ZaubaScraper()
            zauba_records = []
            async for company in zauba_scraper.scrape_companies(date_from=date_from, date_to=date_to):
                zauba_records.append(company)
                if len(zauba_records) % 100 == 0:
                    log.info("zauba_progress", count=len(zauba_records))

            if zauba_records:
                for batch in [zauba_records[i:i+500] for i in range(0, len(zauba_records), 500)]:
                    for r in batch:
                        r["scrape_job_id"] = uuid.UUID(job_id)
                        if r.get("cin"):
                            stmt = pg_insert(ZaubaCompany).values(**r).on_conflict_do_update(
                                index_elements=["cin"],
                                set_={"company_status": r.get("company_status"), "scraped_at": r.get("scraped_at")}
                            )
                        else:
                            stmt = pg_insert(ZaubaCompany).values(**r).on_conflict_do_nothing()
                        await db.execute(stmt)
                await db.commit()

            dg_scraper = DataGovScraper()
            dg_records = []
            async for company in dg_scraper.scrape_companies(date_from=date_from, date_to=date_to):
                dg_records.append(company)

            if dg_records:
                for r in dg_records:
                    r["scrape_job_id"] = uuid.UUID(job_id)
                    stmt = pg_insert(DataGovCompany).values(**r).on_conflict_do_nothing()
                    await db.execute(stmt)
                await db.commit()

            matches = batch_match(zauba_records, dg_records)
            matched_count = 0

            for m in matches:
                if m["match_score"] >= settings.MATCH_CONFIDENCE_THRESHOLD:
                    z = m["zauba_company"]
                    d = m.get("datagov_company") or {}
                    inc_date = z.get("date_of_incorporation")
                    is_startup = False
                    if inc_date:
                        age_years = (date.today() - inc_date).days / 365
                        is_startup = age_years <= 10 and (z.get("authorised_capital") or 0) <= 100_000_000

                    mc = MatchedCompany(
                        company_name=z["company_name"],
                        cin=z.get("cin") or d.get("cin"),
                        match_score=m["match_score"],
                        match_method=m["match_method"],
                        company_status=z.get("company_status") or d.get("company_status"),
                        roc_code=z.get("roc_code") or d.get("roc_code"),
                        company_category=z.get("company_category") or d.get("company_category"),
                        date_of_incorporation=inc_date,
                        state=d.get("state"),
                        authorised_capital=z.get("authorised_capital"),
                        paid_up_capital=z.get("paid_up_capital"),
                        registered_address=z.get("registered_address"),
                        is_startup=is_startup,
                        incorporation_year=inc_date.year if inc_date else None,
                    )
                    db.add(mc)
                    matched_count += 1

            await db.execute(
                update(ScrapeJob).where(ScrapeJob.id == uuid.UUID(job_id)).values(
                    status="completed",
                    records_scraped=len(zauba_records),
                    records_matched=matched_count,
                    completed_at=datetime.utcnow(),
                )
            )
            await db.commit()
            log.info("scrape_complete", job_id=job_id, matched=matched_count)

        except Exception as e:
            log.error("scrape_failed", job_id=job_id, error=str(e))
            try:
                await db.execute(
                    update(ScrapeJob).where(ScrapeJob.id == uuid.UUID(job_id)).values(
                        status="failed", error_message=str(e)[:500]
                    )
                )
                await db.commit()
            except Exception:
                pass


@router.post("/trigger")
@limiter.limit(settings.RATE_LIMIT_SCRAPER)
async def trigger_scrape(
    request: Request,
    background_tasks: BackgroundTasks,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(credentials.credentials, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    if not date_from:
        date_from = date.today() - timedelta(days=365 * 3)
    if not date_to:
        date_to = date.today()

    job = ScrapeJob(triggered_by=user.id, source="both", status="pending")
    db.add(job)
    await db.flush()
    job_id = str(job.id)

    background_tasks.add_task(run_full_scrape, job_id, date_from, date_to)
    return {"job_id": job_id, "status": "pending", "message": "Scrape job queued"}


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)
    result = await db.execute(select(ScrapeJob).where(ScrapeJob.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "records_scraped": job.records_scraped,
        "records_matched": job.records_matched,
        "error_message": job.error_message,
    }


@router.get("/jobs")
async def list_jobs(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)
    result = await db.execute(
        select(ScrapeJob).order_by(ScrapeJob.started_at.desc()).limit(20)
    )
    jobs = result.scalars().all()
    return [
        {
            "job_id": str(j.id),
            "status": j.status,
            "source": j.source,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "records_scraped": j.records_scraped,
            "records_matched": j.records_matched,
        }
        for j in jobs
    ]
