from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from aura.services import gemini, rag_service


def test_model_uses_server_key_and_bounded_retries(monkeypatch):
    captured = {}
    monkeypatch.setattr(gemini.settings, "gemini_api_key", SecretStr("test-key"))

    def factory(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(gemini, "ChatGoogleGenerativeAI", factory)
    gemini.build_chat_model()
    assert captured["google_api_key"] == "test-key"
    assert captured["max_retries"] == 0
    assert captured["timeout"] == gemini.settings.ai_timeout_seconds


def test_response_text_ignores_non_text_blocks():
    response = SimpleNamespace(
        content=[{"type": "thinking", "text": "internal"}, {"type": "text", "text": "Answer"}]
    )
    assert gemini.response_text(response) == "Answer"


@pytest.mark.asyncio
async def test_rag_generates_from_retrieved_rules(monkeypatch):
    monkeypatch.setattr(rag_service.settings, "ai_mode", "gemini")
    chunk = SimpleNamespace(
        source_name="Official source",
        source_url="https://example.com",
        content="Verified rebate rule",
    )
    monkeypatch.setattr(rag_service, "_retrieve_rules", AsyncMock(return_value=[chunk]))
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="Cited answer")))
    monkeypatch.setattr(rag_service, "build_chat_model", lambda: model)
    result = await rag_service.answer_with_rag("What rebate applies?", None, None)
    assert result.mode == "generated"
    assert result.answer == "Cited answer"
    assert "Verified rebate rule" in str(model.ainvoke.call_args)


@pytest.mark.asyncio
async def test_quota_failure_falls_back_to_excerpts(monkeypatch):
    monkeypatch.setattr(rag_service.settings, "ai_mode", "gemini")
    chunk = SimpleNamespace(
        source_name="Official source", source_url=None, content="Verified rebate rule"
    )
    monkeypatch.setattr(rag_service, "_retrieve_rules", AsyncMock(return_value=[chunk]))
    model = SimpleNamespace(ainvoke=AsyncMock(side_effect=RuntimeError("quota exhausted")))
    monkeypatch.setattr(rag_service, "build_chat_model", lambda: model)
    result = await rag_service.answer_with_rag("What rebate applies?", None, None)
    assert result.mode == "extractive"
    assert "Verified rebate rule" in result.answer


@pytest.mark.asyncio
async def test_private_document_mode_never_calls_gemini(monkeypatch):
    from uuid import uuid4

    monkeypatch.setattr(rag_service.settings, "ai_mode", "gemini")
    monkeypatch.setattr(rag_service, "_retrieve_rules", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        rag_service,
        "_retrieve_documents",
        AsyncMock(return_value=[(SimpleNamespace(content="Private salary"), "salary.pdf")]),
    )
    model_factory = AsyncMock()
    monkeypatch.setattr(rag_service, "build_chat_model", model_factory)
    result = await rag_service.answer_with_rag("salary", uuid4(), None, include_documents=True)
    assert result.mode == "extractive"
    assert "Private salary" in result.answer
    model_factory.assert_not_called()
