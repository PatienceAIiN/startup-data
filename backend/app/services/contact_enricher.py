"""Deep contact-info enricher.

Pipeline:
  1. Resolve a candidate official site for the company:
     a) Try plausible guessed domains.
     b) Else, Bing search via warm Playwright context.
  2. Crawl the chosen site:
     - Home page
     - Internal links matching contact / about / team / reach / connect / support
     - Footer links
  3. Extract on every page:
     - mailto: and tel: anchor hrefs
     - schema.org JSON-LD (Organization / ContactPoint / PostalAddress)
     - <address> blocks
     - regex sweeps for emails, phones, social handles
     - Address paragraphs near "Address" / "Office" / "Reach us" headers
  4. Merge, prefer richer values, persist.
"""
import asyncio
import json
import re
from typing import Optional
from urllib.parse import urlparse, urljoin

import httpx
import structlog
from bs4 import BeautifulSoup

from app.services.startupindia_scraper import _get_warm_page

log = structlog.get_logger()

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Indian phone patterns, tried in order of specificity. Each captures the
# match-able portion; _clean_phone validates digit count + Indian rules.
PHONE_PATTERNS = [
    # +91 mobile (10 digits, optional separators)
    re.compile(r"\+\s*91[\s.\-]?[6-9]\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4}\b"),
    re.compile(r"\+\s*91[\s.\-]?\d{10}\b"),
    # 91 prefix without +
    re.compile(r"\b91[\s.\-]?[6-9]\d{9}\b"),
    # 10-digit Indian mobile starting with 6/7/8/9
    re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)"),
    # Indian landline: optional 0 then 2–4 digit STD then 6–8 digit subscriber
    re.compile(r"(?<!\d)0?\d{2,4}[\s.\-]?\d{6,8}(?!\d)"),
]
SOCIAL_RE = re.compile(r"https?://(?:www\.)?(linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com)/[A-Za-z0-9_./-]+")
# Indian Corporate Identification Number — 21-char alphanumeric
CIN_RE = re.compile(r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
GST_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
NOISE_HOSTS = (
    "startupindia.gov.in", "wikipedia.org", "linkedin.com",
    "facebook.com", "twitter.com", "x.com", "youtube.com",
    "instagram.com", "google.com", "bing.com", "duckduckgo.com",
    "tracxn.com", "zaubacorp.com", "indiamart.com", "justdial.com",
    "crunchbase.com", "owler.com", "mca.gov.in", "rocketreach.co",
    "yourstory.com", "inc42.com", "techcrunch.com",
)
TLDS = (".com", ".in", ".co.in", ".io", ".tech", ".net", ".co")
CONTACT_KEYWORDS = ("contact", "about", "team", "reach", "connect", "support", "office", "hello")
ADDRESS_HEADERS = re.compile(r"\b(address|office|registered\s+office|head\s+office|reach\s+us|find\s+us|visit\s+us|our\s+location)\b", re.I)
INVALID_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf")
NOISE_EMAIL_PREFIXES = ("noreply", "no-reply", "donotreply", "example@", "name@", "your@", "test@", "sample@")
DISPOSABLE_DOMAINS = ("example.com", "test.com", "sample.com")

MAX_PAGES = 5
PER_PAGE_TIMEOUT_MS = 6_000
HTTPX_TIMEOUT_S = 6.0
TOTAL_BUDGET_S = 22.0
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}


# ---------- domain guessing ----------

def _slug_candidates(name: str) -> list[str]:
    """Build plausible domain stems. Handles parenthesised qualifiers like
    'TTR ESCAPES (OPC) PRIVATE LIMITED' by stripping the bracketed segment."""
    n = name.lower()
    # Strip bracketed qualifiers entirely
    n = re.sub(r"\([^)]*\)", " ", n)
    n = re.sub(r"\b(private limited|pvt\.? ?ltd\.?|limited|ltd\.?|llp|opc|inc\.?|corp\.?|company)\b", " ", n)
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    parts = [p for p in n.split() if len(p) > 1 and p not in ("the", "and", "of", "co")]
    if not parts:
        return []
    stems: set[str] = set()
    stems.add("".join(parts))
    stems.add(parts[0])
    if len(parts) >= 2:
        stems.add("".join(parts[:2]))
        stems.add(f"{parts[0]}-{parts[1]}")
        stems.add(f"{parts[0]}{parts[1]}")
    return sorted({s for s in stems if 3 <= len(s) <= 40}, key=len, reverse=True)


