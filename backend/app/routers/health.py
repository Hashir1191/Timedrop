from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/ready")
def readiness_check():
    """Report readiness only when the configured database can execute a query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "timedrop-api",
                "checks": {"database": "unavailable"},
            },
        )

    return {
        "status": "ready",
        "service": "timedrop-api",
        "checks": {"database": "ok"},
    }
