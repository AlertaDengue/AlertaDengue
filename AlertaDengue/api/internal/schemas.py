# api/internal/schemas.py

from datetime import date

from pydantic import BaseModel, Field


class NotificationQueryParams(BaseModel):
    municipio_geocodigo: int | None = None
    cid10: str | None = Field(default=None, max_length=5)
    year: int | None = None
    epiweek_start: int | None = Field(default=None, ge=1, le=53)
    epiweek_end: int | None = Field(default=None, ge=1, le=53)
    date_start: date | None = None
    date_end: date | None = None
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)
    include_count: bool = False
