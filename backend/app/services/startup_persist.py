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
            # Merge service_areas/active_years into extras (don't clobber LLM extras)
            extra_seed = {}
            if it.get("service_areas"): extra_seed["service_areas"] = it["service_areas"]
            if it.get("active_years"): extra_seed["active_years"] = it["active_years"]
            if extra_seed:
                merged = dict(existing.extras or {})
                merged.update(extra_seed)
                existing.extras = merged
            existing.raw = it.get("raw") or existing.raw
        else:
            seed_extras: dict = {}
            if it.get("service_areas"): seed_extras["service_areas"] = it["service_areas"]
            if it.get("active_years"): seed_extras["active_years"] = it["active_years"]
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
                extras=seed_extras or None,
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
