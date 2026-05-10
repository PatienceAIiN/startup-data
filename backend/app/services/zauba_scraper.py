import asyncio
from datetime import datetime, date
from typing import AsyncGenerator, Optional
import structlog
from playwright.async_api import async_playwright
from app.config import settings

log = structlog.get_logger()


class ZaubaScraper:
    BASE_URL = settings.ZAUBA_BASE_URL

    async def scrape_companies(
        self,
        pages: int = settings.SCRAPE_MAX_PAGES,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> AsyncGenerator[dict, None]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                extra_http_headers={
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
            page = await context.new_page()

            try:
                current_page = 1
                while current_page <= pages:
                    url = f"{self.BASE_URL}/p-{current_page}"
                    if date_from:
                        url += f"/date-{date_from.strftime('%d-%m-%Y')}"

                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(2)
                    except Exception as e:
                        log.warning("zauba_scraper.page_load_error", page=current_page, error=str(e))
                        break

                    rows = await page.query_selector_all("table.table tbody tr")
                    if not rows:
                        log.info("zauba_scraper.no_rows", page=current_page)
                        break

                    for row in rows:
                        try:
                            company = await self._extract_row(row)
                            if company:
                                if date_from and company.get("date_of_incorporation"):
                                    if company["date_of_incorporation"] < date_from:
                                        continue
                                if date_to and company.get("date_of_incorporation"):
                                    if company["date_of_incorporation"] > date_to:
                                        continue
                                yield company
                        except Exception as e:
                            log.warning("zauba_scraper.row_error", error=str(e))

                    next_btn = await page.query_selector("a[aria-label='Next']")
                    if not next_btn:
                        break

                    current_page += 1
                    await asyncio.sleep(1.5)

            finally:
                await browser.close()

    async def _extract_row(self, row) -> Optional[dict]:
        cells = await row.query_selector_all("td")
        if len(cells) < 4:
            return None

        cin_text = await cells[0].inner_text() if len(cells) > 0 else ""
        name_el = await row.query_selector("td:nth-child(2) a")
        name_text = await name_el.inner_text() if name_el else (await cells[1].inner_text() if len(cells) > 1 else "")
        status_text = await cells[2].inner_text() if len(cells) > 2 else ""
        roc_text = await cells[3].inner_text() if len(cells) > 3 else ""
        date_text = await cells[4].inner_text() if len(cells) > 4 else ""

        inc_date = None
        try:
            date_text_clean = date_text.strip()
            if date_text_clean and date_text_clean != "-":
                inc_date = datetime.strptime(date_text_clean, "%d %b %Y").date()
        except Exception:
            pass

        company_name = name_text.strip()
        if not company_name:
            return None

        return {
            "cin": cin_text.strip() or None,
            "company_name": company_name,
            "company_status": status_text.strip() or None,
            "roc_code": roc_text.strip() or None,
            "date_of_incorporation": inc_date,
            "scraped_at": datetime.utcnow(),
        }
