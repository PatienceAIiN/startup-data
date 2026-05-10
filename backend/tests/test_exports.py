import pytest
from app.services.export_service import generate_csv_bytes, generate_xlsx_bytes

SAMPLE_COMPANIES = [
    {
        "cin": "U72200MH2020PTC123456",
        "company_name": "Test Startup Pvt Ltd",
        "company_status": "Active",
        "roc_code": "RoC-Mumbai",
        "company_category": "Company limited by Shares",
        "date_of_incorporation": "2022-01-15",
        "state": "Maharashtra",
        "authorised_capital": 1000000,
        "paid_up_capital": 500000,
        "match_score": 0.95,
        "match_method": "exact_cin",
        "is_startup": True,
        "registered_address": "Mumbai, MH",
    }
]


def test_csv_export_generates_valid_bytes():
    data = generate_csv_bytes(SAMPLE_COMPANIES)
    assert isinstance(data, bytes)
    assert b"CIN" in data
    assert b"Test Startup Pvt Ltd" in data


def test_csv_has_bom():
    data = generate_csv_bytes(SAMPLE_COMPANIES)
    assert data[:3] == b'\xef\xbb\xbf'


def test_xlsx_export_generates_valid_bytes():
    data = generate_xlsx_bytes(SAMPLE_COMPANIES)
    assert isinstance(data, bytes)
    assert len(data) > 1000


def test_xlsx_has_xlsx_magic_bytes():
    data = generate_xlsx_bytes(SAMPLE_COMPANIES)
    assert data[:4] == b'PK\x03\x04'


def test_empty_export():
    csv_data = generate_csv_bytes([])
    assert b"CIN" in csv_data


def test_empty_xlsx():
    data = generate_xlsx_bytes([])
    assert data[:4] == b'PK\x03\x04'
