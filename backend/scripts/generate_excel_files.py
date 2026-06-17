import asyncio
import sys
import os
import re
from pathlib import Path

# Add backend root directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.startup import StartupIndiaCompany
from app.models.company import MatchedCompany
from app.services.export_service import generate_xlsx_bytes

# Regex to strip XML illegal characters
ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010\013\014\016-\037]')

def clean_for_excel(val):
    if not isinstance(val, str):
        return val
    return ILLEGAL_CHARACTERS_RE.sub("", val)

async def main():
    print("Connecting to database and reading tables...", flush=True)
    async with AsyncSessionLocal() as db:
        # 1. Fetch all StartupIndiaCompany rows
        print("Fetching startups data...", flush=True)
        startup_rows = (await db.execute(select(StartupIndiaCompany))).scalars().all()
        
        # 2. Fetch all MatchedCompany rows
        print("Fetching companies data...", flush=True)
        # Using join for matching details if mirror exists
        sih_profile = func.substr(MatchedCompany.cin, 5)
        query = (
            select(
                MatchedCompany,
                StartupIndiaCompany.city.label("si_city"),
                StartupIndiaCompany.contact_email.label("si_email"),
                StartupIndiaCompany.contact_phone.label("si_phone"),
                StartupIndiaCompany.dpiit_recognised.label("si_dpiit"),
                StartupIndiaCompany.dipp_number.label("si_dipp"),
            )
            .outerjoin(
                StartupIndiaCompany,
                StartupIndiaCompany.profile_id == sih_profile,
            )
            .order_by(MatchedCompany.date_of_incorporation.desc().nulls_last())
        )
        company_rows = (await db.execute(query)).all()

    print(f"Loaded {len(startup_rows)} startups and {len(company_rows)} companies. Formatting datasets...", flush=True)

    # Format Startups
    startup_dicts = []
    for s in startup_rows:
        extras = s.extras or {}
        startup_dicts.append({
            k: clean_for_excel(v) for k, v in {
                "cin": s.cin_real or extras.get("cin"),
                "company_name": s.company_name,
                "company_status": extras.get("status", "Active"),
                "roc_code": extras.get("roc_code"),
                "company_category": extras.get("category"),
                "date_of_incorporation": extras.get("date_of_incorporation"),
                "state": s.state,
                "city": s.city,
                "authorised_capital": extras.get("authorised_capital"),
                "paid_up_capital": extras.get("paid_up_capital"),
                "match_score": 1.0,
                "match_method": "startup_india",
                "is_startup": True,
                "dpiit_recognised": s.dpiit_recognised,
                "dipp_number": s.dipp_number,
                "contact_email": s.contact_email,
                "contact_phone": s.contact_phone,
                "registered_address": s.contact_address,
            }.items()
        })

    # Format Companies
    company_dicts = []
    for row in company_rows:
        c, si_city, si_email, si_phone, si_dpiit, si_dipp = row
        company_dicts.append({
            k: clean_for_excel(v) for k, v in {
                "cin": c.cin,
                "company_name": c.company_name,
                "company_status": c.company_status,
                "roc_code": c.roc_code,
                "company_category": c.company_category,
                "date_of_incorporation": c.date_of_incorporation,
                "state": c.state,
                "city": si_city or c.state,
                "authorised_capital": c.authorised_capital,
                "paid_up_capital": c.paid_up_capital,
                "match_score": c.match_score,
                "match_method": c.match_method,
                "is_startup": c.is_startup,
                "registered_address": c.registered_address,
                "contact_email": si_email or c.contact_email,
                "contact_phone": si_phone or c.contact_phone,
                "dpiit_recognised": bool(si_dpiit) if si_dpiit is not None else False,
                "dipp_number": si_dipp,
            }.items()
        })

    print("Generating startup Excel spreadsheet bytes...", flush=True)
    startup_xlsx = generate_xlsx_bytes(startup_dicts, sheet_title="Enriched Startups")
    
    print("Generating company Excel spreadsheet bytes...", flush=True)
    company_xlsx = generate_xlsx_bytes(company_dicts, sheet_title="Enriched Companies")

    # Save files to workspace root
    workspace_root = Path("/app")
    startup_path = workspace_root / "enriched_startups.xlsx"
    company_path = workspace_root / "enriched_companies.xlsx"

    print(f"Writing startups spreadsheet to {startup_path}...", flush=True)
    with open(startup_path, "wb") as f:
        f.write(startup_xlsx)

    print(f"Writing companies spreadsheet to {company_path}...", flush=True)
    with open(company_path, "wb") as f:
        f.write(company_xlsx)

    print("Spreadsheets generated successfully in workspace root!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
