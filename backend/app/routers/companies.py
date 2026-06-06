import math
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.company import MatchedCompany
from app.schemas.company import CompanyPageResponse, CompanyStatsResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompanyPageResponse)
async def list_companies(
    search: Optional[str] = Query(None, max_length=200),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    state: Optional[str] = Query(None, max_length=100),
    city: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None, max_length=100),
    is_startup: Optional[bool] = Query(None),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

    query = select(MatchedCompany)
    count_query = select(func.count()).select_from(MatchedCompany)

    filters = []
    from sqlalchemy import or_
    if search:
        filters.append(or_(
            MatchedCompany.company_name.ilike(f"%{search}%"),
            MatchedCompany.cin.ilike(f"%{search}%"),
            MatchedCompany.company_category.ilike(f"%{search}%"),
            MatchedCompany.state.ilike(f"%{search}%"),
        ))
    if date_from:
        filters.append(or_(
            MatchedCompany.date_of_incorporation >= date_from,
            MatchedCompany.date_of_incorporation.is_(None),
        ))
    if date_to:
        filters.append(or_(
            MatchedCompany.date_of_incorporation <= date_to,
            MatchedCompany.date_of_incorporation.is_(None),
        ))
    if state:
        filters.append(MatchedCompany.state.ilike(f"%{state}%"))
    if city:
        # City data lives on the StartupIndia mirror — restrict to those rows.
        from app.models.startup import StartupIndiaCompany
        sub = (
            select(("SIH-" + StartupIndiaCompany.profile_id).label("cin"))
            .where(StartupIndiaCompany.city.ilike(f"%{city}%"))
        )
        filters.append(MatchedCompany.cin.in_(sub))
    if status:
        filters.append(MatchedCompany.company_status.ilike(f"%{status}%"))
    if is_startup is not None:
        filters.append(MatchedCompany.is_startup == is_startup)
    if min_score is not None:
        filters.append(MatchedCompany.match_score >= min_score)

    # No default date filter — show all companies including those with NULL inc dates

    for f in filters:
        query = query.where(f)
        count_query = count_query.where(f)

    total = (await db.execute(count_query)).scalar() or 0

    # Startup-side live lookups are driven explicitly by the client via
    # GET /startups/lookup so the dashboard can show a clean status modal.
    # DataGov fallback only runs for non-startup searches — moved to background
    # so the request returns immediately and never causes a gateway timeout.
    if search and total == 0 and is_startup is not True:
        import asyncio as _asyncio
        import structlog
        from app.database import AsyncSessionLocal
        from app.services.datagov_scraper import DataGovScraper
        _log = structlog.get_logger()

        async def _bg_datagov(q: str):
            try:
                async with AsyncSessionLocal() as bg_db:
                    new_count = 0
                    async for c_data in DataGovScraper().scrape_companies(search_query=q, limit_per_page=50):
                        cin = c_data.get("cin")
                        if not cin:
                            continue
                        existing = (await bg_db.execute(
                            select(MatchedCompany).where(MatchedCompany.cin == cin)
                        )).scalar_one_or_none()
                        if existing:
                            continue
                        bg_db.add(MatchedCompany(
                            company_name=c_data.get("company_name"),
                            cin=cin,
                            match_score=1.0,
                            match_method="live_search",
                            company_status=c_data.get("company_status"),
                            roc_code=c_data.get("roc_code"),
                            company_category=c_data.get("company_category"),
                            date_of_incorporation=c_data.get("date_of_incorporation"),
                            state=c_data.get("state"),
                            authorised_capital=c_data.get("authorised_capital"),
                            paid_up_capital=c_data.get("paid_up_capital"),
                            is_startup=False,
                            incorporation_year=c_data.get("date_of_incorporation").year
                                if c_data.get("date_of_incorporation") else None,
                        ))
                        new_count += 1
                    if new_count:
                        await bg_db.commit()
                    _log.info("companies.bg_datagov_done", q=q, new=new_count)
            except Exception as e:
                _log.error("companies.bg_datagov_failed", q=q, error=str(e))

        _asyncio.create_task(_bg_datagov(search))

    query = query.order_by(MatchedCompany.date_of_incorporation.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return CompanyPageResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


_stats_cache = None
_stats_cache_expiry = 0.0

@router.get("/stats", response_model=CompanyStatsResponse)
async def get_stats(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

    global _stats_cache, _stats_cache_expiry
    import time
    now = time.time()
    if _stats_cache is not None and now < _stats_cache_expiry:
        return _stats_cache

    total = (await db.execute(select(func.count()).select_from(MatchedCompany))).scalar() or 0
    matched = (await db.execute(
        select(func.count()).select_from(MatchedCompany).where(MatchedCompany.match_score >= 0.75)
    )).scalar() or 0
    startups = (await db.execute(
        select(func.count()).select_from(MatchedCompany).where(MatchedCompany.is_startup == True)
    )).scalar() or 0
    avg_score_result = (await db.execute(select(func.avg(MatchedCompany.match_score)))).scalar()
    avg_score = round(float(avg_score_result or 0), 3)

    state_rows = (await db.execute(
        select(MatchedCompany.state, func.count().label("cnt"))
        .where(MatchedCompany.state != None)
        .group_by(MatchedCompany.state)
        .order_by(func.count().desc())
        .limit(10)
    )).all()

    year_rows = (await db.execute(
        select(
            func.extract("year", MatchedCompany.date_of_incorporation).label("yr"),
            func.count().label("cnt")
        )
        .where(MatchedCompany.date_of_incorporation != None)
        .group_by(func.extract("year", MatchedCompany.date_of_incorporation))
        .order_by(func.extract("year", MatchedCompany.date_of_incorporation).desc())
        .limit(10)
    )).all()

    res = CompanyStatsResponse(
        total_companies=total,
        matched_companies=matched,
        startups=startups,
        avg_match_score=avg_score,
        by_state={row.state: row.cnt for row in state_rows},
        by_year={int(row.yr): row.cnt for row in year_rows if row.yr},
        last_scrape=None,
    )
    _stats_cache = res
    _stats_cache_expiry = now + 60.0 # Cache for 60 seconds
    return res


@router.get("/states")
async def list_states(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """Distinct list of states across companies + startups (sorted)."""
    await get_current_user(credentials.credentials, db)
    from app.models.startup import StartupIndiaCompany
    rows_m = (await db.execute(
        select(MatchedCompany.state).where(MatchedCompany.state.isnot(None)).distinct()
    )).scalars().all()
    rows_s = (await db.execute(
        select(StartupIndiaCompany.state).where(StartupIndiaCompany.state.isnot(None)).distinct()
    )).scalars().all()
    # Deduplicate case-insensitively, prefer the title-cased / capitalised variant
    seen: dict[str, str] = {}
    for s in list(rows_m) + list(rows_s):
        if not s or not s.strip():
            continue
        clean = s.strip()
        key = clean.lower()
        if key not in seen or clean[0].isupper() and not seen[key][0].isupper():
            seen[key] = clean
    states = sorted(seen.values())
    return {"states": states}


@router.get("/cities")
async def list_cities(
    state: str = Query(..., min_length=1, max_length=100),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    """Distinct cities for the given state. Cities live on StartupIndia rows.
    For company-only data without a city column we still return whatever
    cities StartupIndia knows for that state."""
    await get_current_user(credentials.credentials, db)
    from app.models.startup import StartupIndiaCompany
    rows = (await db.execute(
        select(StartupIndiaCompany.city)
        .where(StartupIndiaCompany.state.ilike(state.strip()))
        .where(StartupIndiaCompany.city.isnot(None))
        .distinct()
    )).scalars().all()
    # Dedup cities case-insensitively too
    seen_c: dict[str, str] = {}
    for c in rows:
        if not c or not c.strip():
            continue
        clean = c.strip()
        key = clean.lower()
        if key not in seen_c or clean[0].isupper() and not seen_c[key][0].isupper():
            seen_c[key] = clean
    cities = sorted(seen_c.values())
    return {"state": state, "cities": cities}


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)
    import uuid
    result = await db.execute(select(MatchedCompany).where(MatchedCompany.id == uuid.UUID(company_id)))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company
