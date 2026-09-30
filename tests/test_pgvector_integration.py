"""Actual PostgreSQL vector queries; only model inference is deterministic in this suite."""

import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aura.db.models import Document, DocumentChunk, TaxRuleChunk, User
from aura.schemas.rag import TaxRuleIngestRequest
from aura.scripts import reindex
from aura.services import embeddings, rag_service, vector_store
from aura.services.text_processing import split_text

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="No test database configured"
)


def unit(axis=0):
    return [1.0 if i == axis else 0.0 for i in range(384)]


@pytest.mark.asyncio
async def test_cosine_ranking_ownership_and_atomic_cascade(monkeypatch):
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    users = [uuid4(), uuid4()]
    documents = [uuid4(), uuid4()]
    monkeypatch.setattr(embeddings, "embed", AsyncMock(return_value=[unit()]))
    try:
        async with factory() as session:
            session.add_all(
                [
                    User(
                        id=id,
                        email=f"{id}@example.com",
                        full_name="Vector Test",
                        password_hash="unused",
                    )
                    for id in users
                ]
            )
            await session.flush()
            session.add_all(
                [
                    Document(
                        id=id,
                        user_id=owner,
                        filename=f"{id}.pdf",
                        mime_type="application/pdf",
                        storage_path="database",
                        checksum=str(id),
                        processing_status="COMPLETED",
                    )
                    for id, owner in zip(documents, users)
                ]
            )
            await session.flush()
            farther = DocumentChunk(
                document_id=documents[0],
                user_id=users[0],
                chunk_index=0,
                content="Farther owner text",
                embedding=unit(1),
                embedding_model=embeddings.MODEL_ID,
            )
            closest = DocumentChunk(
                document_id=documents[0],
                user_id=users[0],
                chunk_index=1,
                content="Closest owner text",
                embedding=unit(),
                embedding_model=embeddings.MODEL_ID,
            )
            # Intentionally inconsistent ownership metadata must not authorize access.
            inconsistent = DocumentChunk(
                document_id=documents[1],
                user_id=users[0],
                chunk_index=0,
                content="Other user's secret",
                embedding=unit(),
                embedding_model=embeddings.MODEL_ID,
            )
            session.add_all([farther, closest, inconsistent])
            session.add_all(
                [
                    DocumentChunk(
                        document_id=documents[1],
                        user_id=users[1],
                        chunk_index=i + 1,
                        content="Other user's secret",
                        embedding=unit(),
                        embedding_model=embeddings.MODEL_ID,
                    )
                    for i in range(20)
                ]
            )
            await session.commit()
            hits = await vector_store.retrieve_documents("no lexical overlap", users[0], session)
            assert [c.id for c, _ in hits] == [closest.id, farther.id]
            assert all("secret" not in c.content for c, _ in hits)
            # Database deletion and vectors commit/roll back together.
            await session.execute(delete(Document).where(Document.id == documents[0]))
            await session.rollback()
            assert len(await vector_store.retrieve_documents("query", users[0], session)) == 2
            await session.execute(delete(Document).where(Document.id == documents[0]))
            await session.commit()
            assert await vector_store.retrieve_documents("query", users[0], session) == []
            assert not list(
                await session.scalars(
                    select(DocumentChunk).where(DocumentChunk.document_id == documents[0])
                )
            )
    finally:
        async with factory() as session:
            await session.execute(delete(Document).where(Document.id.in_(documents)))
            await session.execute(delete(User).where(User.id.in_(users)))
            await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_rule_ingestion_backfill_and_grounded_rag(monkeypatch):
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    name = f"Vector test {uuid4()}"
    content = "Salary rebate verified guidance. " * 80
    try:
        async with factory() as session:
            monkeypatch.setattr(
                embeddings, "embed", AsyncMock(side_effect=RuntimeError("offline model"))
            )
            count, indexed = await rag_service.ingest_tax_rule(
                TaxRuleIngestRequest(source_name=name, content=content), session
            )
            assert count == len(split_text(content))
            assert not indexed
            rows = list(
                await session.scalars(select(TaxRuleChunk).where(TaxRuleChunk.source_name == name))
            )
            assert all(c.embedding is None for c in rows)
            assert await vector_store.retrieve_rules("rebate", session)
        monkeypatch.setattr(
            embeddings, "embed", AsyncMock(side_effect=lambda texts: [unit() for _ in texts])
        )
        monkeypatch.setattr(reindex, "AsyncSessionFactory", factory)
        monkeypatch.setattr(reindex, "close_database", AsyncMock())
        await reindex.reindex()
        await reindex.reindex()  # Idempotent: updates the same rows instead of duplicating chunks.
        async with factory() as session:
            rows = list(
                await session.scalars(select(TaxRuleChunk).where(TaxRuleChunk.source_name == name))
            )
            assert len(rows) == count
            assert all(
                len(c.embedding) == 384 and c.embedding_model == embeddings.MODEL_ID for c in rows
            )
            # Semantic search works even with no keyword match.
            assert await vector_store.retrieve_rules("unrelated phrase", session)
            monkeypatch.setattr(rag_service.settings, "ai_mode", "extractive")
            answer = await rag_service.answer_with_rag("rebate", None, session)
            assert answer.mode == "extractive"
            assert any(source.source_name == name for source in answer.sources)
            assert "Salary rebate" in answer.answer
    finally:
        async with factory() as session:
            await session.execute(delete(TaxRuleChunk).where(TaxRuleChunk.source_name == name))
            await session.commit()
        await engine.dispose()
