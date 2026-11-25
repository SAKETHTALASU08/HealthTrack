"""API-level tests using FastAPI TestClient.

Covers:
- Happy-path POST /api/symptoms → 201
- All invalid input cases → 422 with meaningful messages
- 5+ logs for one patient stored and retrieved with unique timestamps
- GET returns ascending order even when inserted out of order
- Patient isolation (patient A ≠ patient B)
- Trends endpoint computes correct daily averages and respects the 30-day window
- XSS-style and SQL-injection-style payloads are stored literally
- Health check endpoint
- Future timestamp rejection
"""

from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/symptoms – happy path
# ---------------------------------------------------------------------------

class TestCreateSymptom:
    def test_valid_create_returns_201_and_body(self, client):
        payload = {
            "patient_id": "alice",
            "description": "Headache",
            "severity": 5,
        }
        res = client.post("/api/symptoms", json=payload)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["message"] == "Symptom logged successfully"
        data = body["data"]
        assert data["patient_id"] == "alice"
        assert data["description"] == "Headache"
        assert data["severity"] == 5
        assert "id" in data
        assert "timestamp" in data

    def test_optional_timestamp_accepted(self, client):
        ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        res = client.post("/api/symptoms", json={
            "patient_id": "bob",
            "description": "Nausea",
            "severity": 3,
            "timestamp": ts,
        })
        assert res.status_code == 201
        # Timestamp in response must match what we sent (strip microseconds for tolerance)
        returned_ts = res.json()["data"]["timestamp"]
        # Both should parse to roughly the same time
        returned_dt = datetime.fromisoformat(returned_ts.replace("Z", "+00:00"))
        sent_dt = datetime.fromisoformat(ts)
        assert abs((returned_dt - sent_dt).total_seconds()) < 2

    def test_description_is_stripped(self, client):
        res = client.post("/api/symptoms", json={
            "patient_id": "alice",
            "description": "  Fatigue  ",
            "severity": 4,
        })
        assert res.status_code == 201
        assert res.json()["data"]["description"] == "Fatigue"


# ---------------------------------------------------------------------------
# POST /api/symptoms – validation errors
# ---------------------------------------------------------------------------

class TestCreateSymptomValidation:

    def _post(self, client, payload):
        return client.post("/api/symptoms", json=payload)

    def _assert_422(self, res, field_hint=None):
        assert res.status_code == 422, res.text
        body = res.json()
        assert "error" in body
        assert "details" in body
        if field_hint:
            fields = [d["field"] for d in body["details"]]
            assert any(field_hint in f for f in fields), (
                f"Expected field '{field_hint}' in {fields}"
            )

    # ── description ──────────────────────────────────────────
    def test_empty_description_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "", "severity": 5})
        self._assert_422(res, "description")

    def test_whitespace_only_description_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "   ", "severity": 5})
        self._assert_422(res, "description")

    def test_description_too_long_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "x" * 501, "severity": 5})
        self._assert_422(res, "description")

    def test_missing_description_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "severity": 5})
        assert res.status_code == 422

    # ── severity ──────────────────────────────────────────────
    def test_severity_zero_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": 0})
        self._assert_422(res, "severity")

    def test_severity_11_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": 11})
        self._assert_422(res, "severity")

    def test_severity_negative_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": -1})
        self._assert_422(res, "severity")

    def test_severity_string_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": "abc"})
        self._assert_422(res, "severity")

    def test_severity_float_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": 5.5})
        self._assert_422(res, "severity")

    def test_severity_null_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": None})
        self._assert_422(res, "severity")

    def test_severity_boolean_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain", "severity": True})
        self._assert_422(res, "severity")

    def test_missing_severity_rejected(self, client):
        res = self._post(client, {"patient_id": "alice", "description": "Pain"})
        assert res.status_code == 422

    # ── patient_id ────────────────────────────────────────────
    def test_empty_patient_id_rejected(self, client):
        res = self._post(client, {"patient_id": "", "description": "Pain", "severity": 5})
        self._assert_422(res, "patient_id")

    def test_patient_id_too_long_rejected(self, client):
        res = self._post(client, {"patient_id": "a" * 65, "description": "Pain", "severity": 5})
        self._assert_422(res, "patient_id")

    def test_patient_id_invalid_chars_rejected(self, client):
        res = self._post(client, {"patient_id": "alice@evil.com", "description": "Pain", "severity": 5})
        self._assert_422(res, "patient_id")

    def test_patient_id_space_rejected(self, client):
        res = self._post(client, {"patient_id": "alice bob", "description": "Pain", "severity": 5})
        self._assert_422(res, "patient_id")

    # ── timestamp ─────────────────────────────────────────────
    def test_future_timestamp_rejected(self, client):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        res = self._post(client, {
            "patient_id": "alice",
            "description": "Pain",
            "severity": 5,
            "timestamp": future,
        })
        self._assert_422(res, "timestamp")

    # ── XSS / SQL injection payloads are stored safely ────────
    def test_xss_payload_stored_literally(self, client):
        xss = "<script>alert('xss')</script>"
        res = self._post(client, {"patient_id": "alice", "description": xss, "severity": 3})
        assert res.status_code == 201
        assert res.json()["data"]["description"] == xss

    def test_sql_injection_payload_stored_safely(self, client):
        sql = "'; DROP TABLE symptom_logs; --"
        res = self._post(client, {"patient_id": "alice", "description": sql, "severity": 2})
        assert res.status_code == 201
        assert res.json()["data"]["description"] == sql

    def test_html_entity_payload_stored_literally(self, client):
        html = '<img src=x onerror="alert(1)">'
        res = self._post(client, {"patient_id": "alice", "description": html, "severity": 1})
        assert res.status_code == 201
        assert res.json()["data"]["description"] == html


