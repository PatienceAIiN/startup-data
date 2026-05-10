import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.company import MatchedCompany


async def main():
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count()).select_from(MatchedCompany))).scalar()
        with_date = (await db.execute(
            select(func.count()).select_from(MatchedCompany).where(MatchedCompany.date_of_incorporation.is_not(None))
        )).scalar()
        sample = (await db.execute(select(MatchedCompany).limit(5))).scalars().all()
        print(f"Total: {total}, With date: {with_date}")
        for c in sample:
            print(f"  {c.company_name[:50]:50s} | CIN: {c.cin} | Inc: {c.date_of_incorporation} | Status: {c.company_status}")


asyncio.run(main())
