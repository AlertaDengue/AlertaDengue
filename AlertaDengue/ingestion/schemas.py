from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunError(BaseModel):
    """
    Error payload stored in ingestion.run.errors.

    Parameters
    ----------
    ts : datetime
        Error timestamp (UTC recommended).
    step : str
        Pipeline step name (e.g. "stage", "merge").
    code : str
        Short machine-friendly error code.
    message : str
        Human-friendly message.
    context : dict[str, Any]
        Extra structured details (optional).
    """

    ts: datetime = Field(default_factory=datetime.utcnow)
    step: str
    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class RunMetadata(BaseModel):
    """
    Metadata payload stored in ingestion.run.metadata.
    """

    date_formats: dict[str, str | None] = Field(default_factory=dict)
    source_columns: list[str] = Field(default_factory=list)
    se_range: dict[str, int] | None = None
    notes: list[str] = Field(default_factory=list)

    duplicates_removed: int = Field(default=0, ge=0)
    rows_inserted: int = Field(default=0, ge=0)
    rows_updated: int = Field(default=0, ge=0)


SourceFormat = Literal["dbf", "csv", "parquet"]
RunStatus = Literal[
    "detected",
    "queued",
    "staging",
    "staged",
    "merging",
    "completed",
    "failed",
]
