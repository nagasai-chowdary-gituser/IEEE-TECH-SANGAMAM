from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.bootstrap import ensure_storage_directories, init_database
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_settings.cache_clear()
    ensure_storage_directories()
    init_database()
    logger.info("docuverify_api_started env=%s", get_settings().app_env)
    yield


_local_docs = settings.app_env.lower() in {"development", "test"}

app = FastAPI(
    title="DocuVerify API",
    version="0.1.0",
    description="Document forensics API: upload, forensic analysis, evidence fusion, and grounded explanation.",
    lifespan=lifespan,
    docs_url="/docs" if _local_docs else None,
    redoc_url="/redoc" if _local_docs else None,
    openapi_url="/openapi.json" if _local_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-Demo-Token", "Authorization"],
)

app.include_router(api_router, prefix="/api/v1")
