"""StartupIndia listings + on-demand scrape trigger."""
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models.startup import StartupIndiaCompany, ScrapeCursor
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/startups", tags=["startups"])


@router.get("")
async def list_startups(
    search: Optional[str] = Query(None, max_length=200),
    industry: Optional[str] = Query(None, max_length=200),
    sector: Optional[str] = Query(None, max_length=200),
    stage: Optional[str] = Query(None, max_length=100),
    state: Optional[str] = Query(None, max_length=100),
    dpiit_only: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

    query = select(StartupIndiaCompany)
    count_query = select(func.count()).select_from(StartupIndiaCompany)
    filters = []
    if search:
        s = f"%{search}%"
        filters.append(or_(
            StartupIndiaCompany.company_name.ilike(s),
            StartupIndiaCompany.industry.ilike(s),
            StartupIndiaCompany.sector.ilike(s),
            StartupIndiaCompany.state.ilike(s),
            StartupIndiaCompany.city.ilike(s),
        ))
    if industry:
        filters.append(StartupIndiaCompany.industry.ilike(f"%{industry}%"))
    if sector:
        filters.append(StartupIndiaCompany.sector.ilike(f"%{sector}%"))
    if stage:
        filters.append(StartupIndiaCompany.stage.ilike(f"%{stage}%"))
    if state:
        filters.append(StartupIndiaCompany.state.ilike(f"%{state}%"))
    if dpiit_only:
        filters.append(StartupIndiaCompany.dpiit_recognised == True)

    for f in filters:
        query = query.where(f)
        count_query = count_query.where(f)

    total = (await db.execute(count_query)).scalar() or 0

    # Live-search fallback: if a name was searched and we have no match in DB,
    # ask startupindia.gov.in directly, persist, then re-count.
    if search and total == 0:
        import asyncio as _asyncio
        import structlog
        from app.services.startupindia_scraper import StartupIndiaScraper
        from app.services.startup_persist import upsert_startups
        try:
            items = await _asyncio.wait_for(
                StartupIndiaScraper(page_size=20).scrape_by_query(search),
                timeout=15.0,
            )
            if items:
                await upsert_startups(db, items)
                await db.commit()
                total = (await db.execute(count_query)).scalar() or 0
        except _asyncio.TimeoutError:
            structlog.get_logger().warning("startupindia.live_search_timeout", q=search)
        except Exception as e:
            structlog.get_logger().error("startupindia.live_search_failed", error=str(e))

    query = query.order_by(StartupIndiaCompany.scraped_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    def _serialize(r: StartupIndiaCompany):
        return {
            "id": str(r.id),
            "profile_id": r.profile_id,
            "profile_url": r.profile_url,
            "company_name": r.company_name,
            "description": r.description,
            "industry": r.industry,
            "sector": r.sector,
            "stage": r.stage,
            "state": r.state,
            "city": r.city,
            "website": r.website,
            "logo_url": r.logo_url,
            "badges": r.badges or [],
            "dpiit_recognised": r.dpiit_recognised,
            "dipp_number": r.dipp_number,
            "contact_email": r.contact_email,
            "contact_phone": r.contact_phone,
            "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
        }

    return {
        "items": [_serialize(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/lookup")
async def lookup_startup(
    name: str = Query(..., min_length=2, max_length=200),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """Synchronous live check + persist. Returns one of:
    - {status: 'cached', count: N}     -> already in our DB
    - {status: 'found',  count: N}     -> live-fetched & saved
    - {status: 'not_found'}            -> portal returned no match
    - {status: 'unavailable'}          -> source unreachable; please retry
    """
    await get_current_user(credentials.credentials, db)
    import asyncio as _asyncio
    import structlog
    from app.services.startupindia_scraper import StartupIndiaScraper
    from app.services.startup_persist import upsert_startups
    log = structlog.get_logger()

    # 1) DB hit?
    existing = (await db.execute(
        select(StartupIndiaCompany).where(StartupIndiaCompany.company_name.ilike(f"%{name}%"))
    )).scalars().all()
    if existing:
        return {"status": "cached", "count": len(existing)}

    # 2) Live lookup with strict 10s budget
    try:
        items = await _asyncio.wait_for(
            StartupIndiaScraper(page_size=20).scrape_by_query(name),
            timeout=10.0,
        )
    except _asyncio.TimeoutError:
        log.warning("startups.lookup_timeout", q=name)
        return {"status": "unavailable"}
    except Exception as e:
        log.error("startups.lookup_failed", q=name, error=str(e))
        return {"status": "unavailable"}

    if not items:
        return {"status": "not_found"}

    await upsert_startups(db, items)
    await db.commit()
    return {"status": "found", "count": len(items)}


@router.get("/by-cin/{cin}")
async def get_startup_by_cin(
    cin: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """Look up rich startup detail by the mirrored CIN (`SIH-<profile_id>`)."""
    await get_current_user(credentials.credentials, db)
    if not cin.startswith("SIH-"):
        raise HTTPException(status_code=404, detail="Not a startup record")
    pid = cin[len("SIH-"):]
    row = (await db.execute(
        select(StartupIndiaCompany).where(StartupIndiaCompany.profile_id == pid)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Startup not found")
    # Pull MCA capital / status from the mirror row so the modal can show
    # financials sourced from the registry alongside startupindia data.
    from app.models.company import MatchedCompany
    mirror = (await db.execute(
        select(MatchedCompany).where(MatchedCompany.cin == cin)
    )).scalar_one_or_none()
    extras = dict(row.extras or {})
    if mirror is not None:
        if mirror.authorised_capital is not None and "authorised_capital" not in extras:
            extras["authorised_capital"] = mirror.authorised_capital
        if mirror.paid_up_capital is not None and "paid_up_capital" not in extras:
            extras["paid_up_capital"] = mirror.paid_up_capital
        if mirror.date_of_incorporation and "date_of_incorporation" not in extras:
            extras["date_of_incorporation"] = mirror.date_of_incorporation.isoformat()
        if mirror.company_status and "company_status" not in extras:
            extras["company_status"] = mirror.company_status
    return {
        "id": str(row.id),
        "profile_id": row.profile_id,
        "profile_url": row.profile_url,
        "company_name": row.company_name,
        "description": row.description,
        "industry": row.industry,
        "sector": row.sector,
        "stage": row.stage,
        "state": row.state,
        "city": row.city,
        "website": row.website,
        "logo_url": row.logo_url,
        "badges": row.badges or [],
        "dpiit_recognised": row.dpiit_recognised,
        "dipp_number": row.dipp_number,
        "contact_email": row.contact_email,
        "contact_phone": row.contact_phone,
        "contact_address": row.contact_address,
        "linkedin_url": row.linkedin_url,
        "twitter_url": row.twitter_url,
        "facebook_url": row.facebook_url,
        "source_url": row.source_url,
        "contact_enriched_at": row.contact_enriched_at.isoformat() if row.contact_enriched_at else None,
        "scraped_at": row.scraped_at.isoformat() if row.scraped_at else None,
        "cin_real": row.cin_real,
        "gst": row.gst,
        "extras": extras,
    }


@router.post("/enrich/{cin}")
async def enrich_startup(
    cin: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """Run the contact enricher for a startup if not already enriched."""
    await get_current_user(credentials.credentials, db)
    if not cin.startswith("SIH-"):
        raise HTTPException(status_code=400, detail="Not a startup record")
    pid = cin[len("SIH-"):]
    row = (await db.execute(
        select(StartupIndiaCompany).where(StartupIndiaCompany.profile_id == pid)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Startup not found")

    # Skip if recently enriched
    if row.contact_enriched_at and row.contact_email:
        return {"status": "cached"}

    import asyncio as _asyncio
    import structlog
    from datetime import datetime
    from app.services.fast_enricher import fast_enrich
    log = structlog.get_logger()
    # Click flow: fast (≤8s) httpx-only path with strict source verification.
    # The deeper Playwright + site-crawl enricher still runs in the background
    # scheduler sweep for thorough fills.
    async def _try(budget: float) -> dict:
        try:
            return await _asyncio.wait_for(fast_enrich(row.company_name, timeout_s=budget), timeout=budget + 2)
        except _asyncio.TimeoutError:
            log.warning("startups.enrich_timeout", cin=cin)
            return {}
        except Exception as e:
            log.error("startups.enrich_failed", cin=cin, error=str(e))
            return {}

    # First pass — short budget for fast happy path.
    info = await _try(10.0)
    # If the first attempt returned nothing (Groq TPM hit / source flake),
    # immediately retry with a larger budget. Avoids "click → no data → reclick" UX.
    if not info:
        info = await _try(15.0)
    if not info:
        # Nothing verified after retry — do NOT stamp enriched_at, so a manual
        # refresh re-tries. Surface a clear signal to the UI.
        return {"status": "no_data"}

    # Prefer enriched values over existing nulls; don't overwrite good data with null
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
        row.website = info["source"].split("/contact")[0].rstrip("/") + "/" if "/contact" in info["source"] else info["source"]
    row.contact_enriched_at = datetime.utcnow()
    await db.commit()
    return {
        "status": "enriched",
        "found_email": bool(info.get("email")),
        "found_phone": bool(info.get("phone")),
        "found_address": bool(info.get("address")),
        "source": info.get("source"),
    }


@router.get("/status")
async def scrape_status(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)
    cursor = (
        await db.execute(select(ScrapeCursor).where(ScrapeCursor.source == "startupindia"))
    ).scalar_one_or_none()
    total = (await db.execute(select(func.count()).select_from(StartupIndiaCompany))).scalar() or 0
    return {
        "source": "startupindia",
        "total_startups": total,
        "page": cursor.page if cursor else 0,
        "exhausted": cursor.exhausted if cursor else False,
        "last_run_at": cursor.last_run_at.isoformat() if cursor and cursor.last_run_at else None,
        "last_count": cursor.last_count if cursor else 0,
        "notes": cursor.notes if cursor else None,
    }


@router.post("/scrape-now")
async def scrape_now(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """Trigger one scrape cycle immediately (admin)."""
    user = await get_current_user(credentials.credentials, db)
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin only")
    from app.services.scheduler_service import startupindia_tick
    await startupindia_tick()
    return {"ok": True}
