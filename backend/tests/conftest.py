from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_ROOT = Path(__file__).resolve().parent / "_tmp"
TEST_ROOT.mkdir(exist_ok=True)
db_path = TEST_ROOT / "test.db"
if db_path.exists():
    try:
        db_path.unlink()
    except OSError:
        pass
(TEST_ROOT / "uploads").mkdir(exist_ok=True)
(TEST_ROOT / "processed").mkdir(exist_ok=True)

os.environ.setdefault("APP_ENV", "test")
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["PROCESSED_DIR"] = str(TEST_ROOT / "processed")
os.environ["MAX_UPLOAD_SIZE_MB"] = "5"
os.environ["CORS_ORIGINS"] = "http://testserver"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["AI_API_KEY"] = ""
os.environ["AI_PROVIDER"] = ""
os.environ["PAN_API_KEY"] = ""
os.environ["PAN_API_SECRET"] = ""
os.environ["GST_IN_CHECK"] = ""
os.environ["DEMO_API_TOKEN"] = "test-demo-token"
os.environ["AUTH_SECRET"] = "test-auth-secret"
os.environ["AUTH_USER_USERNAME"] = "user"
os.environ["AUTH_USER_PASSWORD"] = "user123"
os.environ["AUTH_ADMIN_USERNAME"] = "admin"
os.environ["AUTH_ADMIN_PASSWORD"] = "admin123"

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.bootstrap import ensure_storage_directories, init_database
from app.main import app

ensure_storage_directories()
init_database()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        test_client.headers.update({"X-Demo-Token": "test-demo-token"})
        yield test_client


@pytest.fixture
def anonymous_client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
