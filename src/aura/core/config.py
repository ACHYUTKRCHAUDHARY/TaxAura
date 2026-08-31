from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaxAura"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taxaura"
    max_upload_size_mb: int = 10
    upload_directory: Path = Path("storage/uploads")
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
