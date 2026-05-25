import asyncio
from datetime import date, timedelta
from uuid import uuid4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import AsyncSessionLocal
from app.models.scrape_job import ScrapeJob
from app.routers.scraper import run_full_scrape

async def main():
    async with AsyncSessionLocal() as db:
        job = ScrapeJob(triggered_by=uuid4(), source="both", status="pending")
        db.add(job)
        await db.commit()
        job_id = str(job.id)
        
    print(f"Triggering real scrape for Job ID: {job_id}")
    date_to = date.today()
    date_from = date_to - timedelta(days=5) # Scrape the last 5 days
    
    await run_full_scrape(job_id, date_from, date_to)

if __name__ == "__main__":
    asyncio.run(main())
