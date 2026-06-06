"""Fast synchronous enricher used for the click-to-popup path.

Goals (in order):
  1. Latency budget: < 8 s end-to-end.
  2. Zero Playwright. All HTTP via httpx for predictable timing.
  3. Every populated field MUST be verifiable in the source text the LLM
     was given. Narrative fields (description/snippet) are allowed through
     because the LLM is asked to summarize.
"""
from __future__ import annotations
import asyncio
import re
import urllib.parse
from typing import Optional
import httpx
import structlog

from app.services.llm_enricher import llm_extract

log = structlog.get_logger()

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# Fields the LLM is permitted to produce free-form text for. Everything else
# must be substring-verifiable in the source corpus.
NARRATIVE_KEYS = {"description", "snippet", "industry", "sector", "type",
                  "headquarters", "city", "state"}

# Scalar contact fields we promote to the top-level enrichment result.
CONTACT_KEYS = ("email", "phone", "address", "linkedin", "twitter",
                "facebook", "instagram", "cin", "gst", "website")


def _name_tokens(name: str) -> list[str]:
    toks = [t.lower() for t in re.split(r"[^A-Za-z0-9]+", name) if t]
    stop = {"private", "limited", "pvt", "ltd", "company", "co", "india",
            "the", "inc", "llc", "llp", "corporation", "corp"}
    return [t for t in toks if len(t) >= 4 and t not in stop]


def _has_name(text: str, name: str) -> bool:
    toks = _name_tokens(name)
    if not toks:
        return True
    hay = text.lower()
    hits = sum(1 for t in toks if t in hay)
    return hits >= max(1, (len(toks) + 1) // 2)


async def _fetch_ddg(client: httpx.AsyncClient, query: str) -> Optional[str]:
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        r = await client.get(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
        })
        if r.status_code in (200, 202) and r.text:
            # Detect DDG CAPTCHA challenge — body mentions challenge text.
            if "Please complete the following challenge" in r.text or "Unfortunately, bots use DuckDuckGo too" in r.text:
                return None
            return r.text
    except Exception as e:
        log.warning("fast.ddg_failed", q=query, error=str(e))
    return None


async def _fetch_bing(client: httpx.AsyncClient, query: str) -> Optional[str]:
    """Bing HTML search — different rate-limit policy from DDG."""
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&cc=in"
        r = await client.get(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
        })
        if r.status_code == 200 and r.text and len(r.text) > 5000:
            # Detect Bing's bot-challenge interstitial.
            if "One last step" in r.text or "Please solve the challenge" in r.text:
                return None
            return r.text
    except Exception as e:
        log.warning("fast.bing_failed", error=str(e))
    return None


def _ai_overview_text(ao: dict) -> str:
    """Flatten SerpAPI's google_ai_overview response into plain text.
    Handles paragraph, list (incl. nested), heading, and expandable blocks."""
    if not isinstance(ao, dict):
        return ""
    out: list[str] = []

    def walk(blocks):
        for block in (blocks or []):
            if not isinstance(block, dict):
                continue
            t = block.get("type")
            if t in ("paragraph", "heading"):
                s = block.get("snippet") or ""
                if s: out.append(s if t == "paragraph" else f"\n## {s}")
            elif t == "list":
                for it in (block.get("list") or []):
                    title = it.get("title") or ""
                    snip = it.get("snippet") or ""
                    if title and snip: out.append(f"- {title}: {snip}")
                    elif snip: out.append(f"- {snip}")
                    elif title: out.append(f"- {title}")
            elif t == "expandable":
                walk(block.get("text_blocks") or [])
            elif "snippet" in block:
                s = block.get("snippet") or ""
                if s: out.append(s)
    walk(ao.get("text_blocks") or [])
    return "\n".join(out).strip()


# Module-level capture of the most recent SerpAPI organic-result URLs so the
# enricher can pick a candidate company website from them.
_LAST_SERP_ORGANIC: list[str] = []


