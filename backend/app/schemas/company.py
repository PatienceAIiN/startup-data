from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID
from typing import Optional


class CompanyBase(BaseModel):
    cin: Optional[str] = None
    company_name: str
    company_status: Optional[str] = None
    roc_code: Optional[str] = None
    company_category: Optional[str] = None
    date_of_incorporation: Optional[date] = None
    state: Optional[str] = None
    authorised_capital: Optional[int] = None
    paid_up_capital: Optional[int] = None


class MatchedCompanyResponse(CompanyBase):
    model_config = {"from_attributes": True}
    id: UUID
    match_score: float
    match_method: Optional[str] = None
    is_startup: bool
    registered_address: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    created_at: datetime


class CompanyPageResponse(BaseModel):
    items: list[MatchedCompanyResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CompanyStatsResponse(BaseModel):
    total_companies: int
    matched_companies: int
    startups: int
    avg_match_score: float
    by_state: dict[str, int]
    by_year: dict[int, int]
    last_scrape: Optional[datetime]
