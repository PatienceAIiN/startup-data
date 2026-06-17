from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.company import MatchedCompany
from app.models.startup import StartupIndiaCompany
from app.models.export_file import ExportFile
from app.services.auth_service import get_current_user
from app.services.export_service import create_and_upload_export

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("/{file_type}")
async def export_companies(
    file_type: str,
    search: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_startup: Optional[bool] = Query(None),
    min_score: Optional[float] = Query(None),
    page: Optional[int] = Query(None),
    page_size: Optional[int] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    if file_type not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="file_type must be 'csv' or 'xlsx'")

    user = await get_current_user(credentials.credentials, db)

    # LEFT JOIN StartupIndiaCompany on the mirror's "SIH-<profile_id>" cin so
    # exports can include city / email / phone / DPIIT for startup rows.
    sih_profile = func.substr(MatchedCompany.cin, 5)  # strip "SIH-" prefix
    query = (
        select(
            MatchedCompany,
            StartupIndiaCompany.city,
            StartupIndiaCompany.contact_email,
            StartupIndiaCompany.contact_phone,
            StartupIndiaCompany.dpiit_recognised,
            StartupIndiaCompany.dipp_number,
        )
        .outerjoin(
            StartupIndiaCompany,
            StartupIndiaCompany.profile_id == sih_profile,
        )
    )

    from sqlalchemy import or_
    if search:
        query = query.where(or_(
            MatchedCompany.company_name.ilike(f"%{search}%"),
            MatchedCompany.cin.ilike(f"%{search}%"),
            MatchedCompany.company_category.ilike(f"%{search}%"),
            MatchedCompany.state.ilike(f"%{search}%"),
        ))
    if date_from:
        query = query.where(or_(
            MatchedCompany.date_of_incorporation >= date_from,
            MatchedCompany.date_of_incorporation.is_(None),
        ))
    if date_to:
        query = query.where(or_(
            MatchedCompany.date_of_incorporation <= date_to,
            MatchedCompany.date_of_incorporation.is_(None),
        ))
    if state:
        query = query.where(MatchedCompany.state.ilike(f"%{state}%"))
    if city:
        query = query.where(StartupIndiaCompany.city.ilike(f"%{city}%"))
    if status:
        query = query.where(MatchedCompany.company_status.ilike(f"%{status}%"))
    if is_startup is not None:
        query = query.where(MatchedCompany.is_startup == is_startup)
    if min_score is not None:
        query = query.where(MatchedCompany.match_score >= min_score)

    query = query.order_by(MatchedCompany.date_of_incorporation.desc())
    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    else:
        query = query.limit(50000)

    rows = (await db.execute(query)).all()

    companies_dicts = [
        {
            "cin": c.cin,
            "company_name": c.company_name,
            "company_status": c.company_status,
            "roc_code": c.roc_code,
            "company_category": c.company_category,
            "date_of_incorporation": c.date_of_incorporation,
            "state": c.state,
            "city": city,
            "authorised_capital": c.authorised_capital,
            "paid_up_capital": c.paid_up_capital,
            "match_score": c.match_score,
            "match_method": c.match_method,
            "is_startup": c.is_startup,
            "registered_address": c.registered_address,
            "contact_email": contact_email or c.contact_email,
            "contact_phone": contact_phone or c.contact_phone,
            "dpiit_recognised": bool(dpiit_recognised) if dpiit_recognised is not None else False,
            "dipp_number": dipp_number,
        }
        for c, city, contact_email, contact_phone, dpiit_recognised, dipp_number in rows
    ]

    filter_params = {
        "search": search,
        "date_from": str(date_from) if date_from else None,
        "date_to": str(date_to) if date_to else None,
        "state": state,
        "city": city,
        "status": status,
        "is_startup": is_startup,
        "min_score": min_score,
        "page": page,
        "page_size": page_size,
    }

    export_meta = await create_and_upload_export(
        companies_dicts, file_type, str(user.id), filter_params
    )

    ef = ExportFile(
        exported_by=user.id,
        file_type=file_type,
        file_name=export_meta["file_name"],
        r2_key=export_meta["r2_key"],
        r2_url=export_meta["r2_url"],
        file_size_bytes=export_meta["file_size_bytes"],
        record_count=export_meta["record_count"],
        filter_params=filter_params,
    )
    db.add(ef)

    return {
        "download_url": export_meta["r2_url"],
        "file_name": export_meta["file_name"],
        "record_count": export_meta["record_count"],
        "file_size_bytes": export_meta["file_size_bytes"],
        "expires_in_hours": 24,
    }


@router.get("/history")
async def export_history(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(credentials.credentials, db)
    result = await db.execute(
        select(ExportFile)
        .where(ExportFile.exported_by == user.id)
        .order_by(ExportFile.created_at.desc())
        .limit(20)
    )
    files = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "file_name": f.file_name,
            "file_type": f.file_type,
            "record_count": f.record_count,
            "r2_url": f.r2_url,
            "created_at": f.created_at,
        }
        for f in files
    ]
