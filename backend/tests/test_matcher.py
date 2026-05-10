import pytest
from datetime import date
from app.services.matcher_service import compute_match_score, batch_match


def test_exact_cin_match():
    score, method = compute_match_score(
        "Acme Tech Pvt Ltd", "ACME TECH PRIVATE LIMITED",
        "U72200MH2020PTC123456", "U72200MH2020PTC123456",
        date(2020, 1, 15), date(2020, 1, 15),
    )
    assert score == 1.0
    assert method == "exact_cin"


def test_fuzzy_name_high_score():
    score, method = compute_match_score(
        "Zomato Limited", "ZOMATO LTD",
        None, None,
        date(2010, 1, 1), date(2010, 1, 1),
    )
    assert score >= 0.75


def test_fuzzy_name_low_score():
    score, method = compute_match_score(
        "Apple Inc", "Orange Beverages Pvt Ltd",
        None, None, None, None,
    )
    assert score < 0.5


def test_batch_match_returns_matches():
    zauba = [
        {"cin": "U72200MH2020PTC111", "company_name": "StartupX India Pvt Ltd", "date_of_incorporation": date(2022, 1, 1)},
        {"cin": None, "company_name": "TechNova Solutions Ltd", "date_of_incorporation": date(2021, 6, 15)},
    ]
    datagov = [
        {"cin": "U72200MH2020PTC111", "company_name": "STARTUPX INDIA PRIVATE LIMITED", "date_of_incorporation": date(2022, 1, 1)},
        {"cin": None, "company_name": "TECHNOVA SOLUTIONS LIMITED", "date_of_incorporation": date(2021, 6, 15)},
    ]
    results = batch_match(zauba, datagov)
    assert len(results) == 2
    assert results[0]["match_score"] == 1.0
    assert results[1]["match_score"] >= 0.75


def test_batch_match_unmatched():
    zauba = [{"cin": None, "company_name": "ABC Completely Different Ltd", "date_of_incorporation": None}]
    datagov = [{"cin": None, "company_name": "XYZ Unrelated Corp", "date_of_incorporation": None}]
    results = batch_match(zauba, datagov)
    assert results[0]["match_method"] == "unmatched"


def test_batch_match_empty_datagov():
    zauba = [{"cin": "U123", "company_name": "Solo Co Pvt Ltd", "date_of_incorporation": None}]
    results = batch_match(zauba, [])
    assert len(results) == 1
    assert results[0]["match_method"] == "unmatched"
