from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "sqlite:///./docuverify.db"
    upload_dir: str = "./uploads"
    processed_dir: str = "./processed"
    max_upload_size_mb: int = 25
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    tesseract_cmd: str = ""
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 30.0
    pan_api_key: str = ""
    pan_api_secret: str = ""
    pan_api_base_url: str = ""
    pan_sandbox_env: str = "test"
    gst_in_check: str = ""
    demo_api_token: str = ""
    auth_secret: str = "docuverify-dev-auth-secret"
    frontend_origin: str = "http://localhost:3000"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/api/auth/google/callback"
    auth_user_username: str = "user"
    auth_user_password: str = "user123"
    auth_admin_username: str = "admin"
    auth_admin_password: str = "admin123"
    pan_api_timeout_seconds: float = 20.0
    gst_api_timeout_seconds: float = 20.0
    ai_rate_limit_per_minute: int = 20
    ai_rate_limit_daily: int = 200
    ai_rate_limit_ip_per_minute: int = 30
    ai_abuse_spike_per_minute: int = 25
    ai_abuse_fail_streak: int = 8
    ai_abuse_token_hour: int = 80000
    ai_abuse_block_minutes: int = 30
    ai_cache_enabled: bool = True
    ai_cache_ttl_seconds: int = 3600
    ai_usd_per_1k_input: float = 0.00015
    ai_usd_per_1k_output: float = 0.0006

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.app_env.lower() in {"development", "test"}:
            origins.extend(
                [
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "http://localhost:3002",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:3001",
                    "http://127.0.0.1:3002",
                ]
            )
        # Preserve order, drop duplicates.
        return list(dict.fromkeys(origins))

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()

    @property
    def processed_path(self) -> Path:
        return Path(self.processed_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment / .env (cached per process)."""
    return Settings()
