from pydantic import BaseModel
from typing import Optional
from datetime import date


class ExportRequest(BaseModel):
    file_type: str
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    state: Optional[str] = None
    is_startup: Optional[bool] = None


class ExportResponse(BaseModel):
    download_url: str
    file_name: str
    record_count: int
    file_size_bytes: int
    expires_in_hours: int = 24
