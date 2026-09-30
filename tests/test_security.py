from uuid import uuid4

from aura.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    encoded = hash_password("a-strong-test-password")
    assert encoded != "a-strong-test-password"
    assert verify_password("a-strong-test-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_contains_identity_and_role() -> None:
    user_id = uuid4()
    token = create_access_token(user_id, "USER")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "USER"


def test_legacy_password_hash_fails_closed():
    assert not verify_password("some-password", "legacy-account-reset-required")


def test_advisor_identity_is_not_a_model_argument(monkeypatch):
    from aura.services import tax_advisor_agent

    monkeypatch.setattr(tax_advisor_agent, "build_chat_model", lambda: object())
    monkeypatch.setattr(tax_advisor_agent, "create_react_agent", lambda model, **kwargs: kwargs)
    advisor = tax_advisor_agent.build_tax_advisor(str(uuid4()))
    status_tool = next(tool for tool in advisor["tools"] if tool.name == "get_document_status")
    assert status_tool.args == {}
