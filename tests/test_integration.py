"""Run against a disposable, migrated PostgreSQL database via TEST_DATABASE_URL."""

import os
from io import BytesIO
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aura.db.models import Document, DocumentChunk, User
from aura.db.session import get_session
from aura.main import app
from aura.services import document_processor, embeddings, vector_store

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="No test database configured"
)


def text_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 30 700 Td (Private salary income 1300000) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_complete_user_flow_and_isolation(monkeypatch):
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def session_override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    monkeypatch.setattr(document_processor, "AsyncSessionFactory", factory)
    monkeypatch.setattr(
        embeddings,
        "embed",
        AsyncMock(side_effect=lambda texts: [[1.0] + [0.0] * 383 for _ in texts]),
    )
    marker = uuid4().hex
    user_ids = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:

            async def register(suffix):
                email = f"{marker}{suffix}@example.com"
                response = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": email,
                        "full_name": "Test User",
                        "password": "very-strong-test-password",
                    },
                )
                assert response.status_code == 201, response.text
                data = response.json()
                user_ids.append(data["user"]["id"])
                return {"Authorization": f"Bearer {data['access_token']}"}, email

            owner, email = await register("a")
            other, _ = await register("b")
            login = await client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": "very-strong-test-password"},
            )
            assert login.status_code == 200
            assert (
                await client.post(
                    "/api/v1/auth/login", data={"username": email, "password": "wrong"}
                )
            ).status_code == 401
            assert (
                await client.post(
                    "/api/v1/knowledge/rules",
                    headers=owner,
                    json={"source_name": "Test", "content": "a" * 60},
                )
            ).status_code == 403
            response = await client.post(
                "/api/v1/documents/upload",
                headers=owner,
                files={"file": ("salary.pdf", text_pdf(), "application/pdf")},
            )
            assert response.status_code == 202, response.text
            doc_id = response.json()["document_id"]
            assert (
                await client.post(
                    "/api/v1/documents/upload",
                    headers=owner,
                    files={"file": ("salary.pdf", text_pdf(), "application/pdf")},
                )
            ).status_code == 409
            for suffix in ("", "/text"):
                assert (
                    await client.get(f"/api/v1/documents/{doc_id}{suffix}", headers=other)
                ).status_code == 404
            assert (
                await client.delete(f"/api/v1/documents/{doc_id}", headers=other)
            ).status_code == 404
            assert (
                await client.post(f"/api/v1/documents/{doc_id}/retry", headers=other)
            ).status_code == 404
            from uuid import UUID

            assert await document_processor.process_document(UUID(doc_id))
            assert not await document_processor.process_document(UUID(doc_id))
            response = await client.get(f"/api/v1/documents/{doc_id}/text", headers=owner)
            assert response.status_code == 200, response.text
            assert "Private salary" in response.json()["text"]
            async with factory() as session:
                chunk = await session.scalar(
                    select(DocumentChunk).where(DocumentChunk.document_id == UUID(doc_id))
                )
                assert chunk.chunk_index == 0
                assert len(chunk.embedding) == 384
                assert chunk.embedding_model == embeddings.MODEL_ID
                assert (
                    await vector_store.retrieve_documents("unrelated", UUID(user_ids[1]), session)
                    == []
                )
                hits = await vector_store.retrieve_documents(
                    "unrelated", UUID(user_ids[0]), session
                )
                assert hits[0][0].id == chunk.id
            result = await client.post(
                "/api/v1/tax/compare", headers=owner, json={"annual_salary": 1300000}
            )
            assert result.json()["new_regime"]["total_tax"] == "26000.00"
            assert (
                await client.delete(f"/api/v1/documents/{doc_id}", headers=owner)
            ).status_code == 204
            assert (await client.get("/api/v1/documents", headers=owner)).json() == []
            async with factory() as session:
                assert (
                    await session.scalar(
                        select(DocumentChunk.id).where(DocumentChunk.document_id == UUID(doc_id))
                    )
                    is None
                )
            bad = await client.post(
                "/api/v1/documents/upload",
                headers=owner,
                files={"file": ("broken.pdf", b"%PDF- broken contents", "application/pdf")},
            )
            assert bad.status_code == 202
            bad_id = bad.json()["document_id"]
            assert await document_processor.process_document(UUID(bad_id))
            failed = await client.get(f"/api/v1/documents/{bad_id}", headers=owner)
            assert failed.json()["processing_status"] == "FAILED"
            assert failed.json()["processing_error"]
            retried = await client.post(f"/api/v1/documents/{bad_id}/retry", headers=owner)
            assert retried.status_code == 200
            assert retried.json()["processing_status"] == "QUEUED"
            assert (
                await client.delete(f"/api/v1/documents/{bad_id}", headers=owner)
            ).status_code == 204
            # Inference failure preserves extraction and owner-filtered keyword search.
            monkeypatch.setattr(
                embeddings, "embed", AsyncMock(side_effect=RuntimeError("model offline"))
            )
            fallback = await client.post(
                "/api/v1/documents/upload",
                headers=owner,
                files={"file": ("fallback.pdf", text_pdf(), "application/pdf")},
            )
            fallback_id = UUID(fallback.json()["document_id"])
            assert await document_processor.process_document(fallback_id)
            async with factory() as session:
                chunk = await session.scalar(
                    select(DocumentChunk).where(DocumentChunk.document_id == fallback_id)
                )
                assert chunk.embedding is None
                assert await vector_store.retrieve_documents("salary", UUID(user_ids[0]), session)
                assert (
                    await vector_store.retrieve_documents("salary", UUID(user_ids[1]), session)
                    == []
                )
            assert (
                await client.delete(f"/api/v1/documents/{fallback_id}", headers=owner)
            ).status_code == 204
    finally:
        app.dependency_overrides.clear()
        async with factory() as session:
            from uuid import UUID

            ids = [UUID(value) for value in user_ids]
            await session.execute(delete(Document).where(Document.user_id.in_(ids)))
            await session.execute(delete(User).where(User.id.in_(ids)))
            await session.commit()
        await engine.dispose()
