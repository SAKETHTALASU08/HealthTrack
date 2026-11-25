"""SQLAlchemy ORM models for HealthTrack."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base


class UTCDateTime(TypeDecorator):
    """Store datetimes in UTC and always return timezone-aware UTC datetimes.

    SQLite does not preserve timezone offsets on DATETIME columns; this
    decorator normalizes values to UTC on write and re-attaches
    ``timezone.utc`` on read so callers always receive aware datetimes.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class SymptomLog(Base):
    """A single patient-reported symptom entry.

    Attributes:
        id: Auto-incremented primary key.
        patient_id: Opaque patient identifier (letters, digits, ``-``, ``_``).
        description: Free-text symptom description (max 500 chars).
        severity: Patient-reported severity on a scale of 1-10.
        timestamp: UTC datetime when the symptom was recorded; set
            server-side by default to :func:`datetime.now(timezone.utc)`.
    """

    __tablename__ = "symptom_logs"

    # DB-level constraint ensures severity is always 1-10 even if the
    # application layer is bypassed.
    __table_args__ = (
        CheckConstraint(
            f"severity >= {settings.severity_min} AND severity <= {settings.severity_max}",
            name="ck_severity_range",
        ),
        Index("ix_symptom_logs_patient_id", "patient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[str] = mapped_column(
        String(settings.patient_id_max_len), nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(settings.description_max_len), nullable=False
    )
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
