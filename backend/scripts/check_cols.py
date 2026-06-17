import asyncio
import sys
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

sys.path.insert(0, str(backend_dir))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def db_run():
    async with AsyncSessionLocal() as db:
        cnt_all = (await db.execute(text("SELECT count(*) FROM matched_companies"))).scalar()
        cnt_startups = (await db.execute(text("SELECT count(*) FROM matched_companies WHERE is_startup = true"))).scalar()
        cnt_non_startups = (await db.execute(text("SELECT count(*) FROM matched_companies WHERE is_startup = false"))).scalar()
        cnt_non_startups_unenriched = (await db.execute(text("SELECT count(*) FROM matched_companies WHERE is_startup = false AND contact_enriched_at IS NULL"))).scalar()
        print(f"Total matched_companies: {cnt_all}")
        print(f"Startups in matched_companies: {cnt_startups}")
        print(f"Non-startups in matched_companies: {cnt_non_startups}")
        print(f"Un-enriched non-startups in matched_companies: {cnt_non_startups_unenriched}")

asyncio.run(db_run())
