"""Promote a user to admin by email."""
import asyncio
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import update, select
from app.database import AsyncSessionLocal
from app.models.user import User


async def main(email: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌ User {email} not found")
            return
        await db.execute(
            update(User).where(User.email == email.lower()).values(is_admin=True)
        )
        await db.commit()
        print(f"✅ {email} is now admin")


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "growth@patienceai.in"
    asyncio.run(main(email))
