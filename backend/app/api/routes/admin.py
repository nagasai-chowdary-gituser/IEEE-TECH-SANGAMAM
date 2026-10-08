from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.admin import AdminOverview
from app.services.admin import build_overview, unblock

router = APIRouter()


@router.get("/admin/overview", response_model=AdminOverview)
def admin_overview(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminOverview:
    return build_overview(db, settings)


@router.delete("/admin/ai-blocks/{block_id}")
def admin_unblock(block_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    unblock(db, block_id)
    return {"status": "unblocked"}
