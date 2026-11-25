"""Pydantic request/response schemas with strict validation.

Validation rules mirror the README contract and are enforced *before*
any database interaction.
"""

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import settings

# Safe charset for patient IDs: letters, digits, hyphen, underscore.
_PATIENT_ID_RE = re.compile(r"^[A-Za-z0-9\-_]+$")


class SymptomLogCreate(BaseModel):
    """Schema for creating a new SymptomLog entry.

    All validation is intentionally strict:
    - ``patient_id`` must match the safe charset.
    - ``description`` is stripped of leading/trailing whitespace.
    - ``severity`` must be an integer in [1, 10]; strings, floats, booleans,
      and ``null`` are all rejected.
    - ``timestamp`` is optional; when supplied it must not be in the future.
    """

    patient_id: str = Field(..., min_length=1, max_length=settings.patient_id_max_len)
    description: str = Field(..., min_length=1, max_length=settings.description_max_len)
    severity: int = Field(..., ge=settings.severity_min, le=settings.severity_max)
    timestamp: datetime | None = Field(
        default=None,
        description="Optional UTC timestamp for seeding; must not be in the future.",
    )

    @field_validator("patient_id")
    @classmethod
    def patient_id_safe_charset(cls, v: str) -> str:
        """Reject patient IDs containing characters outside [A-Za-z0-9\\-_]."""
        v = v.strip()
        if not v:
            raise ValueError("patient_id must not be empty or whitespace-only")
        if not _PATIENT_ID_RE.match(v):
            raise ValueError(
                "patient_id may only contain letters, digits, hyphens, and underscores"
            )
        return v

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        """Strip whitespace and reject empty descriptions."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("description must not be empty or whitespace-only")
        return stripped

    @field_validator("severity", mode="before")
    @classmethod
    def severity_strict_int(cls, v: Any) -> int:
        """Reject booleans, floats, strings, and null for severity."""
        if isinstance(v, bool):
            raise ValueError("severity must be an integer, not a boolean")
        if v is None:
            raise ValueError("severity is required")
        if isinstance(v, float):
            raise ValueError("severity must be a whole integer, not a float")
        if isinstance(v, str):
            raise ValueError("severity must be an integer, not a string")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_not_future(cls, v: datetime | None) -> datetime | None:
        """Reject timestamps that lie in the future."""
        if v is None:
            return v
        # Make timezone-aware if naive (assume UTC)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if v > now_utc:
            raise ValueError("timestamp must not be in the future")
        return v

    @model_validator(mode="before")
    @classmethod
    def reject_missing_required_fields(cls, data: Any) -> Any:
        """Provide clearer error messages for missing required fields."""
        if isinstance(data, dict):
            if "severity" not in data:
                raise ValueError("severity is required")
        return data


class SymptomLogResponse(BaseModel):
    """Schema returned by the API for a single SymptomLog."""

    id: int
    patient_id: str
    description: str
    severity: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class SymptomLogCreateResponse(BaseModel):
    """Envelope returned on successful POST /api/symptoms."""

    message: str
    data: SymptomLogResponse


class TrendPoint(BaseModel):
    """Daily average severity for the trends endpoint."""

    date: str  # ISO-8601 date string, e.g. "2024-01-15"
    average_severity: float
    entry_count: int


class TrendResponse(BaseModel):
    """Full response for GET /api/patients/{patient_id}/trends."""

    patient_id: str
    days: int
    trends: list[TrendPoint]


class InsightsResponse(BaseModel):
    """Aggregate stats for the insights panel."""

    total_entries: int
    overall_average_severity: float | None
    highest_severity_entry: SymptomLogResponse | None
    last_7_days_avg: float | None
    prev_7_days_avg: float | None
    trend_direction: str  # "up", "down", "stable", or "insufficient_data"


class ErrorDetail(BaseModel):
    """Single field-level error."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Consistent error envelope used for all 4xx/5xx responses."""

    error: str
    details: list[ErrorDetail] | None = None
