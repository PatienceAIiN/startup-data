import uuid
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class ExportFile(Base):
    __tablename__ = "export_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exported_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    file_type: Mapped[str | None] = mapped_column(String(10))
    file_name: Mapped[str | None] = mapped_column(String(500))
    r2_key: Mapped[str | None] = mapped_column(String(500))
    r2_url: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    record_count: Mapped[int | None] = mapped_column(Integer)
    filter_params: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
