"""Cerebras Llama 3.3 structured extraction. OpenAI-compatible API.
Free tier: 1M tokens/day. Same interface as llm_enricher / gemini_enricher."""
from __future__ import annotations
import asyncio, json, re
from typing import Optional
import httpx, structlog
from app.config import settings

log = structlog.get_logger()
API_URL = "https://api.cerebras.ai/v1/chat/completions"
MAX_TEXT_CHARS = 14_000
MAX_OUTPUT_TOKENS = 1500

SYSTEM_PROMPT = (
    "You are an information-extraction engine for Indian company records. "
    "Extract verifiable facts from the source text and return ONLY a JSON "
    "object — no prose, no fences. Use null for any field you cannot "
    "confidently determine from the text. Do NOT invent. If the source "
    "does not mention the named company at all, return null for every value.\n\n"
    "Required keys: company_name, legal_name, brand_name, company_type, "
    "company_status, incorporation_date, cin, llpin, gstin, dipp_number, "
    "website, email, phone, support_email, sales_email, registered_address, "
    "corporate_address, city, state, founders, directors, ceo, cto, coo, "
    "industry, sub_industry, products, services, business_model, "
    "target_market, funding_status, total_funding, investors, "
    "linkedin_url, twitter_url, instagram_url, facebook_url, youtube_url, "
    "github_url, founded, employees, revenue, authorised_capital, "
    "paid_up_capital, description, snippet, wikipedia.\n\n"
    "CIN is 21 chars (e.g. U10306MP2026PTC081800). Indian phone format only. "
    "Capital amounts verbatim with currency. Director/investor names as JSON arrays."
)


def _strip_html(t: str) -> str:
    t = re.sub(r"<script[\s\S]*?</script>", " ", t, flags=re.I)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _clean_json(s: str) -> Optional[dict]:
    if not s: return None
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.I).strip()
    try:
        o = json.loads(s); return o if isinstance(o, dict) else None
    except Exception:
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                o = json.loads(m.group(0)); return o if isinstance(o, dict) else None
            except Exception: return None
    return None


async def cerebras_extract(company_name: str, chunks: list[tuple[str, str]],
                            timeout_s: float = 15.0) -> dict:
    if not settings.CEREBRAS_API_KEY: return {}
    parts: list[str] = []
    for label, raw in chunks:
        if not raw: continue
        c = _strip_html(raw)
        if c: parts.append(f"=== {label} ===\n{c}")
    corpus = "\n\n".join(parts)
    if not corpus: return {}
    if len(corpus) > MAX_TEXT_CHARS: corpus = corpus[:MAX_TEXT_CHARS]
    user_msg = f"COMPANY: {company_name}\n\nSOURCE TEXT:\n{corpus}\n\nReturn the JSON object now."
    body = {
        "model": settings.CEREBRAS_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    headers = {"Authorization": f"Bearer {settings.CEREBRAS_API_KEY}",
               "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as c:
            r = await c.post(API_URL, headers=headers, json=body)
    except Exception as e:
        log.warning("cerebras.call_failed", error=str(e)); return {}
    if r.status_code != 200:
        log.warning("cerebras.bad_status", status=r.status_code, body=r.text[:200]); return {}
    data = r.json()
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except Exception: return {}
    obj = _clean_json(text) or {}
    out: dict = {}
    for k, v in obj.items():
        if v is None: continue
        if isinstance(v, str):
            vs = v.strip()
            if not vs or vs.lower() in {"null","none","n/a","na","unknown"}: continue
            out[str(k).strip()] = vs
        else:
            out[str(k).strip()] = v
    return out
