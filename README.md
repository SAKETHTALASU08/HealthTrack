# HealthTrack

A lightweight, production-style symptom-tracking web application built with **FastAPI**, **SQLAlchemy 2.x**, **SQLite**, and **vanilla HTML/CSS/JS** with **Chart.js**. Patients can log symptoms with a 1–10 severity rating, review their chronological history, and visualize 30-day severity trends and insights.

> **Screenshot**
>
> _[Placeholder: Add screenshots of the HealthTrack dashboard in both light mode and dark mode showing the sticky navbar, summary stat cards, severity slider form, 30-day gradient trend chart, and searchable symptom history table.]_

---

## UI Architecture & Highlights

- **Zero-build ES Modules (`/static`):**
  - `index.html` — Semantic HTML5 layout (`<header>`, `<main>`, `<section>`, `<table>` with `<caption>` and `<th scope="col">`)
  - `styles.css` — CSS custom properties design system (teal/slate palette, 12–16px radii, soft shadows, automatic + manual dark mode via `localStorage`, skeleton loaders, reduced-motion support)
  - `utils.js` — Client validation mirroring server rules, human-friendly timestamps, severity badge metadata, safe `localStorage` wrappers
  - `api.js` — Fetch wrapper distinguishing `NetworkError` (with Retry) from `ApiError`
  - `chart.js` — Theme-aware Chart.js line chart with gradient area fill and fixed `0–10` Y-axis
  - `ui.js` — XSS-safe DOM rendering (`textContent` only), top-right toast notifications, alert banners, and slider value bubble
  - `app.js` — State coordination, `Ctrl/Cmd+Enter` form submit shortcut, and last-used Patient ID persistence

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, SQLite
- **Frontend:** Plain HTML5, CSS3, vanilla JavaScript (no build step), Chart.js (via CDN)
- **Testing:** `pytest` + FastAPI `TestClient` with an isolated in-memory SQLite database

---

## Setup & Run

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Seed demo data

Populate ~20 realistic entries over the last 30 days for `patient-001`:

```bash
python seed.py
```

### 4. Start the development server

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Interactive API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 5. Run the test suite

```bash
pytest -v
```

---

## API Reference

### `GET /health`

Simple liveness check.

```bash
curl -s http://127.0.0.1:8000/health
```

```json
{"status": "ok"}
```

---

### `POST /api/symptoms`

Log a new symptom entry.

**Request:**

```bash
curl -s -X POST http://127.0.0.1:8000/api/symptoms \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient-001",
    "description": "Migraine with sensitivity to light",
    "severity": 7
  }'
```

**Success Response (`201 Created`):**

```json
{
  "message": "Symptom logged successfully",
  "data": {
    "id": 1,
    "patient_id": "patient-001",
    "description": "Migraine with sensitivity to light",
    "severity": 7,
    "timestamp": "2026-11-25T09:45:12.123456+00:00"
  }
}
```

**Validation Error Response (`422 Unprocessable Entity`):**

```bash
curl -s -X POST http://127.0.0.1:8000/api/symptoms \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient-001", "description": "   ", "severity": 11}'
```

```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "description",
      "message": "Value error, description must not be empty or whitespace-only"
    },
    {
      "field": "severity",
      "message": "Input should be less than or equal to 10"
    }
  ]
}
```

---

### `GET /api/patients/{patient_id}/symptoms`

Return all symptom logs for a patient sorted by `timestamp` **ascending** (oldest first, newest at the bottom). Supports optional `?days=N` filtering.

```bash
curl -s "http://127.0.0.1:8000/api/patients/patient-001/symptoms?days=30"
```

```json
[
  {
    "id": 1,
    "patient_id": "patient-001",
    "description": "Migraine with sensitivity to light",
    "severity": 7,
    "timestamp": "2026-11-25T09:45:12.123456+00:00"
  }
]
```

---

### `GET /api/patients/{patient_id}/trends?days=30`

