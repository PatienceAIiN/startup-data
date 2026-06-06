"""Groq-LLM powered structured extraction.

Given a company name plus raw text scraped from its website and Google SERP,
ask Groq's Llama 3.3 to return a JSON object of contact + financial + business
fields. Schema is intentionally open — whatever the LLM finds is stored, so
downstream rendering can be fully dynamic.
"""
from __future__ import annotations
import asyncio
import json
import re
from typing import Optional
import structlog
from groq import AsyncGroq

from app.config import settings

log = structlog.get_logger()

# Hard caps so we don't blow the model's context or burn quota.
# 8b-instant TPM is 6000 → keep corpus around 12000 chars (~4000 tokens) plus prompt+output.
MAX_TEXT_CHARS = 12_000
MAX_OUTPUT_TOKENS = 768

SYSTEM_PROMPT = (
    "You are an information-extraction engine for Indian company records. "
    "You will be given a company name plus raw text scraped from its website "
    "and Google search results (which may include a Google AI Overview block "
    "marked '[AI OVERVIEW]'). Extract verifiable facts and return ONLY a JSON "
    "object — no prose, no markdown fences. Use null for any field you "
    "cannot confidently determine FROM THE TEXT GIVEN. Do not invent. "
    "If the source text does not mention the named company at all, return "
    "an object with all values null.\n\n"
    "Field rules:\n"
    "- cin: 21-char Corporate Identification Number (e.g. U10306MP2026PTC081800)\n"
    "- registration_date: ISO date if possible (e.g. 2026-02-03)\n"
    "- registered_address: full registered office address (include PIN)\n"
    "- authorised_capital / paid_up_capital: verbatim with currency symbol (e.g. \"₹1,500,000\")\n"
    "- directors: array of director names (Key Directors)\n"
    "- roc: ROC office (e.g. \"ROC Gwalior\")\n"
    "- phone: valid Indian (10-digit or +91…); ignore generic toll-free unless company-specific\n"
    "- email: syntactically valid; prefer @<company-domain>\n"
    "- description: 1-3 sentence company description if present\n\n"
    "Required keys (null when unknown): email, phone, address, city, state, "
    "website, linkedin, twitter, facebook, instagram, founded, "
    "registration_date, registered_address, roc, headquarters, founders, "
    "directors, ceo, employees, industry, sector, service_areas, "
    "active_years, parent, type, revenue, funding, authorised_capital, "
    "paid_up_capital, cin, gst, dipp_number, description, snippet, wikipedia.\n\n"
    "Contact-extraction priorities: "
    "- email: ONLY accept addresses that look company-owned (custom domain "
    "matching the company name, or info@/contact@/sales@ on the company "
    "domain, or a free-provider address containing the company name in the "
    "local part). Reject generic editorial / publisher emails. "
    "- phone: prefer +91 / 0xx Indian formats. Reject generic helpline / "
    "support numbers belonging to publishers or directories. "
    "- website: ONLY return the company's own official site (not a Tracxn / "
    "Zauba / InstaFinancials / Wikipedia / news article URL)."
)

_client: Optional[AsyncGroq] = None


def _get_client() -> Optional[AsyncGroq]:
    global _client
    if _client is not None:
        return _client
    if not settings.GROQ_API_KEY:
        return None
    _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _client


def _strip_html(text: str) -> str:
    # Cheap text-only view: drop scripts/styles, collapse whitespace.
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_json_payload(s: str) -> Optional[dict]:
    if not s:
        return None
    # Some models still wrap JSON in ```json fences despite instructions.
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        # Last-ditch: extract the largest {...} substring.
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
    return None


async def llm_extract(
    company_name: str,
    chunks: list[tuple[str, str]],
    timeout_s: float = 18.0,
) -> dict:
    """Call Groq with raw page chunks; return a dict of fields (may be empty).

    chunks is a list of (source_label, raw_html_or_text) — typically the
    company website body and a Google SERP capture.
    """
    client = _get_client()
    if client is None:
        return {}

    # Build a compact corpus the model can actually digest.
    parts: list[str] = []
    for label, raw in chunks:
        if not raw:
            continue
        cleaned = _strip_html(raw)
        if not cleaned:
            continue
        parts.append(f"=== {label} ===\n{cleaned}")
    corpus = "\n\n".join(parts)
    if not corpus:
        return {}
    if len(corpus) > MAX_TEXT_CHARS:
        corpus = corpus[:MAX_TEXT_CHARS]

    user_msg = f"COMPANY: {company_name}\n\nSOURCE TEXT:\n{corpus}\n\nReturn the JSON object now."

    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=MAX_OUTPUT_TOKENS,
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        log.warning("llm.timeout", company=company_name)
        return {}
    except Exception as e:
        log.warning("llm.call_failed", company=company_name, error=str(e))
        return {}

    try:
        text = resp.choices[0].message.content or ""
    except Exception:
        return {}

    obj = _clean_json_payload(text) or {}
    # Drop null/empty values so we never overwrite real data with blanks.
    cleaned = {}
    for k, v in obj.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if not v or v.lower() in {"null", "none", "n/a", "na", "unknown"}:
                continue
        cleaned[str(k).strip()] = v
    return cleaned
