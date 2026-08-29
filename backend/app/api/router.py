from fastapi import APIRouter, Depends

from app.api.deps import require_demo_token
from app.api.routes.auth import router as auth_router
from app.api.routes.compliance import router as compliance_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.signatures import router as signatures_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(documents_router, tags=["documents"], dependencies=[Depends(require_demo_token)])
api_router.include_router(compliance_router, tags=["compliance"], dependencies=[Depends(require_demo_token)])
api_router.include_router(signatures_router, tags=["signatures"], dependencies=[Depends(require_demo_token)])
