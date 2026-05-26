from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartReturn Pro"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://smartreturn_user:smartreturn_password"
        "@localhost:5432/smartreturn_pro"
    )
    secret_key: str = "change-me-local-only"
    access_token_expire_minutes: int = 120
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    file_storage_root: str = "./storage"
    local_agent_base_url: str = "http://127.0.0.1:8765"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
