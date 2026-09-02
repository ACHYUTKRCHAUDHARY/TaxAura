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
