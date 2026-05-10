from datetime import date
from typing import Optional
from app.services.zauba_scraper import ZaubaScraper
from app.services.datagov_scraper import DataGovScraper
from app.services.matcher_service import batch_match
import structlog

log = structlog.get_logger()


async def run_scrape_and_match(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    max_zauba_pages: int = 10,
) -> dict:
    zauba_scraper = ZaubaScraper()
    zauba_records = []
    async for company in zauba_scraper.scrape_companies(pages=max_zauba_pages, date_from=date_from, date_to=date_to):
        zauba_records.append(company)

    dg_scraper = DataGovScraper()
    dg_records = []
    async for company in dg_scraper.scrape_companies(date_from=date_from, date_to=date_to):
        dg_records.append(company)

    matches = batch_match(zauba_records, dg_records)
    log.info("scrape_match_complete", zauba=len(zauba_records), datagov=len(dg_records), matches=len(matches))

    return {
        "zauba_records": zauba_records,
        "datagov_records": dg_records,
        "matches": matches,
    }
