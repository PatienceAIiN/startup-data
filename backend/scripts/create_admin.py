"""Create or update admin user with given credentials."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import hash_password


async def main(email: str, password: str, full_name: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        hashed = hash_password(password)
        if user:
            await db.execute(
                update(User).where(User.email == email.lower()).values(
                    hashed_password=hashed,
                    is_admin=True,
                    is_active=True,
                    full_name=full_name,
                )
            )
            await db.commit()
            print(f"[OK] Updated existing admin: {email}")
        else:
            new_user = User(
                email=email.lower(),
                hashed_password=hashed,
                full_name=full_name,
                is_admin=True,
                is_active=True,
            )
            db.add(new_user)
            await db.commit()
            print(f"[OK] Created new admin: {email}")
        print(f"     Password: {password}")
        print(f"     is_admin: True")


if __name__ == "__main__":
    asyncio.run(main("admin@startupintel.in", "Admin@110426", "Administrator"))
