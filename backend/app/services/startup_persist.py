"""Persist scraped startupindia records into both StartupIndiaCompany and a
mirror row in MatchedCompany. Shared by the scheduler tick and live search."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.startup import StartupIndiaCompany
from app.models.company import MatchedCompany


async def upsert_startups(db: AsyncSession, items: list[dict]) -> int:
    """Insert/update each item. Returns count of new StartupIndiaCompany rows."""
    new_count = 0
    for it in items:
        pid = it.get("profile_id")
        if not pid:
            continue
        existing = (
            await db.execute(select(StartupIndiaCompany).where(StartupIndiaCompany.profile_id == pid))
        ).scalar_one_or_none()
        if existing:
            existing.company_name = it["company_name"]
            existing.description = it.get("description") or existing.description
            existing.industry = it.get("industry") or existing.industry
            existing.sector = it.get("sector") or existing.sector
            existing.stage = it.get("stage") or existing.stage
            existing.state = it.get("state") or existing.state
            existing.city = it.get("city") or existing.city
            existing.website = it.get("website") or existing.website
            existing.logo_url = it.get("logo_url") or existing.logo_url
            existing.badges = it.get("badges") or existing.badges
            existing.dpiit_recognised = bool(it.get("dpiit_recognised"))
            if it.get("dipp_number"): existing.dipp_number = it["dipp_number"]
            existing.raw = it.get("raw") or existing.raw
        else:
            db.add(StartupIndiaCompany(
                profile_id=pid,
                profile_url=it.get("profile_url"),
                company_name=it["company_name"],
                description=it.get("description"),
                industry=it.get("industry"),
                sector=it.get("sector"),
                stage=it.get("stage"),
                state=it.get("state"),
                city=it.get("city"),
                website=it.get("website"),
                logo_url=it.get("logo_url"),
                badges=it.get("badges") or [],
                dpiit_recognised=bool(it.get("dpiit_recognised")),
                dipp_number=it.get("dipp_number"),
                raw=it.get("raw"),
            ))
            new_count += 1

        mirror_cin = f"SIH-{pid}"
        mirror = (
            await db.execute(select(MatchedCompany).where(MatchedCompany.cin == mirror_cin))
        ).scalar_one_or_none()
        if mirror is None:
            db.add(MatchedCompany(
                company_name=it["company_name"],
                cin=mirror_cin,
                match_score=1.0,
                match_method="startupindia",
                company_status="Active",
                company_category=it.get("industry"),
                state=it.get("state"),
                website=it.get("website") or it.get("profile_url"),
                is_startup=True,
            ))
        else:
            # Backfill website on existing mirror rows if missing
            if not getattr(mirror, "website", None):
                mirror.website = it.get("website") or it.get("profile_url")
    return new_count