async def _fetch_serpapi(client: httpx.AsyncClient, query: str) -> Optional[str]:
    """SerpAPI — returns Google SERP including AI Overview, knowledge graph,
    organic snippets. Requires SERPAPI_KEY."""
    from app.config import settings
    key = getattr(settings, "SERPAPI_KEY", "") or ""
    if not key:
        return None
    try:
        # AI Overview triggers more reliably on short, question-shaped queries.
        # Try the supplied query, then progressively shorter retries.
        toks = query.split()
        candidate_queries = [query]
        if len(toks) > 4:
            candidate_queries.append(" ".join(toks[:4]) + " CIN")
            candidate_queries.append(" ".join(toks[:4]))

        data = None
        ao_text = ""
        for q in candidate_queries:
            r = await client.get(
                "https://serpapi.com/search.json",
                params={"engine": "google", "q": q, "api_key": key,
                        "hl": "en", "gl": "in",
                        "location": "New Delhi, Delhi, India",
                        "num": "8"},
                timeout=10.0,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            ao = data.get("ai_overview") or {}
            ao_text = _ai_overview_text(ao)
            if not ao_text and isinstance(ao, dict) and ao.get("page_token"):
                try:
                    r2 = await client.get(
                        "https://serpapi.com/search.json",
                        params={"engine": "google_ai_overview",
                                "page_token": ao["page_token"], "api_key": key},
                        timeout=10.0,
                    )
                    if r2.status_code == 200:
                        ao_text = _ai_overview_text(r2.json().get("ai_overview") or {})
                except Exception as e:
                    log.warning("fast.ai_overview_followup_failed", error=str(e))
            if ao_text:
                break  # stop burning credits once we have the AI Overview

        if data is None:
            return None
        parts: list[str] = []
        if ao_text:
            parts.append(f"[GOOGLE AI OVERVIEW]\n{ao_text}")
        if data.get("answer_box"):
            ab = data["answer_box"]
            parts.append("[ANSWER BOX]\n" + (ab.get("answer") or ab.get("snippet") or str(ab)))
        if data.get("knowledge_graph"):
            kg = data["knowledge_graph"]
            kg_lines = []
            for k, v in kg.items():
                if isinstance(v, (str, int, float, bool)):
                    kg_lines.append(f"{k}: {v}")
            if kg_lines:
                parts.append("[KNOWLEDGE GRAPH]\n" + "\n".join(kg_lines))
        # capture organic URLs for the website-picker (excluding directories).
        global _LAST_SERP_ORGANIC
        _LAST_SERP_ORGANIC = []
        for res in data.get("organic_results", [])[:8]:
            link = res.get("link", "")
            if link and not any(h in link.lower() for h in DIRECTORY_HOSTS):
                _LAST_SERP_ORGANIC.append(link)
        for res in data.get("organic_results", [])[:8]:
            title = res.get("title", "")
            snippet = res.get("snippet", "")
            link = res.get("link", "")
            if snippet:
                parts.append(f"[{title} | {link}]\n{snippet}")
        return "\n\n".join(parts) if parts else None
    except Exception as e:
        log.warning("fast.serpapi_failed", error=str(e))
    return None


async def _fetch_tavily(client: httpx.AsyncClient, query: str) -> Optional[str]:
    """Tavily AI search API — production-grade. Requires TAVILY_API_KEY.
    Free tier: 1000 searches/month. Returns concise, LLM-ready text."""
    from app.config import settings
    key = getattr(settings, "TAVILY_API_KEY", "") or ""
    if not key:
        return None
    try:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "max_results": 6,
            },
            timeout=8.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        parts: list[str] = []
        if data.get("answer"):
            parts.append(f"[TAVILY ANSWER]\n{data['answer']}")
        for res in data.get("results", []):
            title = res.get("title", "")
            content = res.get("content", "")
            if content:
                parts.append(f"[{title}]\n{content}")
        return "\n\n".join(parts) if parts else None
    except Exception as e:
        log.warning("fast.tavily_failed", error=str(e))
    return None


