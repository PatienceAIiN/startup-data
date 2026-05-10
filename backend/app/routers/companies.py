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
    if search:
        filters.append(MatchedCompany.company_name.ilike(f"%{search}%"))
    from sqlalchemy import or_
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


@router.get("/stats", response_model=CompanyStatsResponse)
async def get_stats(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(credentials.credentials, db)

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

    return CompanyStatsResponse(
        total_companies=total,
        matched_companies=matched,
        startups=startups,
        avg_match_score=avg_score,
        by_state={row.state: row.cnt for row in state_rows},
        by_year={int(row.yr): row.cnt for row in year_rows if row.yr},
        last_scrape=None,
    )


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
