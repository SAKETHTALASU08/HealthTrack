"""Symptoms router: all /api/symptoms and /api/patients/* endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import (
    InsightsResponse,
    SymptomLogCreate,
    SymptomLogCreateResponse,
    SymptomLogResponse,
    TrendPoint,
    TrendResponse,
)

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


@router.post(
    "/symptoms",
    status_code=status.HTTP_201_CREATED,
    response_model=SymptomLogCreateResponse,
    summary="Log a new symptom entry",
)
def create_symptom(payload: SymptomLogCreate, db: DbDep) -> SymptomLogCreateResponse:
    """Create a new :class:`SymptomLog` entry.

    Returns 201 on success. Pydantic handles 422 for invalid input;
    the exception handler in ``main.py`` formats those as a consistent
    :class:`ErrorResponse`.

    Args:
        payload: Validated request body.
        db: Injected database session.
    """
    log = crud.create_symptom_log(db, payload)
    return SymptomLogCreateResponse(
        message="Symptom logged successfully",
        data=SymptomLogResponse.model_validate(log),
    )


@router.get(
    "/patients/{patient_id}/symptoms",
    response_model=list[SymptomLogResponse],
    summary="List all symptoms for a patient",
)
def get_patient_symptoms(
    patient_id: str,
    db: DbDep,
    days: int | None = Query(default=None, ge=1, description="Limit to last N days"),
) -> list[SymptomLogResponse]:
    """Return all symptom logs for *patient_id*, sorted ascending by timestamp.

    Returns an empty list (200) when the patient has no entries.
    Supports optional ``?days=N`` filter.

    Args:
        patient_id: Path parameter identifying the patient.
        db: Injected database session.
        days: Optional query parameter to filter by recency.
    """
    logs = crud.get_symptoms_for_patient(db, patient_id, days=days)
    return [SymptomLogResponse.model_validate(log) for log in logs]


@router.get(
    "/patients/{patient_id}/trends",
    response_model=TrendResponse,
    summary="Daily average severity trend for a patient",
)
def get_patient_trends(
    patient_id: str,
    db: DbDep,
    days: int = Query(default=30, ge=1, le=365, description="Window in days"),
) -> TrendResponse:
    """Return per-day average severity for the last *days* days.

    Days with no data are omitted. Returns an empty ``trends`` list when
    there is no data in the window.

    Args:
        patient_id: Path parameter identifying the patient.
        db: Injected database session.
        days: Number of days to look back (default 30, max 365).
    """
    trend_data = crud.get_daily_trends(db, patient_id, days=days)
    return TrendResponse(
        patient_id=patient_id,
        days=days,
        trends=[TrendPoint(**point) for point in trend_data],
    )


@router.get(
    "/patients/{patient_id}/insights",
    response_model=InsightsResponse,
    summary="Aggregate insights for a patient",
)
def get_patient_insights(patient_id: str, db: DbDep) -> InsightsResponse:
    """Return aggregate stats for the insights panel.

    Args:
        patient_id: Path parameter identifying the patient.
        db: Injected database session.
    """
    insights = crud.get_insights(db, patient_id)
    highest = insights["highest_severity_entry"]
    return InsightsResponse(
        total_entries=insights["total_entries"],
        overall_average_severity=insights["overall_average_severity"],
        highest_severity_entry=(
            SymptomLogResponse.model_validate(highest) if highest else None
        ),
        last_7_days_avg=insights["last_7_days_avg"],
        prev_7_days_avg=insights["prev_7_days_avg"],
        trend_direction=insights["trend_direction"],
    )
