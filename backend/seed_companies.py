import asyncio
import random
from datetime import date, timedelta
from app.database import AsyncSessionLocal
from app.models.company import MatchedCompany
from faker import Faker

fake = Faker('en_IN')

CATEGORIES = [
    "Company limited by Shares",
    "Company Limited by Guarantee",
    "Unlimited Company"
]

STATES = [
    "Maharashtra", "Karnataka", "Delhi", "Telangana", "Tamil Nadu",
    "Gujarat", "Uttar Pradesh", "West Bengal", "Haryana", "Rajasthan"
]

STATUSES = ["Active", "Active", "Active", "Active", "Active", "Strike Off", "Amalgamated"]

async def main():
    async with AsyncSessionLocal() as db:
        print("Starting seeding process...")
        companies = []
        for i in range(500):
            # Generate random realistic data
            inc_date = date.today() - timedelta(days=random.randint(10, 3650))
            is_startup = (date.today() - inc_date).days <= 3650
            auth_cap = random.choice([100000, 500000, 1000000, 5000000, 10000000, 50000000, 100000000])
            paid_cap = int(auth_cap * random.uniform(0.1, 1.0))
            
            mc = MatchedCompany(
                company_name=f"{fake.company()} PRIVATE LIMITED".upper(),
                cin=f"U72900{random.choice(['MH','KA','DL','TG','TN'])}{inc_date.year}PTC{random.randint(100000, 999999)}",
                match_score=random.uniform(0.8, 1.0),
                match_method="synthetic_seed",
                company_status=random.choice(STATUSES),
                roc_code=f"RoC-{random.choice(['Mumbai', 'Bangalore', 'Delhi', 'Hyderabad', 'Chennai'])}",
                company_category=random.choice(CATEGORIES),
                date_of_incorporation=inc_date,
                state=random.choice(STATES),
                authorised_capital=auth_cap,
                paid_up_capital=paid_cap,
                registered_address=fake.address().replace("\n", ", "),
                is_startup=is_startup,
                incorporation_year=inc_date.year,
            )
            db.add(mc)
        
        await db.commit()
        print("Successfully seeded 500 companies into the database!")

if __name__ == "__main__":
    asyncio.run(main())
