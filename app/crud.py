"""Database access functions (CRUD layer).

No business logic lives here beyond building queries; all validation
happens in the Pydantic schemas before these functions are called.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import SymptomLog
from app.schemas import SymptomLogCreate


def create_symptom_log(db: Session, payload: SymptomLogCreate) -> SymptomLog:
    """Persist a new SymptomLog and return the created ORM instance.

    If the caller supplies a ``timestamp``, that value is stored verbatim
    (useful for seeding historical data). Otherwise the server sets the
    current UTC time.

    Args:
        db: Active SQLAlchemy session.
        payload: Validated creation schema.

    Returns:
        The newly created :class:`SymptomLog` with its auto-assigned ``id``.
    """
    ts = payload.timestamp
    if ts is None:
        ts = datetime.now(timezone.utc)
    elif ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    log = SymptomLog(
        patient_id=payload.patient_id,
        description=payload.description,
        severity=payload.severity,
        timestamp=ts,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_symptoms_for_patient(
    db: Session,
    patient_id: str,
    days: int | None = None,
) -> list[SymptomLog]:
    """Return all SymptomLogs for *patient_id*, sorted by timestamp ascending.

    Args:
        db: Active SQLAlchemy session.
        patient_id: The patient whose logs to retrieve.
        days: If provided, limit results to the last *days* days.

    Returns:
        Ordered list of :class:`SymptomLog` objects (may be empty).
    """
    query = db.query(SymptomLog).filter(SymptomLog.patient_id == patient_id)

    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(SymptomLog.timestamp >= cutoff)

    return query.order_by(SymptomLog.timestamp.asc()).all()


def get_daily_trends(
    db: Session,
    patient_id: str,
    days: int = 30,
) -> list[dict]:
    """Compute average severity per calendar day for the last *days* days.

    Days with no data are omitted from the result. Dates are expressed in
    UTC so they are consistent regardless of server locale.

    Args:
        db: Active SQLAlchemy session.
        patient_id: The patient to aggregate.
        days: Window size in days (default 30).

    Returns:
        List of dicts with keys ``date`` (str), ``average_severity`` (float),
        and ``entry_count`` (int), sorted by ``date`` ascending.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            func.date(SymptomLog.timestamp).label("date"),
            func.avg(SymptomLog.severity).label("avg_severity"),
            func.count(SymptomLog.id).label("entry_count"),
        )
        .filter(
            SymptomLog.patient_id == patient_id,
            SymptomLog.timestamp >= cutoff,
        )
        .group_by(func.date(SymptomLog.timestamp))
        .order_by(func.date(SymptomLog.timestamp).asc())
        .all()
    )

    return [
        {
            "date": str(row.date),
            "average_severity": round(float(row.avg_severity), 2),
            "entry_count": row.entry_count,
        }
        for row in rows
    ]


def get_insights(db: Session, patient_id: str) -> dict:
    """Compute aggregate insights for the insights panel.

    Args:
        db: Active SQLAlchemy session.
        patient_id: The patient to aggregate.

    Returns:
        Dict with total_entries, overall_average_severity,
        highest_severity_entry, last_7_days_avg, prev_7_days_avg,
        and trend_direction.
    """
    now = datetime.now(timezone.utc)
    all_logs = get_symptoms_for_patient(db, patient_id)

    total_entries = len(all_logs)
    overall_average_severity = (
        round(sum(l.severity for l in all_logs) / total_entries, 2)
        if total_entries
        else None
    )

    highest_severity_entry = (
        max(all_logs, key=lambda l: l.severity) if all_logs else None
    )

    # Last 7 days vs previous 7 days
    cutoff_7 = now - timedelta(days=7)
    cutoff_14 = now - timedelta(days=14)

    last_7 = [l for l in all_logs if l.timestamp >= cutoff_7]
    prev_7 = [l for l in all_logs if cutoff_14 <= l.timestamp < cutoff_7]

    last_7_avg = round(sum(l.severity for l in last_7) / len(last_7), 2) if last_7 else None
    prev_7_avg = round(sum(l.severity for l in prev_7) / len(prev_7), 2) if prev_7 else None

    if last_7_avg is None or prev_7_avg is None:
        trend_direction = "insufficient_data"
    elif last_7_avg > prev_7_avg:
        trend_direction = "up"
    elif last_7_avg < prev_7_avg:
        trend_direction = "down"
    else:
        trend_direction = "stable"

    return {
        "total_entries": total_entries,
        "overall_average_severity": overall_average_severity,
        "highest_severity_entry": highest_severity_entry,
        "last_7_days_avg": last_7_avg,
        "prev_7_days_avg": prev_7_avg,
        "trend_direction": trend_direction,
    }
