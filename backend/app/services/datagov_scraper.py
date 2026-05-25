import asyncio
from datetime import datetime, date
from typing import AsyncGenerator, Optional
import httpx
import structlog
from app.config import settings

log = structlog.get_logger()

DATASET_RESOURCE_IDS = [
    "64dbeed7-6d8a-4fcf-a8ed-d01b8c56fd7e",
    "6548e09e-5a55-4a9a-9bd6-12d8d7d78f3c",
]


class DataGovScraper:

    async def scrape_companies(
        self,
        resource_id: str = DATASET_RESOURCE_IDS[0],
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search_query: Optional[str] = None,
        limit_per_page: int = 50,
    ) -> AsyncGenerator[dict, None]:
        offset = 0
        headers = {}
        if settings.DATAGOV_API_KEY:
            headers["api-key"] = settings.DATAGOV_API_KEY

        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            while True:
                params = {
                    "format": "json",
                    "offset": offset,
                    "limit": limit_per_page,
                }
                if settings.DATAGOV_API_KEY:
                    params["api-key"] = settings.DATAGOV_API_KEY
                if date_from:
                    params["filters[DATE_OF_REGISTRATION][from]"] = date_from.strftime("%Y-%m-%d")
                if date_to:
                    params["filters[DATE_OF_REGISTRATION][to]"] = date_to.strftime("%Y-%m-%d")
                if search_query:
                    params["filters[COMPANY_NAME]"] = search_query

                try:
                    url = f"{settings.DATAGOV_API_URL}{resource_id}"
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    log.error("datagov_scraper.fetch_error", error=str(e), offset=offset)
                    break

                records = data.get("records", [])
                if not records:
                    break

                for record in records:
                    company = self._parse_record(record)
                    if company:
                        yield company

                total = data.get("total", 0)
                offset += len(records)
                if offset >= total:
                    break

                await asyncio.sleep(0.5)

    def _parse_record(self, record: dict) -> Optional[dict]:
        name = (
            record.get("COMPANY_NAME") or
            record.get("company_name") or
            record.get("NAME") or ""
        ).strip()

        if not name:
            return None

        date_str = record.get("DATE_OF_REGISTRATION") or record.get("date_of_incorporation") or ""
        inc_date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                inc_date = datetime.strptime(date_str, fmt).date()
                break
            except Exception:
                pass

        auth_cap_raw = record.get("AUTHORIZED_CAPITAL") or "0"
        paid_cap_raw = record.get("PAIDUP_CAPITAL") or "0"
        
        try:
            auth_cap = int(float(auth_cap_raw))
        except Exception:
            auth_cap = None
            
        try:
            paid_cap = int(float(paid_cap_raw))
        except Exception:
            paid_cap = None

        return {
            "cin": (record.get("CIN") or record.get("cin") or "").strip() or None,
            "company_name": name,
            "company_status": (record.get("COMPANY_STATUS") or record.get("company_status") or "").strip() or None,
            "roc_code": (record.get("ROC_CODE") or "").strip() or None,
            "registration_number": (record.get("REG_NO") or "").strip() or None,
            "company_category": (record.get("COMPANY_CATEGORY") or "").strip() or None,
            "date_of_incorporation": inc_date,
            "state": (record.get("STATE") or "").strip() or None,
            "authorised_capital": auth_cap,
            "paid_up_capital": paid_cap,
            "raw_data": record,
        }
