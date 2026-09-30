from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy.exc import SQLAlchemyError

from aura.services import embeddings, vector_store


@pytest.mark.asyncio
async def test_document_query_requires_identity(monkeypatch):
    embed = AsyncMock()
    monkeypatch.setattr(embeddings, "embed", embed)
    assert await vector_store.retrieve_documents("salary", None, AsyncMock()) == []
    embed.assert_not_called()


@pytest.mark.asyncio
async def test_database_failure_is_not_hidden_as_an_empty_search(monkeypatch):
    monkeypatch.setattr(embeddings, "embed", AsyncMock(return_value=[[1.0] + [0.0] * 383]))
    session = AsyncMock()
    session.scalars.side_effect = SQLAlchemyError("database unavailable")
    with pytest.raises(SQLAlchemyError):
        await vector_store.retrieve_rules("rebate", session)


@pytest.mark.asyncio
async def test_indexing_failure_keeps_source_available(monkeypatch):
    monkeypatch.setattr(
        embeddings, "embed", AsyncMock(side_effect=RuntimeError("model unavailable"))
    )
    chunk = SimpleNamespace(id=uuid4(), content="Salary text", embedding=None)
    assert not await vector_store.index_chunks([chunk])
    assert chunk.embedding is None
    assert chunk.content == "Salary text"
    assert await vector_store.query_vector("salary") is None


@pytest.mark.asyncio
async def test_embeddings_populate_rows_without_a_separate_commit(monkeypatch):
    vector = [1.0] + [0.0] * 383
    monkeypatch.setattr(embeddings, "embed", AsyncMock(return_value=[vector]))
    chunk = SimpleNamespace(content="Salary", embedding=None, embedding_model=None)
    assert await vector_store.index_chunks([chunk])
    assert chunk.embedding == vector
    assert chunk.embedding_model == embeddings.MODEL_ID


def test_local_embeddings_validate_and_normalize(monkeypatch):
    class Model:
        def embed(self, texts, batch_size):
            return [[3.0, 4.0] + [0.0] * 382 for _ in texts]

    monkeypatch.setattr(embeddings, "model", lambda: Model())
    result = embeddings.embed_texts(["sample"])
    assert len(result[0]) == 384
    assert np.linalg.norm(result[0]) == pytest.approx(1)


@pytest.mark.parametrize("bad", [[0.0] * 384, [1.0, 0.0], [float("nan")] * 384])
def test_invalid_embeddings_are_rejected(monkeypatch, bad):
    monkeypatch.setattr(embeddings, "model", lambda: SimpleNamespace(embed=lambda *a, **kw: [bad]))
    with pytest.raises(ValueError):
        embeddings.embed_texts(["sample"])
