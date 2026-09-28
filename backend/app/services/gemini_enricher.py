"""Gemini Flash structured extraction — same interface as llm_enricher.

Returns a JSON dict of company fields parsed from raw text chunks. Used as
the default LLM extractor when GEMINI_API_KEY is set; falls back to Groq
when it's empty.
"""
from __future__ import annotations
import asyncio
import json
import re
from typing import Optional
import httpx
import structlog

from app.config import settings

log = structlog.get_logger()

MAX_TEXT_CHARS = 18_000
MAX_OUTPUT_TOKENS = 1500
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = (
    "You are an information-extraction engine for Indian company records. "
    "You will be given a company name plus raw text from web sources "
    "(SearXNG results, crawled official pages, AI overviews). Extract "
    "verifiable facts and return ONLY a JSON object — no prose, no fences. "
    "Use null for any field you cannot confidently determine FROM THE TEXT. "
    "Do not invent. If the source text does not mention the named company, "
    "return null for every value.\n\n"
    "Required keys: company_name, legal_name, brand_name, company_type, "
    "company_status, incorporation_date, cin, llpin, gstin, dipp_number, "
    "website, email, phone, support_email, sales_email, registered_address, "
    "corporate_address, city, state, founders, directors, ceo, cto, coo, "
    "industry, sub_industry, products, services, business_model, "
    "target_market, funding_status, total_funding, investors, "
    "linkedin_url, twitter_url, instagram_url, facebook_url, youtube_url, "
    "github_url, founded, employees, revenue, authorised_capital, "
    "paid_up_capital, description, snippet, wikipedia.\n\n"
    "Field rules: CIN must be 21 chars (e.g. U10306MP2026PTC081800). "
    "Indian phone format only (+91, 0xx, or 10-digit 6-9 prefix). "
    "Capital amounts verbatim with currency symbol. Arrays of names "
    "(founders/directors/investors) as JSON arrays of strings."
)


def _strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_json(s: str) -> Optional[dict]:
    if not s:
        return None
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
    return None


async def gemini_grounded_overview(company_name: str, timeout_s: float = 18.0) -> dict:
    """Ask Gemini to research the company on Google and return a grounded
    summary. Uses the googleSearch tool which makes Gemini do its own
    Google search and cite sources — this replaces SerpAPI's AI Overview.

    Returns:
      {
        "overview": "plain text grounded answer (acts as AI Overview)",
        "sources": ["url1", "url2", ...],  # the URLs Gemini grounded on
      }
    """
    if not settings.GEMINI_API_KEY:
        return {}
    prompt = (
        f"Research the Indian company '{company_name}'. Search Google and "
        "report ONLY verified facts you find. Required structure:\n"
        "1. A one-paragraph overview.\n"
        "2. Bulleted key details — use this exact format on each bullet:\n"
        "   - Label: value\n"
        "   Required labels (skip those you cannot verify): CIN, "
        "Incorporation Date, Registered Address, ROC, Authorised Capital, "
        "Paid-up Capital, Directors, Email, Phone, Website, Industry.\n"
        "Do NOT invent values. If a fact is unverified, omit that bullet."
    )
    body = {
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1500},
    }
    url = API_URL.format(model=settings.GEMINI_MODEL)
    headers = {"Content-Type": "application/json", "X-goog-api-key": settings.GEMINI_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as c:
            r = await c.post(url, headers=headers, json=body)
    except Exception as e:
        log.warning("gemini_ground.call_failed", error=str(e))
        return {}
    if r.status_code != 200:
        log.warning("gemini_ground.bad_status", status=r.status_code, body=r.text[:200])
        return {}
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"] or ""
    except Exception:
        return {}
    sources: list[str] = []
    try:
        gm = data["candidates"][0].get("groundingMetadata", {})
        for chunk in gm.get("groundingChunks", []):
            u = (chunk.get("web") or {}).get("uri") or ""
            if u and u not in sources:
                sources.append(u)
    except Exception:
        pass
    return {"overview": text.strip(), "sources": sources}


async def gemini_extract(
    company_name: str,
    chunks: list[tuple[str, str]],
    timeout_s: float = 18.0,
) -> dict:
    """Call Gemini Flash with raw chunks; return a dict of fields (may be empty)."""
    if not settings.GEMINI_API_KEY:
        return {}

    parts: list[str] = []
    for label, raw in chunks:
        if not raw:
            continue
        cleaned = _strip_html(raw)
        if cleaned:
            parts.append(f"=== {label} ===\n{cleaned}")
    corpus = "\n\n".join(parts)
    if not corpus:
        return {}
    if len(corpus) > MAX_TEXT_CHARS:
        corpus = corpus[:MAX_TEXT_CHARS]

    user_msg = f"COMPANY: {company_name}\n\nSOURCE TEXT:\n{corpus}\n\nReturn the JSON object now."
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_msg}], "role": "user"}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "responseMimeType": "application/json",
        },
    }
    url = API_URL.format(model=settings.GEMINI_MODEL)
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": settings.GEMINI_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as c:
            r = await c.post(url, headers=headers, json=body)
    except Exception as e:
        log.warning("gemini.call_failed", company=company_name, error=str(e))
        return {}

    if r.status_code != 200:
        log.warning("gemini.bad_status", status=r.status_code, body=r.text[:200])
        return {}
    data = r.json()
    text = ""
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"] or ""
    except Exception:
        return {}

    obj = _clean_json(text) or {}
    cleaned: dict = {}
    for k, v in obj.items():
        if v is None:
            continue
        if isinstance(v, str):
            vs = v.strip()
            if not vs or vs.lower() in {"null", "none", "n/a", "na", "unknown"}:
                continue
            cleaned[str(k).strip()] = vs
        else:
            cleaned[str(k).strip()] = v
    return cleaned
