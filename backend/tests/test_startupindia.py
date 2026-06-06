"""Unit tests for the StartupIndia scraper normalizer.

These tests do not hit the network — they exercise the JSON envelope parsing
and per-record normalization. The Playwright-driven page load itself is
exercised in manual local runs since it requires a Chromium install.
"""
from app.services.startupindia_scraper import StartupIndiaScraper


def test_extract_items_handles_content_envelope():
    body = {
        "content": [
            {"profileId": "p1", "companyName": "Acme"},
            {"profileId": "p2", "companyName": "Beta"},
        ],
        "totalElements": 2,
    }
    items = StartupIndiaScraper._extract_items(body)
    assert len(items) == 2
    assert items[0]["profileId"] == "p1"


def test_extract_items_handles_bare_list():
    body = [{"id": "x", "name": "Foo"}]
    assert StartupIndiaScraper._extract_items(body) == body


def test_extract_items_handles_nested_data():
    body = {"data": {"content": [{"id": "1", "name": "N"}]}}
    items = StartupIndiaScraper._extract_items(body)
    assert items == [{"id": "1", "name": "N"}]


def test_normalize_required_fields():
    s = StartupIndiaScraper()
    out = s._normalize({
        "profileId": "abc-123",
        "companyName": "Foo Tech Pvt Ltd",
        "industry": "FinTech",
        "sector": "Banking",
        "stage": "Growth",
        "state": "Karnataka",
        "city": "Bengaluru",
        "website": "https://foo.tech",
        "logo": "https://cdn/x.png",
        "description": "We do things.",
        "badges": ["DPIIT"],
        # Strict DPIIT requires all three signals
        "dippRecognitionStatus": "RECOGNISED",
        "dippCertified": True,
        "dippNumber": "DIPP123456",
    })
    assert out["profile_id"] == "abc-123"
    assert out["company_name"] == "Foo Tech Pvt Ltd"
    assert out["industry"] == "FinTech"
    assert out["stage"] == "Growth"
    assert out["dpiit_recognised"] is True
    assert out["dipp_number"] == "DIPP123456"
    assert "profileId=abc-123" in out["profile_url"]
    assert out["badges"] == ["DPIIT"]


def test_normalize_dpiit_strictness():
    """Without the strict triple-check, dpiit must NOT be True."""
    s = StartupIndiaScraper()
    # Missing recognition status
    out = s._normalize({"profileId":"x","companyName":"A","dippCertified":True,"dippNumber":"DIPP1"})
    assert out["dpiit_recognised"] is False
    # Wrong status value
    out = s._normalize({"profileId":"x","companyName":"A","dippRecognitionStatus":"APPLIED","dippCertified":True,"dippNumber":"DIPP1"})
    assert out["dpiit_recognised"] is False
    # Malformed DIPP number
    out = s._normalize({"profileId":"x","companyName":"A","dippRecognitionStatus":"RECOGNISED","dippCertified":True,"dippNumber":"X-1"})
    assert out["dpiit_recognised"] is False


def test_normalize_missing_id_returns_none():
    s = StartupIndiaScraper()
    assert s._normalize({"companyName": "no id here"}) is None


def test_normalize_missing_name_returns_none():
    s = StartupIndiaScraper()
    assert s._normalize({"profileId": "x"}) is None


def test_normalize_handles_alternate_keys():
    s = StartupIndiaScraper()
    out = s._normalize({
        "id": "alt-1",
        "name": "Other Co",
        "industryName": "AI",
        "sectorName": "ML",
        "stateName": "TN",
    })
    assert out["profile_id"] == "alt-1"
    assert out["company_name"] == "Other Co"
    assert out["industry"] == "AI"
    assert out["sector"] == "ML"
    assert out["state"] == "TN"


def test_normalize_badges_string_coerced_to_list():
    s = StartupIndiaScraper()
    out = s._normalize({"id": "1", "name": "X", "badges": "DPIIT"})
    assert out["badges"] == ["DPIIT"]
