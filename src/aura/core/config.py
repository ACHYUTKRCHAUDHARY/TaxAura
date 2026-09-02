from pathlib import Path
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaxAura"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taxaura"
    max_upload_size_mb: int = 10
    upload_directory: Path = Path("storage/uploads")
    frontend_directory: Path = Path("frontend")
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    n8n_webhook_url: str | None = None
    n8n_webhook_secret: str | None = None
    tesseract_cmd: str | None = None
    environment: str = "development"
    jwt_secret_key: str = "replace-this-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ]
    allowed_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1", "testserver"]

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