Return daily average severity over the requested window (default `30` days, max `365`). Days with no entries are omitted.

```bash
curl -s "http://127.0.0.1:8000/api/patients/patient-001/trends?days=30"
```

```json
{
  "patient_id": "patient-001",
  "days": 30,
  "trends": [
    {
      "date": "2026-11-24",
      "average_severity": 5.5,
      "entry_count": 2
    }
  ]
}
```

---

### `GET /api/patients/{patient_id}/insights`

Return aggregate stats for the insights panel: total entries, overall average severity, highest severity entry, and 7-day trend direction (`up`, `down`, `stable`, or `insufficient_data`).

```bash
curl -s "http://127.0.0.1:8000/api/patients/patient-001/insights"
```

---

## Key Design Decisions & Trade-offs

| Decision | Rationale & Trade-off |
|---|---|
| **FastAPI + Pydantic v2** | Automatic OpenAPI docs, strict type validation before DB writes, and clean dependency injection (`Depends(get_db)`). |
| **SQLite + SQLAlchemy 2.x** | Zero-config local persistence for a single-node demo, with ORM parameterized queries and easy migration path to PostgreSQL via `DATABASE_URL`. Trade-off: not suited for high-concurrency multi-writer production loads. |
| **Server-side UTC timestamps** | Defaulting `timestamp` to `datetime.now(timezone.utc)` prevents client clock skew while still allowing an optional past UTC timestamp for seeding. Displayed in the browser's local timezone. |
| **Defense-in-depth validation** | Client-side JS mirrors rules for immediate UX; Pydantic enforces strict types (rejecting `bool`, `float`, `str`, `null` for `severity`); SQLite `CheckConstraint` enforces `1 <= severity <= 10` at the storage layer. |
| **No authentication** | Intentionally omitted to keep the scope focused on symptom logging and visualization. Not safe for multi-user production without auth. |

---

## Edge Cases Handled

- Empty or whitespace-only `description` (stripped and rejected) and descriptions > 500 chars
- Invalid `severity` values: `0`, `11`, `-1`, `"abc"`, `5.5`, `true`, `null`, or missing field
- Invalid `patient_id`: empty, > 64 chars, or characters outside `[A-Za-z0-9\-_]`
- Future timestamps rejected; naive timestamps normalized to UTC
- Unknown patient returns `200 []` instead of `404`
- XSS payloads (`<script>...`, `<img onerror=...>`) stored literally and rendered safely via `textContent` (never `innerHTML`)
- SQL-injection-like strings stored safely via SQLAlchemy ORM parameterized queries
- Rapid/out-of-order submissions preserve microsecond precision and always sort ascending on retrieval
- Network failures, `4xx`, and `5xx` errors display dismissible banners without clearing user form input

---

## Known Limitations & Next Steps

1. **No authentication or authorization:** Anyone who knows a `patient_id` can read or append logs. Next: add OAuth2/JWT authentication and role-based access control (patient vs. healthcare provider).
2. **No pagination:** `GET /api/patients/{patient_id}/symptoms` returns all matching logs. Next: add cursor- or offset-based pagination (`limit`/`offset`).
3. **SQLite concurrency & migrations:** Next: switch `DATABASE_URL` to PostgreSQL and add Alembic for schema migrations.
4. **Provider views:** Add provider-specific endpoints to manage assigned patient rosters, clinical notes, and CSV/PDF export.

---

## AI Usage

> _Fill in honestly before submitting:_
> - **Tools used:** _[e.g., Antigravity / Claude / ChatGPT / Copilot]_
> - **Which parts they touched:** _[e.g., initial project scaffolding, Pydantic schema validators, Chart.js setup, unit/API tests]_
> - **What I verified or changed afterwards:** _[e.g., reviewed all validation rules, ran `pytest -v` and verified all tests pass, tested XSS payloads and error banners manually in the browser]_