async def _fetch_wikipedia_search(client: httpx.AsyncClient, name: str) -> Optional[str]:
    """Wikipedia action API search + extract — works where REST summary 403s."""
    try:
        # Search for the page title first.
        r = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": name,
                    "format": "json", "srlimit": "1"},
            headers={"User-Agent": "NexusIntel/1.0 (admin@nexusintel.in)"},
        )
        if r.status_code != 200:
            return None
        hits = r.json().get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        # Pull the plain-text extract.
        r2 = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "prop": "extracts", "explaintext": "1",
                    "exintro": "1", "titles": title, "format": "json"},
            headers={"User-Agent": "NexusIntel/1.0 (admin@nexusintel.in)"},
        )
        if r2.status_code != 200:
            return None
        pages = r2.json().get("query", {}).get("pages", {})
        for p in pages.values():
            ex = p.get("extract")
            if ex:
                return f"[WIKIPEDIA: {title}]\n{ex}"
    except Exception as e:
        log.warning("fast.wikisearch_failed", error=str(e))
    return None


async def _fetch_wikipedia(client: httpx.AsyncClient, name: str) -> Optional[str]:
    # Use the REST summary endpoint — single hop, returns plain text.
    try:
        # Try a couple of normalisations.
        candidates = [name, name.title(), re.sub(r"\b(Private|Limited|Pvt|Ltd)\b", "", name, flags=re.I).strip()]
        seen = set()
        for cand in candidates:
            cand = re.sub(r"\s+", " ", cand).strip()
            if not cand or cand in seen:
                continue
            seen.add(cand)
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(cand)}"
            r = await client.get(url, headers={
                "User-Agent": "NexusIntel/1.0 (contact: admin@nexusintel.in)",
                "Accept": "application/json",
            })
            if r.status_code == 200:
                data = r.json()
                if data.get("extract"):
                    return f"[WIKIPEDIA: {data.get('title','')}]\n{data['extract']}"
    except Exception as e:
        log.warning("fast.wiki_failed", error=str(e))
    return None


async def _fetch_zauba_search(client: httpx.AsyncClient, name: str) -> Optional[str]:
    """Zauba's company search page returns CIN/ROC/address text in HTML."""
    try:
        url = f"https://www.zaubacorp.com/companysearchresults/{urllib.parse.quote(name)}"
        r = await client.get(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
            "Referer": "https://www.zaubacorp.com/",
        }, follow_redirects=True)
        # Zauba sometimes returns the search-results page with 403 but body is fine.
        if r.text and len(r.text) > 1000:
            return r.text
    except Exception as e:
        log.warning("fast.zauba_failed", error=str(e))
    return None


