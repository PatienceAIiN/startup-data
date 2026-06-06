"""Self-hosted SearXNG meta-search client.

Drop-in replacement for SerpAPI/Tavily. Returns a list of {title, url,
snippet} dicts. Backend service URL comes from settings.SEARXNG_URL.
"""
from __future__ import annotations
from typing import Optional
import httpx
import structlog

from app.config import settings

log = structlog.get_logger()


async def searxng_search(client: httpx.AsyncClient, query: str, *,
                          categories: str = "general",
                          max_results: int = 10) -> list[dict]:
    """Hit the configured SearXNG instance and return a list of result dicts."""
    base = (settings.SEARXNG_URL or "").rstrip("/")
    if not base:
        return []
    try:
        r = await client.get(
            f"{base}/search",
            params={"q": query, "format": "json", "categories": categories,
                    "safesearch": "0", "language": "en-IN"},
            timeout=12.0,
        )
    except Exception as e:
        log.warning("searxng.request_failed", error=str(e))
        return []
    if r.status_code != 200:
        log.warning("searxng.bad_status", status=r.status_code)
        return []
    try:
        data = r.json()
    except Exception:
        return []
    out: list[dict] = []
    for res in (data.get("results") or [])[:max_results]:
        url = res.get("url") or ""
        title = res.get("title") or ""
        content = res.get("content") or ""
        if url:
            out.append({"title": title, "url": url, "snippet": content})
    return out


async def fetch_page(client: httpx.AsyncClient, url: str, timeout_s: float = 6.0) -> Optional[str]:
    """Crawl4AI-equivalent: fetch URL via httpx and return raw HTML.
    Heavy JS sites would need Playwright; for company sites this is enough."""
    try:
        r = await client.get(url, timeout=timeout_s, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NexusIntel/1.0; +https://nexuscompany.patienceai.in)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en",
        })
        if r.status_code < 400 and r.text:
            return r.text
    except Exception as e:
        log.warning("crawl.fetch_failed", url=url, error=str(e))
    return None