# ---------------------------------------------------------------------------
# GET /api/patients/{patient_id}/symptoms
# ---------------------------------------------------------------------------

class TestGetPatientSymptoms:

    def _create(self, client, patient_id, description, severity, ts=None):
        payload = {"patient_id": patient_id, "description": description, "severity": severity}
        if ts:
            payload["timestamp"] = ts
        return client.post("/api/symptoms", json=payload)

    def test_empty_list_for_unknown_patient(self, client):
        res = client.get("/api/patients/nobody/symptoms")
        assert res.status_code == 200
        assert res.json() == []

    def test_five_logs_stored_and_retrieved(self, client):
        """Five logs for one patient must all be stored with unique timestamps."""
        base = datetime.now(timezone.utc) - timedelta(days=5)
        for i in range(5):
            ts = (base + timedelta(seconds=i)).isoformat()
            r = self._create(client, "carol", f"Symptom {i}", i + 1, ts=ts)
            assert r.status_code == 201, r.text

        res = client.get("/api/patients/carol/symptoms")
        assert res.status_code == 200
        logs = res.json()
        assert len(logs) == 5
        # All IDs unique → distinct rows
        ids = [l["id"] for l in logs]
        assert len(set(ids)) == 5

    def test_ascending_order_even_when_inserted_out_of_order(self, client):
        """Logs inserted in reverse chronological order must come back ascending."""
        base = datetime.now(timezone.utc) - timedelta(days=3)
        timestamps = [
            (base + timedelta(hours=3)).isoformat(),
            (base + timedelta(hours=1)).isoformat(),
            (base + timedelta(hours=2)).isoformat(),
        ]
        for ts in timestamps:
            self._create(client, "dave", "Pain", 5, ts=ts)

        res = client.get("/api/patients/dave/symptoms")
        logs = res.json()
        ts_list = [l["timestamp"] for l in logs]
        assert ts_list == sorted(ts_list), "Logs not returned in ascending timestamp order"

    def test_patient_isolation(self, client):
        """Patient A must never see patient B's logs."""
        self._create(client, "patA", "Cough", 3)
        self._create(client, "patB", "Fever", 7)

        res_a = client.get("/api/patients/patA/symptoms")
        res_b = client.get("/api/patients/patB/symptoms")

        logs_a = res_a.json()
        logs_b = res_b.json()

        assert all(l["patient_id"] == "patA" for l in logs_a)
        assert all(l["patient_id"] == "patB" for l in logs_b)
        assert len(logs_a) == 1
        assert len(logs_b) == 1

    def test_days_filter(self, client):
        """?days=N should only return logs within the last N days."""
        old_ts = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        new_ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self._create(client, "eve", "Old symptom", 2, ts=old_ts)
        self._create(client, "eve", "Recent symptom", 6, ts=new_ts)

        res = client.get("/api/patients/eve/symptoms?days=7")
        logs = res.json()
        assert len(logs) == 1
        assert logs[0]["description"] == "Recent symptom"


