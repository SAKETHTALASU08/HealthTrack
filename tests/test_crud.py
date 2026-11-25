"""Unit tests for the CRUD layer (direct DB calls, no HTTP).

Tests:
- create_symptom_log stores all fields
- get_symptoms_for_patient returns empty list for unknown patient
- get_symptoms_for_patient returns logs in ascending timestamp order
- get_daily_trends computes correct per-day averages
- get_insights returns expected shape
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import crud
from app.schemas import SymptomLogCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(
    patient_id="p1",
    description="Headache",
    severity=5,
    days_ago=0,
) -> SymptomLogCreate:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago, seconds=1)
    return SymptomLogCreate(
        patient_id=patient_id,
        description=description,
        severity=severity,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# create_symptom_log
# ---------------------------------------------------------------------------

class TestCreateSymptomLog:

    def test_creates_record_with_correct_fields(self, db_session):
        payload = _make_payload(patient_id="alice", description="Nausea", severity=7)
        log = crud.create_symptom_log(db_session, payload)

        assert log.id is not None
        assert log.patient_id == "alice"
        assert log.description == "Nausea"
        assert log.severity == 7
        # Timestamp should be timezone-aware
        assert log.timestamp.tzinfo is not None

    def test_server_sets_timestamp_when_not_provided(self, db_session):
        payload = SymptomLogCreate(
            patient_id="bob",
            description="Fatigue",
            severity=3,
        )
        before = datetime.now(timezone.utc)
        log = crud.create_symptom_log(db_session, payload)
        after = datetime.now(timezone.utc)

        assert before <= log.timestamp <= after

    def test_five_logs_have_unique_timestamps(self, db_session):
        """Five logs created with explicit microsecond-spaced timestamps must all persist."""
        base = datetime.now(timezone.utc) - timedelta(days=5)
        logs = []
        for i in range(5):
            payload = SymptomLogCreate(
                patient_id="carol",
                description=f"Symptom {i}",
                severity=i + 1,
                timestamp=base + timedelta(microseconds=i * 100),
            )
            logs.append(crud.create_symptom_log(db_session, payload))

        ids = [l.id for l in logs]
        assert len(set(ids)) == 5, "All five logs must have distinct IDs"
        timestamps = [l.timestamp for l in logs]
        assert len(set(timestamps)) == 5, "All five timestamps must be distinct"


# ---------------------------------------------------------------------------
# get_symptoms_for_patient
# ---------------------------------------------------------------------------

class TestGetSymptomsForPatient:

    def test_empty_list_for_unknown_patient(self, db_session):
        result = crud.get_symptoms_for_patient(db_session, "nobody")
        assert result == []

    def test_ascending_order(self, db_session):
        base = datetime.now(timezone.utc) - timedelta(days=2)
        # Insert in reverse order
        for i in [3, 1, 2]:
            crud.create_symptom_log(db_session, _make_payload(
                patient_id="dave",
                severity=5,
                days_ago=0,
            ) if False else SymptomLogCreate(
                patient_id="dave",
                description="x",
                severity=5,
                timestamp=base + timedelta(hours=i),
            ))

        logs = crud.get_symptoms_for_patient(db_session, "dave")
        ts_list = [l.timestamp for l in logs]
        assert ts_list == sorted(ts_list)

    def test_days_filter_excludes_old_logs(self, db_session):
        old = SymptomLogCreate(
            patient_id="eve",
            description="Old",
            severity=2,
            timestamp=datetime.now(timezone.utc) - timedelta(days=20),
        )
        new = SymptomLogCreate(
            patient_id="eve",
            description="New",
            severity=6,
            timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        )
        crud.create_symptom_log(db_session, old)
        crud.create_symptom_log(db_session, new)

        result = crud.get_symptoms_for_patient(db_session, "eve", days=7)
        assert len(result) == 1
        assert result[0].description == "New"

    def test_patient_isolation(self, db_session):
        crud.create_symptom_log(db_session, _make_payload(patient_id="A"))
        crud.create_symptom_log(db_session, _make_payload(patient_id="B"))

        a_logs = crud.get_symptoms_for_patient(db_session, "A")
        b_logs = crud.get_symptoms_for_patient(db_session, "B")

        assert all(l.patient_id == "A" for l in a_logs)
        assert all(l.patient_id == "B" for l in b_logs)
        assert len(a_logs) == 1
        assert len(b_logs) == 1


# ---------------------------------------------------------------------------
# get_daily_trends
# ---------------------------------------------------------------------------

class TestGetDailyTrends:

    def test_empty_trends_for_unknown_patient(self, db_session):
        result = crud.get_daily_trends(db_session, "nobody")
        assert result == []

    def test_30_day_window_excludes_older_logs(self, db_session):
        # 35-day-old log – outside the 30-day window
        crud.create_symptom_log(db_session, SymptomLogCreate(
            patient_id="fred",
            description="Old",
            severity=9,
            timestamp=datetime.now(timezone.utc) - timedelta(days=35),
        ))
        # Recent log – inside the window
        crud.create_symptom_log(db_session, SymptomLogCreate(
            patient_id="fred",
            description="Recent",
            severity=3,
            timestamp=datetime.now(timezone.utc) - timedelta(days=5),
        ))

        result = crud.get_daily_trends(db_session, "fred", days=30)
        avg_values = [r["average_severity"] for r in result]
        assert 9.0 not in avg_values
        assert 3.0 in avg_values

    def test_daily_average_correct(self, db_session):
        base = datetime.now(timezone.utc) - timedelta(days=10)
        day = base.replace(hour=0, minute=0, second=0, microsecond=0)

        crud.create_symptom_log(db_session, SymptomLogCreate(
            patient_id="gina", description="A", severity=4,
            timestamp=day + timedelta(hours=8),
        ))
        crud.create_symptom_log(db_session, SymptomLogCreate(
            patient_id="gina", description="B", severity=6,
            timestamp=day + timedelta(hours=16),
        ))

        result = crud.get_daily_trends(db_session, "gina", days=30)
        assert len(result) == 1
        assert result[0]["average_severity"] == 5.0
        assert result[0]["entry_count"] == 2

    def test_trends_sorted_ascending_by_date(self, db_session):
        for d in [5, 1, 3]:
            crud.create_symptom_log(db_session, SymptomLogCreate(
                patient_id="hank", description="x", severity=5,
                timestamp=datetime.now(timezone.utc) - timedelta(days=d),
            ))
        result = crud.get_daily_trends(db_session, "hank", days=30)
        dates = [r["date"] for r in result]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# get_insights
# ---------------------------------------------------------------------------

class TestGetInsights:

    def test_empty_insights_for_new_patient(self, db_session):
        result = crud.get_insights(db_session, "nobody")
        assert result["total_entries"] == 0
        assert result["overall_average_severity"] is None
        assert result["highest_severity_entry"] is None
        assert result["trend_direction"] == "insufficient_data"

    def test_total_and_average(self, db_session):
        for sev in [2, 4, 6]:
            crud.create_symptom_log(db_session, _make_payload(patient_id="iris", severity=sev))

        result = crud.get_insights(db_session, "iris")
        assert result["total_entries"] == 3
        assert result["overall_average_severity"] == pytest.approx(4.0)

    def test_highest_severity_entry(self, db_session):
        for sev in [3, 9, 5]:
            crud.create_symptom_log(db_session, _make_payload(patient_id="jack", severity=sev))

        result = crud.get_insights(db_session, "jack")
        assert result["highest_severity_entry"].severity == 9
