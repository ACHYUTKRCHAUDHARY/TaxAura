from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from aura.services import vector_store


@pytest.mark.asyncio
async def test_document_query_requires_identity(monkeypatch):
    monkeypatch.setattr(vector_store.settings, "chroma_mode", "http")
    target = MagicMock()
    monkeypatch.setattr(vector_store, "collection", target)
    assert await vector_store.semantic_ids("salary", "documents") == []
    target.assert_not_called()


@pytest.mark.asyncio
async def test_document_query_is_filtered_by_owner(monkeypatch):
    owner, chunk = uuid4(), uuid4()
    monkeypatch.setattr(vector_store.settings, "chroma_mode", "http")
    target = MagicMock()
    target.query.return_value = {"ids": [[str(chunk)]]}
    monkeypatch.setattr(vector_store, "collection", lambda _: target)
    assert await vector_store.semantic_ids("salary", "documents", owner) == [chunk]
    assert target.query.call_args.kwargs["where"] == {"user_id": str(owner)}