# ---------- extraction primitives ----------

def _clean_email(e: str) -> Optional[str]:
    el = e.lower()
    if any(el.endswith(x) for x in INVALID_EMAIL_SUFFIXES):
        return None
    if any(el.startswith(x) for x in NOISE_EMAIL_PREFIXES):
        return None
    if any(d in el for d in DISPOSABLE_DOMAINS):
        return None
    return e


YEAR_LIKE = re.compile(r"^(19|20)\d{2}$")


def _normalize_indian_phone(digits: str) -> Optional[str]:
    """Return E.164-style Indian number if `digits` is a valid Indian phone.
    Mobile: 10 digits starting 6-9, optionally prefixed by 91 or 0.
    Landline: 10-11 digits starting with 0 followed by area code + subscriber.
    """
    # Strip leading 0 from landline-style 11-digit
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    # +91 mobile
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        m = digits[2:]
        return f"+91 {m[:5]} {m[5:]}"
    # 10-digit mobile
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91 {digits[:5]} {digits[5:]}"
    # +91 landline (11–12 digit total): 91 + 2–4 area + 6–8 subscriber
    if 11 <= len(digits) <= 14 and digits.startswith("91") and len(digits) - 2 >= 8:
        rest = digits[2:]
        # Heuristic landline format split: assume 2-digit area for metros (11/22/33/44/40/79/80)
        # else fall back to first 4 digits as area
        area = rest[:2] if rest[:2] in {"11","22","33","44","40","79","80","20","33"} else rest[:3]
        sub = rest[len(area):]
        if 6 <= len(sub) <= 9:
            return f"+91 {area} {sub}"
    # 10-digit landline starting with non-mobile digit (e.g., 22XXXXXXXX = Mumbai)
    if len(digits) == 10 and digits[0] in "12345":
        return f"+91 {digits[:2]} {digits[2:]}"
    return None


