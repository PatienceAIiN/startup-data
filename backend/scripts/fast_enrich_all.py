"""Quickly enrich un-enriched startups in the database using fast_enrich (Google AI Overview) and commit immediately."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add backend root directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.startup import StartupIndiaCompany
from app.services.fast_enricher import fast_enrich

CONCURRENCY_LIMIT = 4  # Number of concurrent search queries

async def enrich_and_save_startup(sem: asyncio.Semaphore, company_id: str, name: str, index: int, total: int):
    async with sem:
        print(f"[{index}/{total}] Starting enrichment for: {name} (ID: {company_id})")
        try:
            # Run fast_enrich with a 15-second budget
            info = await fast_enrich(name, timeout_s=15.0)
        except Exception as e:
            print(f"[ERROR] [{index}/{total}] Failed to enrich {name}: {str(e)}")
            return

        # Prepare a dict of fields to save even if info is empty (to set contact_enriched_at and avoid re-processing)
        async with AsyncSessionLocal() as db:
            try:
                row_result = await db.execute(
                    select(StartupIndiaCompany).where(StartupIndiaCompany.id == company_id)
                )
                row = row_result.scalar_one_or_none()
                if not row:
                    print(f"[WARN] [{index}/{total}] Company {name} not found in DB anymore.")
                    return

                if info:
                    if info.get("email"): row.contact_email = info["email"]
                    if info.get("phone"): row.contact_phone = info["phone"]
                    if info.get("address"): row.contact_address = info["address"]
                    if info.get("linkedin"): row.linkedin_url = info["linkedin"]
                    if info.get("twitter"): row.twitter_url = info["twitter"]
                    if info.get("facebook"): row.facebook_url = info["facebook"]
                    if info.get("cin"): row.cin_real = info["cin"]
                    if info.get("gst"): row.gst = info["gst"]
                    if info.get("extras"):
                        merged_extras = dict(row.extras or {})
                        merged_extras.update({k: v for k, v in info["extras"].items() if v})
                        if merged_extras: row.extras = merged_extras
                    if info.get("website"):
                        row.website = info["website"]
                    print(f"[SUCCESS] [{index}/{total}] Enriched {name}: "
                          f"Email={bool(info.get('email'))}, Phone={bool(info.get('phone'))}, "
                          f"CIN={bool(info.get('cin'))}, AI Overview={bool(info.get('extras', {}).get('google_ai_overview'))}")
                else:
                    print(f"[INFO] [{index}/{total}] No verified data found for: {name}")

                # Mark as enriched so we don't scan it again
                row.contact_enriched_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[ERROR] [{index}/{total}] Failed to save to DB for {name}: {str(e)}")

async def main():
    print("Initializing Database Session...")
    async with AsyncSessionLocal() as db:
        # Fetch all un-enriched startups
        result = await db.execute(
            select(StartupIndiaCompany)
            .where(StartupIndiaCompany.contact_enriched_at.is_(None))
            .order_by(StartupIndiaCompany.scraped_at.asc())
        )
        rows = result.scalars().all()
        
    total = len(rows)
    if total == 0:
        print("All startups are already enriched! Nothing to do.")
        return

    print(f"Found {total} un-enriched startups. Running enrichment with concurrency={CONCURRENCY_LIMIT}...")
    
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # Process tasks concurrently as they complete
    tasks = [
        enrich_and_save_startup(sem, str(row.id), row.company_name, i + 1, total)
        for i, row in enumerate(rows)
    ]
    
    await asyncio.gather(*tasks)
    print("Enrichment batch processing completed!")

if __name__ == "__main__":
    asyncio.run(main())
