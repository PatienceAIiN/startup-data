"""Ingest an MCA CSV data dump to populate missing company details.

Usage:
    python3 scripts/ingest_mca_csv.py <path_to_csv>
"""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.company import MatchedCompany
import structlog

log = structlog.get_logger()

async def main(csv_path: str):
    log.info("ingest_mca_csv.started", path=csv_path)
    
    updated_count = 0
    not_found_count = 0

    async with AsyncSessionLocal() as db:
        # Load all CINs we care about from MatchedCompany to reduce query overhead
        # In a real large scale app, we might do chunked processing.
        matched_cins_result = await db.execute(select(MatchedCompany.cin).where(MatchedCompany.cin.is_not(None)))
        existing_cins = set(matched_cins_result.scalars().all())

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            # Normalize headers
            headers = [h.strip().upper() for h in reader.fieldnames] if reader.fieldnames else []
            reader.fieldnames = headers

            batch = []
            for row in reader:
                cin = row.get("CIN") or row.get("LLPIN") or row.get("REG_NO")
                if not cin:
                    continue
                cin = cin.strip().upper()
                
                if cin not in existing_cins:
                    not_found_count += 1
                    continue
                
                # Parse numeric values carefully
                auth_cap_raw = row.get("AUTHORIZED_CAPITAL") or "0"
                paid_cap_raw = row.get("PAIDUP_CAPITAL") or "0"
                
                try:
                    auth_cap = int(float(auth_cap_raw))
                except Exception:
                    auth_cap = None
                    
                try:
                    paid_cap = int(float(paid_cap_raw))
                except Exception:
                    paid_cap = None

                state = row.get("STATE", "").strip() or None
                category = row.get("COMPANY_CATEGORY", "").strip() or None
                status = row.get("COMPANY_STATUS", "").strip() or None
                address = row.get("REGISTERED_ADDRESS", "").strip() or None

                # Update the MatchedCompany record
                await db.execute(
                    update(MatchedCompany)
                    .where(MatchedCompany.cin == cin)
                    .values(
                        authorised_capital=auth_cap,
                        paid_up_capital=paid_cap,
                        state=state,
                        company_category=category,
                        company_status=status,
                        registered_address=address,
                        match_method="csv_enriched"
                    )
                )
                
                updated_count += 1
                
                if updated_count % 500 == 0:
                    await db.commit()
                    log.info("ingest_mca_csv.progress", updated=updated_count)

        await db.commit()
        log.info("ingest_mca_csv.completed", updated=updated_count, skipped_not_in_db=not_found_count)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/ingest_mca_csv.py <path_to_csv>")
        sys.exit(1)
        
    csv_file_path = sys.argv[1]
    if not Path(csv_file_path).exists():
        print(f"File not found: {csv_file_path}")
        sys.exit(1)
        
    asyncio.run(main(csv_file_path))
