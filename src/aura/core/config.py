from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaxAura"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taxaura"
    max_upload_size_mb: int = Field(default=10, ge=1, le=25)
    max_documents_per_user: int = Field(default=50, ge=1)
    document_worker_enabled: bool = True
    worker_poll_seconds: float = Field(default=3, ge=0.1)
    ai_mode: Literal["extractive", "gemini"] = "gemini"
    ai_timeout_seconds: float = Field(default=45, ge=1, le=300)
    chroma_mode: Literal["http", "disabled"] = "http"
    chroma_host: str = "chroma"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_ssl: bool = False
    upload_directory: Path = Path("storage/uploads")
    frontend_directory: Path = Path("frontend")
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    n8n_webhook_url: str | None = None
    n8n_webhook_secret: str | None = None
    tesseract_cmd: str | None = None
    environment: Literal["development", "test", "production"] = "development"
    jwt_secret_key: str = "replace-this-with-a-long-random-secret"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ]
    allowed_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1", "testserver"]

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def empty_api_key(cls, value):
        return value or None

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return value.replace(prefix, "postgresql+asyncpg://", 1)
        return value

    @field_validator("allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        if self.environment == "production" and self.jwt_secret_key.startswith("replace-this"):
            raise ValueError("JWT_SECRET_KEY must be changed in production.")
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters.")
        if self.n8n_webhook_url and not self.n8n_webhook_secret:
            raise ValueError("N8N_WEBHOOK_SECRET is required when N8N_WEBHOOK_URL is configured.")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
