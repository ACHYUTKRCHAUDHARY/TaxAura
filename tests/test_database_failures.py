from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError

from aura import main
from aura.api.dependencies import get_current_user, require_admin
from aura.api.routes import rag
from aura.db.session import get_session


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_is_down(monkeypatch):
    factory = AsyncMock()
    factory.__aenter__.side_effect = SQLAlchemyError("credentials must not leak")
    monkeypatch.setattr(main, "AsyncSessionFactory", lambda: factory)
    response = await main.readiness()
    assert response.status_code == 503
    assert b"credentials" not in response.body


@pytest.mark.asyncio
async def test_rag_database_failures_return_safe_503(monkeypatch):
    session = AsyncMock()

    async def db():
        yield session

    main.app.dependency_overrides[get_session] = db
    main.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    main.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id=uuid4())
    monkeypatch.setattr(
        rag, "answer_with_rag", AsyncMock(side_effect=SQLAlchemyError("private db URL"))
    )
    monkeypatch.setattr(
        rag, "ingest_tax_rule", AsyncMock(side_effect=SQLAlchemyError("private db URL"))
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/v1/knowledge/ask", json={"question": "What rebate applies?"}
            )
            assert response.status_code == 503
            assert "private db URL" not in response.text
            response = await client.post(
                "/api/v1/knowledge/rules",
                json={"source_name": "test source", "content": "Tax guidance " * 10},
            )
            assert response.status_code == 503
            assert "private db URL" not in response.text
            session.rollback.assert_awaited_once()
    finally:
        main.app.dependency_overrides.clear()
