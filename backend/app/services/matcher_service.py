from datetime import date
from typing import Optional
from rapidfuzz import fuzz, process
from app.config import settings

THRESHOLD = settings.MATCH_CONFIDENCE_THRESHOLD


def compute_match_score(
    zauba_name: str, datagov_name: str,
    zauba_cin: Optional[str], datagov_cin: Optional[str],
    zauba_date: Optional[date], datagov_date: Optional[date]
) -> tuple[float, str]:
    if zauba_cin and datagov_cin and zauba_cin.strip().upper() == datagov_cin.strip().upper():
        return 1.0, "exact_cin"

    name_score = fuzz.token_sort_ratio(zauba_name.upper(), datagov_name.upper()) / 100.0

    date_bonus = 0.0
    if zauba_date and datagov_date and zauba_date.year == datagov_date.year:
        date_bonus = 0.05

    combined = min(name_score + date_bonus, 1.0)
    method = "fuzzy_name" if date_bonus == 0 else "combined"
    return combined, method


def batch_match(zauba_companies: list[dict], datagov_companies: list[dict]) -> list[dict]:
    results = []
    if not datagov_companies:
        for zauba in zauba_companies:
            results.append({
                "zauba_company": zauba,
                "datagov_company": None,
                "match_score": 0.0,
                "match_method": "unmatched",
            })
        return results

    datagov_names = [c["company_name"].upper() for c in datagov_companies]
    datagov_cin_map = {c["cin"].upper(): c for c in datagov_companies if c.get("cin")}

    for zauba in zauba_companies:
        best_score = 0.0
        best_match = None
        best_method = "none"

        zauba_cin = (zauba.get("cin") or "").strip().upper()

        if zauba_cin and zauba_cin in datagov_cin_map:
            dg = datagov_cin_map[zauba_cin]
            score, method = compute_match_score(
                zauba["company_name"], dg["company_name"],
                zauba.get("cin"), dg.get("cin"),
                zauba.get("date_of_incorporation"), dg.get("date_of_incorporation")
            )
            best_score, best_match, best_method = score, dg, method
        else:
            top_matches = process.extract(
                zauba["company_name"].upper(),
                datagov_names,
                scorer=fuzz.token_sort_ratio,
                limit=3
            )
            for match_name, match_score_raw, match_idx in top_matches:
                dg = datagov_companies[match_idx]
                score, method = compute_match_score(
                    zauba["company_name"], dg["company_name"],
                    zauba.get("cin"), dg.get("cin"),
                    zauba.get("date_of_incorporation"), dg.get("date_of_incorporation")
                )
                if score > best_score:
                    best_score, best_match, best_method = score, dg, method

        if best_score >= THRESHOLD and best_match:
            results.append({
                "zauba_company": zauba,
                "datagov_company": best_match,
                "match_score": round(best_score, 4),
                "match_method": best_method,
            })
        else:
            results.append({
                "zauba_company": zauba,
                "datagov_company": None,
                "match_score": round(best_score, 4),
                "match_method": "unmatched",
            })

    return results
