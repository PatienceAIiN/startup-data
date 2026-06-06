"""
StartupIndia scraper.

Loads https://www.startupindia.gov.in/content/sih/en/search.html?roles=Startup&page=N
in a real Chromium browser (Playwright) and intercepts the XHR JSON response from
api.startupindiahub.org.in's /sih/api/noauth/search/profile endpoint.

Why through a browser: the API is behind CloudFront + bot/WAF rules that reject
direct curl/httpx requests. The SPA loads it cleanly with proper headers + TLS
fingerprint, so we ride along.
"""
import asyncio
import json
from typing import AsyncGenerator, Optional
import structlog
from playwright.async_api import async_playwright, Response

log = structlog.get_logger()

SEARCH_URL = "https://www.startupindia.gov.in/content/sih/en/search.html?roles=Startup&page={page}"
SEARCH_QUERY_URL = "https://www.startupindia.gov.in/content/sih/en/search.html?roles=Startup&page=0&query={q}"
API_PATH_HINT = "/search/profile"


# ---- shared browser pool ----------------------------------------------------
# Live search is interactive; cold-launching Chromium every call costs ~12s.
# Keep one browser + one warm context across requests.

_pw = None
_browser = None
_context = None
_warm_page = None
_pool_lock = asyncio.Lock()