# ---------------------------------------------------------------------------
# GET /api/patients/{patient_id}/trends
# ---------------------------------------------------------------------------

class TestTrends:

    def _create(self, client, patient_id, severity, days_ago):
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        client.post("/api/symptoms", json={
            "patient_id": patient_id,
            "description": "Test",
            "severity": severity,
            "timestamp": ts,
        })

    def test_empty_trends_for_unknown_patient(self, client):
        res = client.get("/api/patients/nobody/trends")
        assert res.status_code == 200
        assert res.json()["trends"] == []

    def test_30_day_window_excludes_older_logs(self, client):
        self._create(client, "fred", 8, days_ago=35)  # outside window
        self._create(client, "fred", 4, days_ago=5)   # inside window

        res = client.get("/api/patients/fred/trends?days=30")
        body = res.json()
        avg_values = [t["average_severity"] for t in body["trends"]]
        assert 8.0 not in avg_values, "35-day-old log should be excluded"
        assert 4.0 in avg_values

    def test_daily_average_computed_correctly(self, client):
        """Two logs on the same day should average to their mean."""
        # Anchor to the same UTC day: 10 days ago, different hours
        base = datetime.now(timezone.utc) - timedelta(days=10)
        ts1 = base.replace(hour=8, minute=0, second=0, microsecond=0).isoformat()
        ts2 = base.replace(hour=20, minute=0, second=0, microsecond=1000).isoformat()

        client.post("/api/symptoms", json={"patient_id": "gina", "description": "A", "severity": 4, "timestamp": ts1})
        client.post("/api/symptoms", json={"patient_id": "gina", "description": "B", "severity": 6, "timestamp": ts2})

        res = client.get("/api/patients/gina/trends?days=30")
        body = res.json()
        assert len(body["trends"]) == 1
        point = body["trends"][0]
        assert point["average_severity"] == 5.0
        assert point["entry_count"] == 2

    def test_trends_sorted_ascending_by_date(self, client):
        for d in [5, 1, 3]:
            self._create(client, "hank", 5, days_ago=d)

        res = client.get("/api/patients/hank/trends?days=30")
        dates = [t["date"] for t in res.json()["trends"]]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# GET /api/patients/{patient_id}/insights
# ---------------------------------------------------------------------------

class TestInsights:

    def _create(self, client, patient_id, severity, days_ago=0):
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago, seconds=1)).isoformat()
        client.post("/api/symptoms", json={
            "patient_id": patient_id,
            "description": "Test",
            "severity": severity,
            "timestamp": ts,
        })

    def test_insights_empty_for_new_patient(self, client):
        res = client.get("/api/patients/nobody/insights")
        assert res.status_code == 200
        body = res.json()
        assert body["total_entries"] == 0
        assert body["overall_average_severity"] is None
        assert body["trend_direction"] == "insufficient_data"

    def test_total_entries_correct(self, client):
        for _ in range(3):
            self._create(client, "iris", 5)
        res = client.get("/api/patients/iris/insights")
        assert res.json()["total_entries"] == 3

    def test_highest_severity_entry(self, client):
        self._create(client, "jack", 3, days_ago=2)
        self._create(client, "jack", 9, days_ago=1)
        self._create(client, "jack", 5)

        res = client.get("/api/patients/jack/insights")
        body = res.json()
        assert body["highest_severity_entry"]["severity"] == 9

    def test_trend_direction_up(self, client):
        # Previous 7 days (days 8-14 ago): low severity
        for d in range(8, 15):
            self._create(client, "karen", 2, days_ago=d)
        # Last 7 days: high severity
        for d in range(1, 8):
            self._create(client, "karen", 8, days_ago=d)

        res = client.get("/api/patients/karen/insights")
        assert res.json()["trend_direction"] == "up"

    def test_trend_direction_down(self, client):
        # Previous 7 days: high
        for d in range(8, 15):
            self._create(client, "leo", 9, days_ago=d)
        # Last 7 days: low
        for d in range(1, 8):
            self._create(client, "leo", 2, days_ago=d)

        res = client.get("/api/patients/leo/insights")
        assert res.json()["trend_direction"] == "down"
