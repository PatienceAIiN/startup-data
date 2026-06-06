import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class StartupIndiaCompany(Base):
    __tablename__ = "startupindia_companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    profile_url: Mapped[str | None] = mapped_column(String(500))
    company_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(200), index=True)
    sector: Mapped[str | None] = mapped_column(String(200), index=True)
    stage: Mapped[str | None] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    badges: Mapped[list | None] = mapped_column(JSONB)
    dpiit_recognised: Mapped[bool] = mapped_column(Boolean, default=False)
    dipp_number: Mapped[str | None] = mapped_column(String(50))
    raw: Mapped[dict | None] = mapped_column(JSONB)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    contact_address: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    twitter_url: Mapped[str | None] = mapped_column(String(500))
    facebook_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    cin_real: Mapped[str | None] = mapped_column(String(50))
    gst: Mapped[str | None] = mapped_column(String(50))
    extras: Mapped[dict | None] = mapped_column(JSONB)
    contact_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ScrapeCursor(Base):
    """Persistent paging cursor per scrape source. One row per source."""
    __tablename__ = "scrape_cursors"

    source: Mapped[str] = mapped_column(String(50), primary_key=True)
    page: Mapped[int] = mapped_column(Integer, default=0)
    exhausted: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(String(500))