async def _get_warm_page():
    """Return a long-lived Page sitting on startupindia.gov.in. Live searches
    do their fetches via page.evaluate so they ride the SPA's CORS-allowed,
    WAF-blessed origin."""
    global _pw, _browser, _context, _warm_page
    async with _pool_lock:
        if _warm_page is not None and _browser and _browser.is_connected():
            try:
                # Cheap liveness probe — querying url() throws if page is closed.
                _ = _warm_page.url
                return _warm_page
            except Exception:
                _warm_page = None

        if _pw is None:
            _pw = await async_playwright().start()
        if _browser is None or not _browser.is_connected():
            _browser = await _pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            _context = await _browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 900},
                locale="en-IN",
                extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            )

        _warm_page = await _context.new_page()
        try:
            await _warm_page.goto(
                SEARCH_URL.format(page=0),
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            await asyncio.sleep(2.0)
        except Exception as e:
            log.warning("startupindia.warm_failed", error=str(e))
        return _warm_page


class StartupIndiaScraper:
    """Scrapes startupindia.gov.in listings page-by-page."""

    def __init__(self, page_size: int = 50, nav_timeout_ms: int = 45_000, settle_seconds: float = 6.0):
        self.page_size = page_size
        self.nav_timeout_ms = nav_timeout_ms
        self.settle_seconds = settle_seconds

    async def scrape_by_query(self, query: str) -> list[dict]:
        """Live search by name. Fires the search POST from inside a warm page
        on startupindia.gov.in so the request shares the SPA's origin, cookies,
        and any WAF tokens."""
        captured: list[dict] = []
        ql = (query or "").strip().lower()

        page = await _get_warm_page()
        try:
            body = await page.evaluate(
                """
                async ({q, size}) => {
                    const hosts = [
                        'https://api.startupindia.gov.in/sih/api/noauth/search/profiles',
                        'https://api.startupindiahub.org.in/sih/api/noauth/search/profiles',
                    ];
                    // Exact payload shape used by startupindia.gov.in's own SPA.
                    const payload = {
                        query: q,
                        focusSector: false,
                        industries: [], sectors: [], states: [], cities: [], stages: [], badges: [],
                        roles: ['Startup'],
                        page: 0,
                        sort: {orders: [{field: 'registeredOn', direction: 'DESC'}]},
                        dpiitRecogniseUser: true,
                        internationalUser: false,
                    };
                    const tryHost = (base) => {
                        const ctrl = new AbortController();
                        const to = setTimeout(() => ctrl.abort(), 7000);
                        return fetch(`${base}?page=0&size=${size}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(payload),
                            credentials: 'include',
                            signal: ctrl.signal,
                        }).then(async r => {
                            clearTimeout(to);
                            if (!r.ok) throw new Error('status ' + r.status);
                            const b = await r.json();
                            return {host: base, body: b};
                        });
                    };
                    try {
                        return await Promise.any(hosts.map(tryHost));
                    } catch (e) {
                        return null;
                    }
                }
                """,
                {"q": query.strip(), "size": self.page_size},
            )
        except Exception as e:
            log.warning("startupindia.query_eval_failed", error=str(e))
            body = None

        if body is None:
            log.warning("startupindia.query_no_response", q=query)
        else:
            items = self._extract_items(body.get("body"))
            log.info("startupindia.query_api_ok", host=body.get("host"), count=len(items))
            captured.extend(items)

        normalized: list[dict] = []
        seen = set()
        for raw in captured[: self.page_size]:
            norm = self._normalize(raw)
            if not norm:
                continue
            pid = norm.get("profile_id")
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            normalized.append(norm)
        if ql:
            filtered = [n for n in normalized if ql in (n["company_name"] or "").lower()]
            if filtered:
                normalized = filtered
        return normalized[: self.page_size]

    async def _scrape_by_query_legacy(self, query: str) -> list[dict]:
        """Legacy fresh-browser path (kept for reference). Not used."""
        captured: list[dict] = []
        ql = (query or "").strip().lower()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1366, "height": 900},
                    locale="en-IN",
                    extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
                )
                page = await context.new_page()
                try:
                    await page.goto(
                        SEARCH_URL.format(page=0),
                        wait_until="commit",
                        timeout=self.nav_timeout_ms,
                    )
                except Exception as e:
                    log.warning("startupindia.query_goto_failed", error=str(e))

                # Brief settle — enough for the SPA to set its session cookies.
                await asyncio.sleep(1.0)

                hosts = [
                    "https://api.startupindiahub.org.in/sih/api/noauth/search/profile",
                    "https://api.startupindia.gov.in/sih/api/noauth/search/profile",
                ]
                payload = {
                    "query": query.strip(),
                    "focusSector": False, "sector": [], "industry": [],
                    "state": [], "stage": [], "roles": ["Startup"],
                    "badges": [], "city": [],
                    "internationalUser": False, "dpiitRecogniseUser": False,
                }
                for base in hosts:
                    try:
                        resp = await context.request.post(
                            f"{base}?page=0&size={self.page_size}",
                            data=payload,
                            headers={
                                "Content-Type": "application/json",
                                "Origin": "https://www.startupindia.gov.in",
                                "Referer": "https://www.startupindia.gov.in/",
                            },
                            timeout=20_000,
                        )
                        status = resp.status
                        if not resp.ok:
                            log.warning("startupindia.query_api_bad_status", host=base, status=status)
                            continue
                        body = await resp.json()
                        items = self._extract_items(body)
                        if items:
                            captured.extend(items)
                            log.info("startupindia.query_api_ok", host=base, count=len(items))
                            break
                    except Exception as e:
                        log.warning("startupindia.query_api_failed", host=base, error=str(e))

            finally:
                await browser.close()

        source = captured

        normalized: list[dict] = []
        seen = set()
        ql = query.strip().lower()
        for raw in source[: self.page_size * 2]:
            norm = self._normalize(raw)
            if not norm:
                continue
            pid = norm.get("profile_id")
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            normalized.append(norm)

        # Filter to name-matches only (the API sometimes returns broader results).
        if ql:
            filtered = [n for n in normalized if ql in (n["company_name"] or "").lower()]
            if filtered:
                normalized = filtered
        return normalized[: self.page_size]

    async def scrape_page(self, page_index: int) -> list[dict]:
        """Returns up to page_size startup dicts from the given page index (0-based)."""
        url = SEARCH_URL.format(page=page_index)
        return await self._scrape_url(url)

    async def _scrape_url(self, url: str) -> list[dict]:
        captured: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1366, "height": 900},
                    locale="en-IN",
                    extra_http_headers={
                        "Accept-Language": "en-IN,en;q=0.9",
                    },
                )
                page = await context.new_page()

                async def on_response(resp: Response) -> None:
                    try:
                        if API_PATH_HINT not in resp.url:
                            return
                        ct = (resp.headers.get("content-type") or "").lower()
                        if "json" not in ct:
                            return
                        body = await resp.json()
                        items = self._extract_items(body)
                        if items:
                            captured.extend(items)
                    except Exception as e:
                        log.warning("startupindia.response_parse_failed", url=resp.url, error=str(e))

                page.on("response", on_response)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.nav_timeout_ms)
                except Exception as e:
                    log.warning("startupindia.goto_failed", page=page_index, error=str(e))

                # Give SPA time to fire its XHR
                await asyncio.sleep(self.settle_seconds)

                # As a fallback, try to read cards from DOM if no XHR fired
                if not captured:
                    captured.extend(await self._extract_cards_from_dom(page))

            finally:
                await browser.close()

        normalized: list[dict] = []
        seen = set()
        for raw in captured[: self.page_size]:
            norm = self._normalize(raw)
            if not norm:
                continue
            pid = norm.get("profile_id")
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            normalized.append(norm)
        return normalized

    async def scrape_pages(self, start_page: int, max_pages: int, hard_cap: int) -> AsyncGenerator[dict, None]:
        emitted = 0
        for offset in range(max_pages):
            if emitted >= hard_cap:
                return
            items = await self.scrape_page(start_page + offset)
            if not items:
                return
            for it in items:
                yield it
                emitted += 1
                if emitted >= hard_cap:
                    return

    # ---- parsing helpers ---------------------------------------------------

    @staticmethod
    def _extract_items(body) -> list[dict]:
        """The API wraps results in different envelopes across versions.
        Walk a few common keys."""
        if not body:
            return []
        if isinstance(body, list):
            return [x for x in body if isinstance(x, dict)]
        if isinstance(body, dict):
            for key in ("content", "data", "results", "profiles", "items"):
                v = body.get(key)
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
                if isinstance(v, dict):
                    for sub in ("content", "data", "results", "items"):
                        sv = v.get(sub)
                        if isinstance(sv, list):
                            return [x for x in sv if isinstance(x, dict)]
        return []

    @staticmethod
    def _first(d: dict, *keys, default=None):
        for k in keys:
            v = d.get(k)
            if v not in (None, "", []):
                return v
        return default

    def _normalize(self, raw: dict) -> Optional[dict]:
        if not isinstance(raw, dict):
            return None
        name = self._first(raw, "companyName", "name", "title", "fullName")
        if not name:
            return None
        profile_id = self._first(raw, "profileId", "id", "uid", "slug", "profileSlug")
        if not profile_id:
            return None
        profile_id = str(profile_id)

        # Industry/sector/stage live in plural arrays on the listing payload
        def _join_arr(*keys):
            for k in keys:
                v = raw.get(k)
                if isinstance(v, list) and v:
                    return ", ".join(str(x).strip() for x in v if x)
            return None
        industry = _join_arr("industries") or self._first(raw, "industry", "industryName", "industryDisplay")
        sector = _join_arr("sectors") or self._first(raw, "sector", "sectorName", "sectorDisplay")
        stage = _join_arr("stages") or self._first(raw, "stage", "stageName", "stageOfDevelopment")
        state = self._first(raw, "state", "stateName")
        city = self._first(raw, "city", "cityName")
        website = self._first(raw, "website", "websiteUrl", "url")
        logo_url = self._first(raw, "logo", "logoUrl", "image", "imageUrl")
        description = self._first(raw, "description", "shortDescription", "about", "summary")

        badges = self._first(raw, "badges", "badgeList", default=[])
        if isinstance(badges, str):
            badges = [badges]
        if not isinstance(badges, list):
            badges = []

        # DPIIT recognition: the listing payload carries an explicit status
        # field. Only the literal "RECOGNISED" counts; other states (APPLIED,
        # PENDING, DEFERRED, REJECTED, …) must NOT show the tick.
        import re as _re
        recognition_status = str(raw.get("dippRecognitionStatus") or "").strip().upper()
        dipp_certified = bool(raw.get("dippCertified"))
        raw_dipp = self._first(raw, "dippNumber", "dipp_number", "dpiitRecognitionNumber")
        dipp_number = None
        if raw_dipp and _re.match(r"^DIPP\d{4,8}$", str(raw_dipp).strip(), _re.IGNORECASE):
            dipp_number = str(raw_dipp).strip().upper()
        dpiit = recognition_status == "RECOGNISED" and dipp_certified and bool(dipp_number)

        profile_url = None
        if isinstance(profile_id, str) and profile_id:
            profile_url = f"https://www.startupindia.gov.in/content/sih/en/profile.html?profileId={profile_id}"

        return {
            "profile_id": profile_id,
            "profile_url": profile_url,
            "company_name": str(name).strip(),
            "description": (str(description).strip() if description else None),
            "industry": (str(industry).strip() if industry else None),
            "sector": (str(sector).strip() if sector else None),
            "stage": (str(stage).strip() if stage else None),
            "state": (str(state).strip() if state else None),
            "city": (str(city).strip() if city else None),
            "website": (str(website).strip() if website else None),
            "logo_url": (str(logo_url).strip() if logo_url else None),
            "badges": badges,
            "dpiit_recognised": dpiit,
            "dipp_number": (str(dipp_number) if dipp_number else None),
            "raw": raw,
        }

    async def _extract_cards_from_dom(self, page) -> list[dict]:
        """Fallback parser if no XHR was captured."""
        try:
            cards = await page.query_selector_all("div.tile, div.searchTile, article.tile, div.card")
            out: list[dict] = []
            for card in cards[: self.page_size]:
                try:
                    name_el = await card.query_selector("h3, h2, a.name, .title")
                    if not name_el:
                        continue
                    name = (await name_el.inner_text()).strip()
                    if not name:
                        continue
                    href = None
                    link = await card.query_selector("a")
                    if link:
                        href = await link.get_attribute("href")
                    pid = href.split("profileId=")[-1] if href and "profileId=" in href else name.lower().replace(" ", "-")
                    out.append({"name": name, "profileId": pid, "_dom_fallback": True})
                except Exception:
                    continue
            return out
        except Exception as e:
            log.warning("startupindia.dom_fallback_failed", error=str(e))
            return []
