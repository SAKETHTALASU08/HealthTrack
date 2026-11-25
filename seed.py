"""Seed script to populate realistic symptom logs for demo purposes.

Inserts ~20 realistic SymptomLog entries over the last 30 days for a
demo patient (``patient-001``) so the trend chart and insights panel
have meaningful data right away.

Usage:
    python seed.py
"""

from datetime import datetime, timedelta, timezone

from app import crud
from app.database import Base, SessionLocal, engine
from app.schemas import SymptomLogCreate

DEMO_PATIENT_ID = "patient-001"

# (days_ago, hour_utc, severity, description)
SEED_ENTRIES: list[tuple[int, int, int, str]] = [
    (29, 9, 4, "Mild morning headache and stiffness"),
    (27, 14, 5, "Tension headache after screen time"),
    (25, 10, 6, "Persistent fatigue and low-grade fever"),
    (24, 18, 7, "Throbbing migraine with light sensitivity"),
    (22, 8, 6, "Morning nausea and dizziness"),
    (20, 15, 5, "Moderate fatigue, improved after rest"),
    (18, 11, 4, "Mild sinus pressure"),
    (16, 13, 6, "Joint ache in knees and wrists"),
    (15, 20, 7, "Sharp headache and neck stiffness"),
    (13, 9, 5, "Moderate sore throat and dry cough"),
    (11, 16, 5, "Continued dry cough, mild chest tightness"),
    (10, 8, 4, "Mild fatigue on waking"),
    (8, 12, 3, "Slight headache, resolved with hydration"),
    (6, 10, 4, "Mild dizziness when standing up"),
    (5, 19, 3, "Occasional dry cough"),
    (4, 9, 2, "Slight residual fatigue"),
    (3, 15, 3, "Mild tension in shoulders and neck"),
    (2, 11, 2, "Minor headache in the afternoon"),
    (1, 8, 2, "Slight morning grogginess"),
    (0, 9, 1, "Feeling mostly recovered, very mild fatigue"),
]


def seed_demo_data(patient_id: str = DEMO_PATIENT_ID) -> int:
    """Create tables if needed and insert demo symptom logs.

    Args:
        patient_id: Target patient identifier for the seeded records.

    Returns:
        Number of entries inserted.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    inserted = 0

    try:
        for idx, (days_ago, hour_utc, severity, description) in enumerate(SEED_ENTRIES):
            ts = (now - timedelta(days=days_ago)).replace(
                hour=hour_utc,
                minute=(idx * 7) % 60,
                second=0,
                microsecond=idx * 1000,
            )
            # Guard against timestamps slightly in the future on day 0
            if ts > now:
                ts = now - timedelta(minutes=idx + 1)

            payload = SymptomLogCreate(
                patient_id=patient_id,
                description=description,
                severity=severity,
                timestamp=ts,
            )
            crud.create_symptom_log(db, payload)
            inserted += 1
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    count = seed_demo_data()
    print(f"Seeded {count} symptom logs for patient '{DEMO_PATIENT_ID}'.")
