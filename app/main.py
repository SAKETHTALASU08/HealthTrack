"""HealthTrack FastAPI application factory.

This module creates the FastAPI app, registers routers, mounts static
files, and installs a global validation-error handler that normalises
Pydantic 422 errors into the project's :class:`ErrorResponse` shape.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers.symptoms import router as symptoms_router

# ---------------------------------------------------------------------------
# Create all tables on startup (safe to call repeatedly: CREATE IF NOT EXISTS)
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HealthTrack",
    description="Symptom-tracking API for patients and healthcare providers.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic validation errors into a consistent ErrorResponse.

    Each field error is surfaced with a human-readable ``message`` and
    the dot-joined field path so the client can highlight the offending
    input.
    """
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append({"field": field or "body", "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "details": details,
        },
    )


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
app.include_router(symptoms_router, prefix="/api", tags=["symptoms"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"], summary="Service health check")
def health_check() -> dict:
    """Return a simple alive signal.

    Returns:
        ``{"status": "ok"}`` when the service is running.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static files  (must be mounted AFTER routes to avoid shadowing /api/*)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="static", html=True), name="static")
