import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, Integer, Float, BigInteger, Date, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ZaubaCompany(Base):
    __tablename__ = "zauba_companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cin: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    company_status: Mapped[str | None] = mapped_column(String(100))
    roc_code: Mapped[str | None] = mapped_column(String(50))
    registration_number: Mapped[str | None] = mapped_column(String(100))
    company_category: Mapped[str | None] = mapped_column(String(200))
    company_subcategory: Mapped[str | None] = mapped_column(String(200))
    class_of_company: Mapped[str | None] = mapped_column(String(100))
    date_of_incorporation: Mapped[date | None] = mapped_column(Date, index=True)
    authorised_capital: Mapped[int | None] = mapped_column(BigInteger)
    paid_up_capital: Mapped[int | None] = mapped_column(BigInteger)
    registered_address: Mapped[str | None] = mapped_column(Text)
    listing_status: Mapped[str | None] = mapped_column(String(100))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    scrape_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class DataGovCompany(Base):
    __tablename__ = "datagov_companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cin: Mapped[str | None] = mapped_column(String(50), index=True)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    company_status: Mapped[str | None] = mapped_column(String(100))
    roc_code: Mapped[str | None] = mapped_column(String(50))
    registration_number: Mapped[str | None] = mapped_column(String(100))
    company_category: Mapped[str | None] = mapped_column(String(200))
    date_of_incorporation: Mapped[date | None] = mapped_column(Date)
    state: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    scrape_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class MatchedCompany(Base):
    __tablename__ = "matched_companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zauba_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    datagov_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    cin: Mapped[str | None] = mapped_column(String(50), index=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_method: Mapped[str | None] = mapped_column(String(50))
    company_status: Mapped[str | None] = mapped_column(String(100))
    roc_code: Mapped[str | None] = mapped_column(String(50))
    company_category: Mapped[str | None] = mapped_column(String(200))
    date_of_incorporation: Mapped[date | None] = mapped_column(Date, index=True)
    state: Mapped[str | None] = mapped_column(String(100))
    authorised_capital: Mapped[int | None] = mapped_column(BigInteger)
    paid_up_capital: Mapped[int | None] = mapped_column(BigInteger)
    registered_address: Mapped[str | None] = mapped_column(Text)
    is_startup: Mapped[bool] = mapped_column(Boolean, default=False)
    incorporation_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
