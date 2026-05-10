"""Promote Zauba-only companies into MatchedCompany.

Without a data.gov.in API key, no cross-source matches happen, leaving the
matched_companies table empty. Treat Zauba records as authoritative and
promote them — score=1.0 (CIN is unique), method='zauba_only'.
"""
import asyncio
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.company import ZaubaCompany, MatchedCompany


async def main():
    async with AsyncSessionLocal() as db:
        z_rows = (await db.execute(select(ZaubaCompany))).scalars().all()
        existing_cins = set(
            (await db.execute(select(MatchedCompany.cin).where(MatchedCompany.cin.is_not(None)))).scalars().all()
        )
        promoted = 0
        for z in z_rows:
            if z.cin and z.cin in existing_cins:
                continue
            inc_date = z.date_of_incorporation
            is_startup = False
            if inc_date:
                age_years = (date.today() - inc_date).days / 365
                is_startup = age_years <= 10 and (z.authorised_capital or 0) <= 100_000_000

            mc = MatchedCompany(
                zauba_id=z.id,
                company_name=z.company_name,
                cin=z.cin,
                match_score=1.0,
                match_method="zauba_only",
                company_status=z.company_status,
                roc_code=z.roc_code,
                company_category=z.company_category,
                date_of_incorporation=inc_date,
                state=None,
                authorised_capital=z.authorised_capital,
                paid_up_capital=z.paid_up_capital,
                registered_address=z.registered_address,
                is_startup=is_startup,
                incorporation_year=inc_date.year if inc_date else None,
            )
            db.add(mc)
            promoted += 1
        await db.commit()
        print(f"[OK] Promoted {promoted} companies into matched_companies")
        total = (await db.execute(select(MatchedCompany))).scalars().all()
        print(f"     Total in matched_companies: {len(total)}")


if __name__ == "__main__":
    asyncio.run(main())