def _clean_phone(p: str) -> Optional[str]:
    """Return a normalised Indian phone, or None if it's clearly not a phone.
    Rejects obvious non-phones (years, PINs, etc.)."""
    if not p:
        return None
    raw = p.strip()
    # Quick reject — bare 4-digit year
    if YEAR_LIKE.match(raw):
        return None
    # Quick reject — looks like Indian PIN (exactly 6 digits with no separators)
    if re.fullmatch(r"\d{6}", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    normalised = _normalize_indian_phone(digits)
    if normalised:
        return normalised
    # Fall back: accept generic E.164-ish input (8–15 digits, with leading +)
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return raw
    return None


def _scan_phones(text: str) -> Optional[str]:
    """Run our phone patterns over `text` and return the first one that
    validates through _clean_phone."""
    for pat in PHONE_PATTERNS:
        for m in pat.finditer(text):
            cand = _clean_phone(m.group(0))
            if cand:
                return cand
    return None


def _extract_jsonld(soup: BeautifulSoup) -> dict:
    """Walk all JSON-LD blocks for Organization / ContactPoint / PostalAddress."""
    out = {"email": None, "phone": None, "address": None}
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    kl = k.lower()
                    if kl == "email" and isinstance(v, str) and not out["email"]:
                        e = _clean_email(v.replace("mailto:", ""))
                        if e:
                            out["email"] = e
                    elif kl == "telephone" and isinstance(v, str) and not out["phone"]:
                        p = _clean_phone(v)
                        if p:
                            out["phone"] = p
                    elif kl == "address" and not out["address"]:
                        if isinstance(v, str):
                            out["address"] = v.strip()
                        elif isinstance(v, dict):
                            parts = [v.get(k) for k in (
                                "streetAddress", "addressLocality",
                                "addressRegion", "postalCode", "addressCountry"
                            )]
                            joined = ", ".join([p for p in parts if isinstance(p, str) and p.strip()])
                            if joined:
                                out["address"] = joined
                    if isinstance(v, (dict, list)):
                        walk(v)
            elif isinstance(node, list):
                for n in node:
                    walk(n)

        for c in candidates:
            walk(c)
    return out


def _extract_anchor_contacts(soup: BeautifulSoup) -> dict:
    out = {"email": None, "phone": None, "linkedin": None, "twitter": None, "facebook": None, "instagram": None}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:") and not out["email"]:
            e = _clean_email(href.split(":", 1)[1].split("?")[0])
            if e:
                out["email"] = e
        elif href.lower().startswith("tel:") and not out["phone"]:
            p = _clean_phone(href.split(":", 1)[1])
            if p:
                out["phone"] = p
        else:
            m = SOCIAL_RE.search(href)
            if m:
                host = m.group(1)
                if "linkedin" in host and not out["linkedin"]:
                    out["linkedin"] = m.group(0)
                elif ("twitter" in host or "x.com" in host) and not out["twitter"]:
                    out["twitter"] = m.group(0)
                elif "facebook" in host and not out["facebook"]:
                    out["facebook"] = m.group(0)
                elif "instagram" in host and not out["instagram"]:
                    out["instagram"] = m.group(0)
    return out


PIN_RE = re.compile(r"\b\d{6}\b")
STATE_RE = re.compile(r"\b(Andhra Pradesh|Arunachal Pradesh|Assam|Bihar|Chhattisgarh|Goa|Gujarat|Haryana|"
                      r"Himachal Pradesh|Jharkhand|Karnataka|Kerala|Madhya Pradesh|Maharashtra|Manipur|"
                      r"Meghalaya|Mizoram|Nagaland|Odisha|Punjab|Rajasthan|Sikkim|Tamil Nadu|Telangana|"
                      r"Tripura|Uttar Pradesh|Uttarakhand|West Bengal|Delhi|Chandigarh|Puducherry|"
                      r"Jammu and Kashmir|Ladakh)\b", re.I)


def _looks_like_address(text: str) -> bool:
    """Require an Indian PIN code — sharply reduces false positives from marketing copy."""
    if not text or len(text) < 15:
        return False
    return bool(PIN_RE.search(text))


def _extract_address_blocks(soup: BeautifulSoup) -> Optional[str]:
    # 1) explicit <address> tag
    for el in soup.find_all("address"):
        t = " ".join(el.get_text(" ", strip=True).split())
        if _looks_like_address(t) and len(t) <= 400:
            return t

    # 2) Paragraphs near "Address" / "Office" headers (require address signal)
    text = soup.get_text("\n", strip=True)
    for m in ADDRESS_HEADERS.finditer(text):
        snippet = text[m.end(): m.end() + 300]
        snippet = re.sub(r"\s+", " ", snippet).strip(" :,-")
        if _looks_like_address(snippet) and len(snippet) <= 300:
            return snippet

    # 3) Last-resort: scan footer / contact-section text for any block that
    #    contains a pin code, capture +/- a sentence around it.
    full = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    for pm in PIN_RE.finditer(full):
        start = max(0, pm.start() - 150)
        end = min(len(full), pm.end() + 60)
        snippet = full[start:end].strip(" :,-")
        if _looks_like_address(snippet):
            return snippet
    return None


def _extract_regex_sweep(html: str) -> dict:
    out = {"email": None, "phone": None}
    for e in EMAIL_RE.findall(html):
        e = _clean_email(e)
        if e:
            out["email"] = e
            break
    out["phone"] = _scan_phones(html)
    return out


def _harvest_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    jl = _extract_jsonld(soup)
    a = _extract_anchor_contacts(soup)
    sweep = _extract_regex_sweep(html)
    addr = _extract_address_blocks(soup) or jl.get("address")
    # Identifiers (regulatory)
    cin_m = CIN_RE.search(html)
    gst_m = GST_RE.search(html)
    return {
        "email": a.get("email") or jl.get("email") or sweep.get("email"),
        "phone": a.get("phone") or jl.get("phone") or sweep.get("phone"),
        "address": addr,
        "linkedin": a.get("linkedin"),
        "twitter": a.get("twitter"),
        "facebook": a.get("facebook"),
        "instagram": a.get("instagram"),
        "cin": cin_m.group(0) if cin_m else None,
        "gst": gst_m.group(0) if gst_m else None,
    }


def _internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    host = urlparse(base_url).netloc.lower()
    out: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = (a.get_text(" ", strip=True) or "").lower()
        href = a["href"]
        full = urljoin(base_url, href)
        u = urlparse(full)
        if u.netloc and u.netloc.lower() != host:
            continue
        if u.scheme not in ("http", "https"):
            continue
        full = u._replace(fragment="").geturl()
        if full in seen:
            continue
        # prioritize by keyword
        path = u.path.lower()
        score = sum(1 for k in CONTACT_KEYWORDS if k in path or k in text)
        if score == 0:
            continue
        seen.add(full)
        out.append(full)
    return out[:MAX_PAGES]


# ---------- site selection ----------

async def _probe_candidate_domains(client: httpx.AsyncClient, name: str) -> Optional[tuple[str, str]]:
    stems = _slug_candidates(name)
    if not stems:
        return None
    candidates: list[str] = []
    for s in stems:
        for tld in TLDS:
            candidates.append(f"https://{s}{tld}/")
    log.info("contact.candidates_built", count=len(candidates), name=name)

    async def fetch_one(url: str):
        try:
            r = await client.get(url, timeout=HTTPX_TIMEOUT_S, follow_redirects=True)
            if r.status_code >= 400:
                return None
            html = r.text
            if not any(s and s in html.lower() for s in stems if len(s) >= 4):
                return None
            return (str(r.url), html)
        except Exception:
            return None

    for r in await asyncio.gather(*[fetch_one(u) for u in candidates]):
        if r:
            return r
    return None


async def _google_enrichment(page, company_name: str) -> dict:
    """Run two Google queries and return raw SERP text (incl. AI Overview).

    Lets the downstream LLM parse CIN / registration date / capital /
    directors / address instead of fighting selector churn. Also surfaces
    wikipedia/linkedin links opportunistically.
    """
    out: dict = {"serp_text": "", "wikipedia": None, "linkedin_company": None}
    queries = [
        f"{company_name} India",
        f"{company_name} CIN registered address authorised capital directors",
    ]
    blobs: list[str] = []
    for q in queries:
        try:
            await page.goto(
                f"https://www.google.com/search?q={q}&hl=en&gl=in",
                wait_until="domcontentloaded",
                timeout=15_000,
            )
            await asyncio.sleep(2.0)  # let AI Overview hydrate
            data = await page.evaluate(
                """
                () => {
                  // Grab AI Overview if present (jsname WBdPq / WaaZC / LT6XE wrappers vary)
                  const ai = document.querySelector('[jsname="WBdPq"], [data-attrid*="AIOverview"], .WaaZC, .LT6XE, .ULSxyf');
                  const aiText = ai ? (ai.innerText || '').trim() : '';
                  // Whole results column
                  const main = document.querySelector('#center_col, #search, #main') || document.body;
                  const mainText = (main.innerText || '').trim();
                  const links = Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && h.startsWith('http'));
                  return {
                    aiText,
                    mainText: mainText.slice(0, 12000),
                    wiki: links.find(h => h.includes('wikipedia.org')) || null,
                    li: links.find(h => h.includes('linkedin.com/company/')) || null,
                  };
                }
                """
            )
            data = data or {}
            chunk = ""
            if data.get("aiText"):
                chunk += "[AI OVERVIEW]\n" + data["aiText"] + "\n\n"
            if data.get("mainText"):
                chunk += data["mainText"]
            if chunk:
                blobs.append(f"--- google: {q} ---\n{chunk}")
            if not out["wikipedia"] and data.get("wiki"):
                out["wikipedia"] = data["wiki"]
            if not out["linkedin_company"] and data.get("li"):
                out["linkedin_company"] = data["li"]
        except Exception as e:
            log.warning("contact.google_query_failed", q=q, error=str(e))
    out["serp_text"] = "\n\n".join(blobs)
    return out


async def _bing_first_result(page, query: str) -> Optional[str]:
    """Bing wraps result URLs as bing.com/ck/a?...&u=<base64>. Resolve them
    to the real destination (and skip social/aggregator noise)."""
    try:
        await page.goto(f"https://www.bing.com/search?q={query}", wait_until="domcontentloaded", timeout=18_000)
        await asyncio.sleep(1.2)
        # Get hrefs + the visible cite text (Bing shows the unhidden domain there)
        items = await page.eval_on_selector_all(
            "li.b_algo",
            """els => els.map(el => ({
                href: (el.querySelector('h2 a') || {}).href || '',
                cite: (el.querySelector('cite') || {}).textContent || ''
            }))""",
        )
        from urllib.parse import urlparse
        for it in items:
            href = it.get("href") or ""
            cite = (it.get("cite") or "").strip()
            # Prefer cite-derived URL when href is a bing redirector
            target = None
            if href and ("bing.com/ck" in href or not href.startswith("http")):
                if cite:
                    cite_host = cite.split("›")[0].strip().split(" ")[0]
                    if not cite_host.startswith("http"):
                        cite_host = "https://" + cite_host
                    target = cite_host
            else:
                target = href
            if not target or not target.startswith("http"):
                continue
            host = urlparse(target).netloc.lower()
            if any(n in host for n in NOISE_HOSTS):
                continue
            return target
        return None
    except Exception as e:
        log.warning("contact.bing_failed", error=str(e))
        return None


def _merge(into: dict, src: dict) -> None:
    for k, v in src.items():
        if v and not into.get(k):
            into[k] = v


# ---------- entry point ----------

async def enrich_contact(company_name: str) -> dict:
    deadline = asyncio.get_event_loop().time() + TOTAL_BUDGET_S
    async with httpx.AsyncClient(headers=COMMON_HEADERS, follow_redirects=True, timeout=HTTPX_TIMEOUT_S) as client:
        chosen: Optional[str] = None
        home_html: str = ""

        # 1a) Domain guessing (httpx, parallel — fast)
        hit = await _probe_candidate_domains(client, company_name)
        if hit:
            chosen, home_html = hit
            log.info("contact.candidate_picked", url=chosen, name=company_name, method="guess")

        # 1b) Bing fallback via warm Playwright (needs browser to avoid bot block)
        if not chosen and asyncio.get_event_loop().time() < deadline:
            # Use a dedicated short-lived page so the warm page (used by other
            # callers) can't be navigated out from under us.
            try:
                warm = await _get_warm_page()
                bing_page = await warm.context.new_page()
                try:
                    bing_url = await _bing_first_result(bing_page, company_name + " official website")
                finally:
                    await bing_page.close()
            except Exception as e:
                log.warning("contact.bing_setup_failed", error=str(e))
                bing_url = None
            if bing_url:
                try:
                    r = await client.get(bing_url, timeout=HTTPX_TIMEOUT_S)
                    if r.status_code < 400:
                        chosen = str(r.url)
                        home_html = r.text
                        log.info("contact.candidate_picked", url=chosen, name=company_name, method="bing")
                except Exception:
                    pass

        # Google knowledge-panel enrichment — runs alongside site scraping for
        # extra business facts (founded, HQ, founders, employees, CEO, revenue).
        # Google SERP harvest (AI Overview + main column raw text + wiki/li links).
        extras: dict = {}
        google_chunk = ""
        if asyncio.get_event_loop().time() < deadline:
            try:
                warm = await _get_warm_page()
                gpage = await warm.context.new_page()
                try:
                    g = await asyncio.wait_for(_google_enrichment(gpage, company_name), timeout=16.0)
                finally:
                    await gpage.close()
                google_chunk = (g or {}).get("serp_text") or ""
                if g and g.get("wikipedia"): extras["wikipedia"] = g["wikipedia"]
                if g and g.get("linkedin_company"): extras["linkedin_company"] = g["linkedin_company"]
            except Exception as e:
                log.warning("contact.google_setup_failed", error=str(e))

        # Validate the chosen company website actually mentions the company name.
        # Without this gate a generic site (zhihu.com etc.) can poison enrichment.
        def _name_present(text: str, name: str) -> bool:
            toks = [t for t in re.split(r"[^A-Za-z0-9]+", name.lower()) if len(t) >= 4
                    and t not in {"private","limited","pvt","ltd","company","india","the"}]
            if not toks:
                return True
            hay = (text or "").lower()
            hits = sum(1 for t in toks if t in hay)
            return hits >= max(1, len(toks) // 2)

        if chosen and home_html and not _name_present(home_html, company_name):
            log.info("contact.chosen_site_rejected_name_mismatch", site=chosen)
            chosen, home_html = None, ""

        if not chosen:
            # Still try the LLM on Google text alone — often contains AI Overview.
            llm_only: dict = {}
            if google_chunk:
                try:
                    from app.services.llm_enricher import llm_extract
                    budget = max(2.0, min(18.0, deadline - asyncio.get_event_loop().time()))
                    llm_only = await llm_extract(company_name, [("google_serp", google_chunk)], timeout_s=budget)
                except Exception as e:
                    log.warning("contact.llm_failed", error=str(e))
            if llm_only:
                for k, v in llm_only.items():
                    if v: extras[k] = v
            return {"email": llm_only.get("email"), "phone": llm_only.get("phone"),
                    "address": llm_only.get("address"), "linkedin": llm_only.get("linkedin"),
                    "twitter": llm_only.get("twitter"), "facebook": llm_only.get("facebook"),
                    "instagram": llm_only.get("instagram"),
                    "source": None, "extras": extras or None}

        # 2) Deep crawl — home + likely internal pages
        merged: dict = {"source": chosen}
        soup = BeautifulSoup(home_html, "html.parser")
        _merge(merged, _harvest_page(home_html))
        links = _internal_links(soup, chosen)

        base = urlparse(chosen)
        base_origin = f"{base.scheme}://{base.netloc}"
        forced = [f"{base_origin}{p}" for p in
                  ("/contact", "/contact-us", "/contactus", "/about", "/about-us", "/team", "/reach-us")]
        visited = {chosen}
        queue: list[str] = []
        for u in links + forced:
            if u not in visited:
                visited.add(u)
                queue.append(u)
        pages_to_fetch = queue[:MAX_PAGES]

        async def fetch_one(url: str):
            try:
                r = await client.get(url, timeout=HTTPX_TIMEOUT_S)
                if r.status_code < 400:
                    return (url, r.text)
            except Exception:
                pass
            return (url, None)

        # Run remaining fetches concurrently with a global deadline
        remaining = max(0.5, deadline - asyncio.get_event_loop().time())
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[fetch_one(u) for u in pages_to_fetch]),
                timeout=remaining,
            )
        except asyncio.TimeoutError:
            results = []

        # Keep raw HTML chunks for the LLM pass after the regex sweep.
        # Only include pages that actually mention the company name, to avoid
        # the LLM hallucinating from a stray off-topic page reached by a link.
        raw_chunks: list[tuple[str, str]] = []
        if home_html and _name_present(home_html, company_name):
            raw_chunks.append(("homepage", home_html))
        for url, html in results:
            if not html:
                continue
            info = _harvest_page(html)
            _merge(merged, info)
            if _name_present(html, company_name):
                raw_chunks.append((url, html))
            if any(k in url.lower() for k in CONTACT_KEYWORDS) and (info.get("email") or info.get("address")):
                merged["source"] = url
        if google_chunk:
            raw_chunks.append(("google_serp", google_chunk))

        # LLM-powered structured extraction over everything we collected.
        # Best-effort: if Groq is down or slow, regex extractions still stand.
        if raw_chunks and asyncio.get_event_loop().time() < deadline:
            try:
                from app.services.llm_enricher import llm_extract
                budget = max(2.0, min(18.0, deadline - asyncio.get_event_loop().time()))
                llm_fields = await llm_extract(company_name, raw_chunks, timeout_s=budget)
            except Exception as e:
                log.warning("contact.llm_failed", error=str(e))
                llm_fields = {}
        else:
            llm_fields = {}

        if llm_fields:
            # Promote scalar contact fields to the top-level result if missing.
            for src_key, dst_key in (
                ("email", "email"), ("phone", "phone"), ("address", "address"),
                ("linkedin", "linkedin"), ("twitter", "twitter"),
                ("facebook", "facebook"), ("instagram", "instagram"),
                ("cin", "cin"), ("gst", "gst"),
            ):
                v = llm_fields.get(src_key)
                if v and not merged.get(dst_key):
                    merged[dst_key] = v
            # Everything else (founded, hq, revenue, capital, directors,
            # service_areas, registration_date, registered_address …) rides
            # in extras so the UI can render it dynamically. We pass through
            # *every* non-contact LLM key to avoid silently dropping new ones.
            top_level_keys = {"email","phone","address","linkedin","twitter",
                              "facebook","instagram","cin","gst","source"}
            for k, v in llm_fields.items():
                if v and k not in top_level_keys:
                    extras[k] = v

        if extras:
            merged["extras"] = extras
        return merged
