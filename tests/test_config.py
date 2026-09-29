import pytest
from pydantic import ValidationError

from aura.core.config import Settings


def test_comma_separated_origin_configuration() -> None:
    settings = Settings(
        allowed_origins="https://app.example.com,https://admin.example.com",
    )
    assert settings.allowed_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_production_rejects_placeholder_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret_key="replace-this-with-a-long-random-secret",
        )


def test_managed_postgres_url_is_normalized():
    assert (
        Settings(database_url="postgres://user:pass@host/db").database_url
        == "postgresql+asyncpg://user:pass@host/db"
    )


def test_cloud_chroma_requires_credentials():
    with pytest.raises(ValidationError):
        Settings(chroma_mode="cloud", chroma_api_key=None, chroma_tenant=None, chroma_database=None)
