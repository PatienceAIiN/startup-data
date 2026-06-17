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
        await db.execute(text("ALTER TABLE matched_companies ADD COLUMN IF NOT EXISTS contact_email VARCHAR(200);"))
        await db.execute(text("ALTER TABLE matched_companies ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(100);"))
        await db.execute(text("ALTER TABLE matched_companies ADD COLUMN IF NOT EXISTS contact_enriched_at TIMESTAMP WITH TIME ZONE;"))
        await db.commit()
        print("Successfully added columns to matched_companies table!")

asyncio.run(db_run())
