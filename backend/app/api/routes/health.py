from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.analysis import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    database_state = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_state = "error"
    return HealthResponse(
        status="ok" if database_state == "ok" else "degraded",
        service="docuverify-api",
        environment=settings.app_env,
        database=database_state,
    )
