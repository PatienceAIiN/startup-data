import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.company import MatchedCompany
import structlog

log = structlog.get_logger()

async def main(csv_path: str):
    log.info("ingest_mca_csv_insert.started", path=csv_path)
    
    inserted_count = 0
    skipped_count = 0

    async with AsyncSessionLocal() as db:
        matched_cins_result = await db.execute(select(MatchedCompany.cin).where(MatchedCompany.cin.is_not(None)))
        existing_cins = set(matched_cins_result.scalars().all())
        log.info("loaded_existing_cins", count=len(existing_cins))

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = [h.strip().upper() for h in reader.fieldnames] if reader.fieldnames else []
            reader.fieldnames = headers

            batch = []
            for row in reader:
                cin = row.get("CIN") or row.get("LLPIN") or row.get("REG_NO")
                if not cin: continue
                cin = cin.strip().upper()
                
                if cin in existing_cins:
                    skipped_count += 1
                    continue
                
                # Use correct mapped header names
                company_name = row.get("COMPANYNAME", "").strip() or row.get("COMPANY_NAME", "").strip()
                if not company_name: continue

                auth_cap_raw = row.get("AUTHORIZEDCAPITAL") or row.get("AUTHORIZED_CAPITAL") or "0"
                paid_cap_raw = row.get("PAIDUPCAPITAL") or row.get("PAIDUP_CAPITAL") or "0"
                try: auth_cap = int(float(auth_cap_raw))
                except: auth_cap = None
                try: paid_cap = int(float(paid_cap_raw))
                except: paid_cap = None

                state = row.get("COMPANYSTATECODE", "").strip() or row.get("STATE", "").strip() or None
                category = row.get("COMPANYCATEGORY", "").strip() or row.get("COMPANY_CATEGORY", "").strip() or None
                status = row.get("COMPANYSTATUS", "").strip() or row.get("COMPANY_STATUS", "").strip() or None
                address = row.get("REGISTERED_OFFICE_ADDRESS", "").strip() or row.get("REGISTERED_ADDRESS", "").strip() or None
                roc_code = row.get("COMPANYROCCODE", "").strip() or row.get("ROC_CODE", "").strip() or None
                
                inc_date_raw = row.get("COMPANYREGISTRATIONDATE_DATE") or row.get("DATE_OF_REGISTRATION") or row.get("DATE_OF_INCORPORATION")
                inc_date = None
                if inc_date_raw:
                    try: inc_date = datetime.strptime(inc_date_raw.strip(), "%Y-%m-%d").date()
                    except: pass
                
                mc = MatchedCompany(
                    company_name=company_name,
                    cin=cin,
                    match_score=1.0,
                    match_method="csv_seed",
                    company_status=status,
                    roc_code=roc_code,
                    company_category=category,
                    date_of_incorporation=inc_date,
                    state=state,
                    authorised_capital=auth_cap,
                    paid_up_capital=paid_cap,
                    registered_address=address,
                    is_startup=False
                )
                batch.append(mc)
                existing_cins.add(cin)

                if len(batch) >= 1000:
                    db.add_all(batch)
                    await db.commit()
                    inserted_count += len(batch)
                    batch = []
                    log.info("ingest_mca_csv_insert.progress", inserted=inserted_count)
                    # Limit to 50k for demo purposes to avoid timeout
                    if inserted_count >= 50000:
                        break

            if batch and inserted_count < 50000:
                db.add_all(batch)
                await db.commit()
                inserted_count += len(batch)

        log.info("ingest_mca_csv_insert.completed", inserted=inserted_count, skipped_duplicate=skipped_count)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <path>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
