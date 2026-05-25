import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.company import MatchedCompany
import structlog
from thefuzz import fuzz

log = structlog.get_logger()

async def main(csv_path: str):
    log.info("ingest_startup_csv.started", path=csv_path)
    
    merged_count = 0
    new_count = 0

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(MatchedCompany.id, MatchedCompany.company_name, MatchedCompany.company_category, MatchedCompany.match_score))
        existing = res.fetchall()
        
        # Build list for faster matching
        company_data = [(row.id, row.company_name, row.company_category, row.match_score) for row in existing if row.company_name]
        log.info("loaded_existing_companies", count=len(company_data))

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            new_batch = []
            
            for i, row in enumerate(reader):
                startup_name = row.get("Startup", "").strip()
                if not startup_name:
                    continue
                    
                industry = row.get("Industry", "").strip()
                city = row.get("City", "").strip()
                
                # Fast fuzzy match using token_set_ratio
                best_match = None
                best_score = 0
                
                for cid, cname, ccat, cscore in company_data:
                    # Very fast partial check first
                    if startup_name.lower() in cname.lower():
                        score = fuzz.token_set_ratio(startup_name, cname)
                        if score > best_score:
                            best_score = score
                            best_match = (cid, cname, ccat, cscore)
                
                # If no strict substring, fallback to full fuzzy search for a decent match
                if best_score < 80:
                    for cid, cname, ccat, cscore in company_data:
                        score = fuzz.token_set_ratio(startup_name, cname)
                        if score > best_score:
                            best_score = score
                            best_match = (cid, cname, ccat, cscore)
                            if best_score == 100: break

                if best_match and best_score >= 80:
                    cid, cname, ccat, cscore = best_match
                    new_cat = f"{ccat} | {industry}" if ccat else industry
                    new_score = (cscore + (best_score / 100.0)) / 2.0
                    
                    await db.execute(
                        update(MatchedCompany)
                        .where(MatchedCompany.id == cid)
                        .values(
                            is_startup=True,
                            match_score=new_score,
                            company_category=new_cat
                        )
                    )
                    merged_count += 1
                else:
                    mc = MatchedCompany(
                        company_name=startup_name,
                        match_score=1.0,
                        match_method="startup_india_csv",
                        company_category=industry,
                        state=city,
                        is_startup=True
                    )
                    new_batch.append(mc)
                    new_count += 1

                if (i + 1) % 50 == 0:
                    await db.commit()
                    log.info("ingest_startup_csv.progress", processed=i+1, merged=merged_count, new=new_count)

            if new_batch:
                db.add_all(new_batch)
            await db.commit()

        log.info("ingest_startup_csv.completed", merged=merged_count, new_inserted=new_count)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <path>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
