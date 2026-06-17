"""Quickly enrich un-enriched non-startup companies in the database using fast_enrich and commit immediately."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.company import MatchedCompany
from app.services.fast_enricher import fast_enrich

CONCURRENCY_LIMIT = 5  # Number of concurrent search queries

async def enrich_and_save_company(sem: asyncio.Semaphore, company_id: str, name: str, index: int, total: int):
    async with sem:
        print(f"[{index}/{total}] Starting company enrichment for: {name} (ID: {company_id})", flush=True)
        try:
            # Run fast_enrich with a 15-second budget
            info = await fast_enrich(name, timeout_s=15.0)
        except Exception as e:
            print(f"[ERROR] [{index}/{total}] Failed to enrich {name}: {str(e)}", flush=True)
            return

        async with AsyncSessionLocal() as db:
            try:
                row_result = await db.execute(
                    select(MatchedCompany).where(MatchedCompany.id == company_id)
                )
                row = row_result.scalar_one_or_none()
                if not row:
                    print(f"[WARN] [{index}/{total}] Company {name} not found in DB anymore.", flush=True)
                    return

                if info:
                    if info.get("email"): row.contact_email = info["email"]
                    if info.get("phone"): row.contact_phone = info["phone"]
                    if info.get("website") and not row.website: row.website = info["website"]
                    if info.get("address") and not row.registered_address: row.registered_address = info["address"]
                    if info.get("cin") and not row.cin: row.cin = info["cin"]
                    
                    print(f"[SUCCESS] [{index}/{total}] Enriched {name}: "
                          f"Email={bool(info.get('email'))}, Phone={bool(info.get('phone'))}, "
                          f"CIN={bool(info.get('cin'))}", flush=True)
                else:
                    print(f"[INFO] [{index}/{total}] No verified data found for: {name}", flush=True)

                # Mark as enriched so we don't scan it again
                row.contact_enriched_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"[ERROR] [{index}/{total}] Failed to save to DB for {name}: {str(e)}", flush=True)

async def main():
    print("Initializing Database Session...", flush=True)
    async with AsyncSessionLocal() as db:
        # Fetch un-enriched non-startup companies (limit to a batch of 5000 to prevent loading too many into memory)
        result = await db.execute(
            select(MatchedCompany)
            .where(MatchedCompany.is_startup == False)
            .where(MatchedCompany.contact_enriched_at.is_(None))
            .order_by(MatchedCompany.created_at.asc())
            .limit(5000)
        )
        rows = result.scalars().all()
        
    total = len(rows)
    if total == 0:
        print("All companies are already enriched! Nothing to do.", flush=True)
        return

    print(f"Found {total} un-enriched companies (batch limited to 5000). Running enrichment with concurrency={CONCURRENCY_LIMIT}...", flush=True)
    
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # Process tasks concurrently
    tasks = [
        enrich_and_save_company(sem, str(row.id), row.company_name, i + 1, total)
        for i, row in enumerate(rows)
    ]
    
    await asyncio.gather(*tasks)
    print("Enrichment batch processing completed!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