def _strip(s: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Strict field-level validators. Each must return True for the value to be kept.
INDIAN_STATES = {
    "andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh","goa",
    "gujarat","haryana","himachal pradesh","jharkhand","karnataka","kerala",
    "madhya pradesh","maharashtra","manipur","meghalaya","mizoram","nagaland",
    "odisha","punjab","rajasthan","sikkim","tamil nadu","telangana","tripura",
    "uttar pradesh","uttarakhand","west bengal","delhi","chandigarh",
    "jammu and kashmir","ladakh","puducherry","andaman","lakshadweep","dadra",
}
CIN_RE = re.compile(r"^[ULul]\d{5}[A-Za-z]{2}\d{4}[A-Za-z]{3}\d{6}$")
GST_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$", re.I)
PHONE_DIGITS = re.compile(r"\d")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
URL_RE = re.compile(r"^https?://", re.I)
SPAM_TOKENS = ("profit withdraw","invest now","capital back","return type",
               "bitcoin","crypto","forex signal","mlm","lottery")


def _looks_like_address(s: str) -> bool:
    sl = s.lower()
    if any(t in sl for t in SPAM_TOKENS):
        return False
    if re.search(r"\b\d{6}\b", s):  # PIN code
        return True
    if any(st in sl for st in INDIAN_STATES):
        return True
    return False


def _valid_email(s: str) -> bool:
    if not EMAIL_RE.match(s):
        return False
    local = s.split("@", 1)[0].lower()
    if local in {"info","contact","support","hello","admin","sales"}:
        return True  # generic role email is fine
    return True


DIRECTORY_HOSTS = (
    "tracxn.com", "zaubacorp.com", "instafinancials.com", "wikipedia.org",
    "linkedin.com/in/", "indiamart.com", "justdial.com", "tofler.in",
    "thecompanycheck.com", "mca.gov.in", "startupindia.gov.in",
    "crunchbase.com", "owler.com", "rocketreach.co", "growjo.com",
    "newcompanyalert.in", "indianyellowpages.com", "tradeindia.com",
    "exportersindia.com", "dnb.com", "bizapedia.com", "opencorporates.com",
    "companies360.in", "themasterprofile.in", "kotwalfinancial.com",
    "quickcompany.in", "rocsearch.com",
)


def _valid_url(s: str) -> bool:
    if not (URL_RE.match(s) and "." in s and len(s) < 250):
        return False
    sl = s.lower()
    if any(h in sl for h in DIRECTORY_HOSTS):
        return False
    return True


def _verify(fields: dict, source_text: str, name: str) -> dict:
    """Drop any scalar field whose value isn't substring-present in source
    AND fails its format validator. This is the production gate."""
    if not fields:
        return {}
    hay = source_text.lower()
    if not _has_name(source_text, name):
        return {}
    out: dict = {}
    for k, v in fields.items():
        if v is None or v == "":
            continue
        if isinstance(v, list):
            kept = [x for x in v if isinstance(x, str) and x.lower() in hay]
            if kept:
                out[k] = kept
            continue
        if not isinstance(v, str):
            out[k] = v
            continue
        vs = v.strip()

        # Format-level validators first — these catch hallucinations even
        # when the LLM happens to copy a stray substring from source.
        if k == "cin" and not CIN_RE.match(vs):
            continue
        if k == "gst" and not GST_RE.match(vs):
            continue
        if k == "email" and not _valid_email(vs):
            continue
        if k == "website" and not _valid_url(vs):
            continue
        if k in ("address", "registered_address") and not _looks_like_address(vs):
            continue
        if k == "phone":
            digits = re.sub(r"\D", "", vs)
            if not (10 <= len(digits) <= 13):
                continue

        if k in NARRATIVE_KEYS:
            out[k] = vs
            continue
        norm = re.sub(r"\s+", " ", vs.lower())
        if norm in hay:
            out[k] = vs
            continue
        digits = re.sub(r"\D", "", vs)
        if len(digits) >= 5 and digits in re.sub(r"\D", "", hay):
            out[k] = vs
            continue
    return out


def _domain_matches_name(url: str, name: str) -> bool:
    """Reject directory-style hits: the URL's domain must contain a name token."""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
        # Strip TLD, keep the second-level label.
        root = host.split(".")[-2] if "." in host else host
        return any(tok in root.lower() for tok in _name_tokens(name))
    except Exception:
        return False


async def _fetch_company_site(client: httpx.AsyncClient, candidates: list[str], name: str) -> tuple[Optional[str], Optional[str]]:
    """Pick the first candidate URL whose DOMAIN reflects the company name
    AND whose homepage actually mentions the company. Skips directory hosts.
    Returns (chosen_url, combined_text_of_home_plus_contact_page)."""
    candidates = [u for u in candidates if _domain_matches_name(u, name)]
    for url in candidates[:4]:
        try:
            r = await client.get(url, timeout=4.0,
                                 headers={"User-Agent": UA},
                                 follow_redirects=True)
            if r.status_code >= 400 or not r.text:
                continue
            home_text = _strip(r.text)[:8000]
            if not _has_name(home_text, name):
                continue
            # Try to also grab /contact for richer contact details.
            parts = [f"[HOMEPAGE: {url}]\n{home_text}"]
            try:
                base = urllib.parse.urlparse(url)
                origin = f"{base.scheme}://{base.netloc}"
                for path in ("/contact", "/contact-us", "/contactus", "/about", "/about-us"):
                    r2 = await client.get(origin + path, timeout=3.0,
                                          headers={"User-Agent": UA},
                                          follow_redirects=True)
                    if r2.status_code < 400 and r2.text:
                        ct = _strip(r2.text)[:4000]
                        if _has_name(ct, name):
                            parts.append(f"[{path}]\n{ct}")
                            break
            except Exception:
                pass
            return url, "\n\n".join(parts)
        except Exception:
            continue
    return None, None


async def _verify_website(client: httpx.AsyncClient, url: str, name: str) -> bool:
    """Fetch the candidate site and require its body to mention the company."""
    try:
        r = await client.get(url, timeout=4.0, headers={"User-Agent": UA},
                             follow_redirects=True)
        if r.status_code >= 400 or not r.text:
            return False
        return _has_name(_strip(r.text)[:8000], name)
    except Exception:
        return False


async def fast_enrich(name: str, timeout_s: float = 8.0) -> dict:
    """Return a dict shaped like enrich_contact's output (incl. extras)."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    chunks: list[tuple[str, str]] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=True) as client:
        # Paid APIs in parallel — no cross-rate-limiting between them.
        primary = await asyncio.gather(
            _fetch_serpapi(client, f"{name} CIN registered address directors authorised paid-up capital India"),
            _fetch_tavily(client, f"{name} official website contact email phone CIN address"),
            return_exceptions=True,
        )
        results: list = [
            primary[0] if not isinstance(primary[0], Exception) else None,
            primary[1] if not isinstance(primary[1], Exception) else None,
        ]
        # Only hit free-tier fallbacks if both paid APIs failed AND budget remains.
        if not any(results) and asyncio.get_event_loop().time() < deadline - 4:
            for fn in (
                lambda: _fetch_zauba_search(client, name),
                lambda: _fetch_bing(client, f"{name} India CIN address directors"),
                lambda: _fetch_wikipedia_search(client, name),
            ):
                if asyncio.get_event_loop().time() >= deadline - 4:
                    results.append(None); continue
                try: results.append(await fn())
                except Exception as e:
                    log.warning("fast.source_failed", error=str(e))
                    results.append(None)
        else:
            results.extend([None, None, None])

    labels = ["serpapi_google", "tavily_search", "zauba", "bing_overview", "wikipedia"]
    for label, res in zip(labels, results):
        if isinstance(res, Exception) or not res:
            continue
        text = _strip(res)
        if not text:
            continue
        # Hard cap each chunk; multi-source corpus must fit the 8b TPM budget.
        chunks.append((label, text[:4500]))

    if not chunks:
        return {}

    # Extract Google AI Overview block (if SerpAPI captured one).
    serp = next((t for l, t in chunks if l == "serpapi_google"), "")
    ao_block = ""
    if "[GOOGLE AI OVERVIEW]" in serp:
        after = serp.split("[GOOGLE AI OVERVIEW]", 1)[1].lstrip("\n")
        ao_block = after.split("\n\n[", 1)[0]
    ao_has_cin = bool(ao_block) and bool(
        re.search(r"[ULul]\d{5}[A-Za-z]{2}\d{4}[A-Za-z]{3}\d{6}",
                  ao_block.replace(" ", "").replace("\n", ""))
    )

    # Per user mandate: contacts ONLY from (a) Google AI Overview OR
    # (b) the company's own website. Fetch that website live from SerpAPI's
    # organic-result candidates (directory hosts already excluded).
    site_url, site_text = None, None
    if _LAST_SERP_ORGANIC and asyncio.get_event_loop().time() < deadline - 4:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0),
                                         follow_redirects=True) as sclient:
                site_url, site_text = await _fetch_company_site(sclient, _LAST_SERP_ORGANIC, name)
        except Exception as e:
            log.warning("fast.company_site_fetch_failed", error=str(e))

    # Rebuild a clean LLM corpus from AO + company website only.
    if ao_block or site_text:
        clean_chunks: list[tuple[str, str]] = []
        if ao_block:
            clean_chunks.append(("google_ai_overview", "[GOOGLE AI OVERVIEW]\n" + ao_block))
        if site_text:
            clean_chunks.append(("company_site", site_text))
        chunks = clean_chunks
        log.info("fast.using_clean_corpus", ao=bool(ao_block), site=bool(site_url))

    source_text = "\n\n".join(c[1] for c in chunks)
    budget = max(2.0, deadline - asyncio.get_event_loop().time())
    fields = await llm_extract(name, chunks, timeout_s=budget)
    verified = _verify(fields, source_text, name)
    if not verified:
        return {}

    # Punctuation-insensitive matcher used by the AO-vs-site source check.
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", s.lower())

    if ao_has_cin:
        ao_n = _norm(ao_block)
        site_n = _norm(site_text or "")
        REGISTRY_FIELDS = {"cin", "directors", "address", "registered_address",
                           "roc", "authorised_capital", "paid_up_capital",
                           "registration_date", "founded", "company_status"}
        for k in list(verified.keys()):
            if k not in REGISTRY_FIELDS:
                continue
            v = verified[k]
            if isinstance(v, list):
                kept = [x for x in v if isinstance(x, str) and _norm(x) in ao_n]
                if kept:
                    verified[k] = kept
                else:
                    log.info("fast.drop_registry_not_in_ao", key=k)
                    verified.pop(k, None)
            elif isinstance(v, str):
                vn = _norm(v)
                if vn in ao_n or (vn and vn in site_n):
                    continue
                digits = re.sub(r"\D", "", v)
                ao_digits = re.sub(r"\D", "", ao_block)
                if len(digits) >= 5 and digits in ao_digits:
                    continue
                log.info("fast.drop_registry_not_in_ao", key=k, value=v[:80])
                verified.pop(k, None)

    # India-anchor gate (hard). Indian companies always have CINs; if none
    # was extracted, require a strong Indian extracted anchor in the FIELDS
    # (not just the source corpus, which always contains "India" because
    # that was in our own query). Without an anchor, drop the whole result.
    addr_blob = (str(verified.get("address","")) + " " +
                 str(verified.get("registered_address",""))).lower()
    has_anchor = (
        bool(verified.get("cin"))
        or bool(re.search(r"\b\d{6}\b", addr_blob))  # Indian PIN in extracted address
        or any(st in addr_blob for st in INDIAN_STATES)
        or (verified.get("phone","").startswith("+91"))
    )
    if not has_anchor:
        log.info("fast.drop_no_india_anchor", name=name, kept_fields=list(verified.keys()))
        return {}
    # Also drop any field that contains a clearly foreign anchor.
    FOREIGN_TOKENS = ("united states","new hampshire","california","texas","florida",
                      "ontario","quebec","london, uk","united kingdom"," usa")
    for k in list(verified.keys()):
        v = verified[k]
        if isinstance(v, str) and any(t in v.lower() for t in FOREIGN_TOKENS):
            log.info("fast.drop_foreign_value", key=k, value=v[:80])
            verified.pop(k, None)
    # Drop phones that aren't Indian (+91, 0xxxxxxxxx, or 10-digit starting 6-9).
    ph = verified.get("phone")
    if ph:
        digits = re.sub(r"\D", "", ph)
        if ph.startswith("+1") or (len(digits) == 11 and digits.startswith("1")):
            verified.pop("phone", None)

    # Live website verification — drop the URL if the page doesn't mention
    # the company. If website is dropped, also drop email/phone unless their
    # source was the registry corpus (zauba) directly.
    async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
        site_ok = True
        site = verified.get("website")
        if site:
            site_ok = await _verify_website(client, site, name)
            if not site_ok:
                verified.pop("website", None)
    if not site_ok:
        # Decouple email when website mismatched — domain coupling can't be
        # established, so the email may also belong to the wrong site.
        em = verified.get("email")
        if em and "@" in em:
            verified.pop("email", None)

    # Email-domain coupling: if both email and website kept, require domain match.
    em = verified.get("email")
    site = verified.get("website")
    if em and site:
        try:
            site_host = urllib.parse.urlparse(site).hostname or ""
            site_root = ".".join(site_host.split(".")[-2:]).lower()
            em_host = em.split("@", 1)[1].lower()
            em_root = ".".join(em_host.split(".")[-2:])
            if site_root and em_root and site_root != em_root:
                verified.pop("email", None)
        except Exception:
            pass

    # CIN-anchored consistency: drop fields that contradict the CIN.
    # CIN layout: [U/L] NNNNN SS YYYY XXX NNNNNN  (S=state code, Y=incorp year)
    cin = verified.get("cin")
    if cin and len(cin) == 21:
        cin_state = cin[6:8].upper()
        cin_year = cin[8:12]
        STATE_MAP = {  # CIN state code → expected state name in addresses
            "MH": "maharashtra", "DL": "delhi", "KA": "karnataka", "TN": "tamil nadu",
            "TG": "telangana", "AP": "andhra pradesh", "GJ": "gujarat", "RJ": "rajasthan",
            "UP": "uttar pradesh", "MP": "madhya pradesh", "WB": "west bengal",
            "UT": "uttarakhand", "UR": "uttarakhand", "PB": "punjab", "HR": "haryana",
            "OR": "odisha", "BR": "bihar", "JH": "jharkhand", "KL": "kerala",
            "CT": "chhattisgarh", "CH": "chandigarh", "GA": "goa", "AS": "assam",
            "ML": "meghalaya", "MN": "manipur", "TR": "tripura", "MZ": "mizoram",
            "NL": "nagaland", "AR": "arunachal pradesh", "SK": "sikkim",
            "JK": "jammu and kashmir", "PY": "puducherry",
        }
        expected_state = STATE_MAP.get(cin_state)
        for addr_key in ("address", "registered_address"):
            v = verified.get(addr_key)
            if v and expected_state and expected_state not in v.lower():
                log.info("fast.drop_addr_state_mismatch", key=addr_key, value=v[:80], expected=expected_state)
                verified.pop(addr_key, None)
        # Drop founded date if it disagrees with CIN year by > 1 year.
        founded = verified.get("founded") or verified.get("registration_date")
        if founded and isinstance(founded, str):
            m = re.search(r"(19|20)\d{2}", founded)
            if m and abs(int(m.group(0)) - int(cin_year)) > 1:
                verified.pop("founded", None)

    # Email sanity: for free-provider emails (gmail/yahoo/…), the local-part
    # MUST contain the company's first name-token in full. Catches typos
    # like "ronixfoods@gmail.com" for "DRONIX FOODS".
    em = verified.get("email")
    if em:
        first_token = next(iter(_name_tokens(name)), "")
        local, _, domain = em.partition("@")
        local = local.lower(); domain = domain.lower()
        FREE_PROVIDERS = {"gmail.com","yahoo.com","yahoo.in","outlook.com","hotmail.com",
                          "rediffmail.com","icloud.com","live.com","aol.com"}
        if first_token and len(first_token) >= 4:
            if domain in FREE_PROVIDERS:
                if first_token not in local:
                    verified.pop("email", None)
            else:
                # Custom domain: domain root should contain the first name-token.
                root = ".".join(domain.split(".")[-2:]).split(".")[0]
                if first_token not in root and root not in first_token:
                    verified.pop("email", None)

    out: dict = {}
    for k in CONTACT_KEYS:
        if verified.get(k):
            out[k] = verified[k]
    extras = {k: v for k, v in verified.items() if k not in set(CONTACT_KEYS) | {"source"}}
    # Carry the verbatim Google AI Overview block so the modal can show it
    # as-rendered alongside the LLM-parsed structured fields.
    if ao_block:
        extras["google_ai_overview"] = ao_block.strip()
    if site_url:
        extras.setdefault("website", site_url)
    if extras:
        out["extras"] = extras
    return out
