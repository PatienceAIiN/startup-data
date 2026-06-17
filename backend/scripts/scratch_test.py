import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, func

# Add backend root directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import AsyncSessionLocal
from app.models.startup import StartupIndiaCompany
from app.models.company import MatchedCompany

async def check_db_stats():
    async with AsyncSessionLocal() as db:
        # 1. Startups
        total_startups = (await db.execute(select(func.count(StartupIndiaCompany.id)))).scalar()
        enriched_startups = (await db.execute(
            select(func.count(StartupIndiaCompany.id))
            .where(StartupIndiaCompany.contact_enriched_at.is_not(None))
        )).scalar()
        
        # 2. Companies
        total_companies = (await db.execute(select(func.count(MatchedCompany.id)))).scalar()
        enriched_companies = (await db.execute(
            select(func.count(MatchedCompany.id))
            .where(MatchedCompany.contact_enriched_at.is_not(None))
        )).scalar()
        
        print("DATABASE STATISTICS:")
        print(f"Total Startups in DB: {total_startups}")
        print(f"Enriched Startups   : {enriched_startups}")
        print(f"Pending Startups    : {total_startups - enriched_startups}")
        print("-" * 40)
        print(f"Total Companies in DB: {total_companies}")
        print(f"Enriched Companies   : {enriched_companies}")
        print(f"Pending Companies    : {total_companies - enriched_companies}")

if __name__ == "__main__":
    asyncio.run(check_db_stats())
