"""Chroma holds a rebuildable semantic index; PostgreSQL owns source records."""

import asyncio
import logging
from functools import lru_cache
from uuid import UUID

from aura.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def chroma_client():
    import chromadb
    from chromadb.config import Settings

    options = Settings(anonymized_telemetry=False)
    if settings.chroma_mode == "http":
        return chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            ssl=settings.chroma_ssl,
            settings=options,
        )
    raise RuntimeError("Semantic search is disabled")


def collection(kind: str):
    # Chroma's local all-MiniLM-L6-v2 embedding function is independent of Gemini.
    # Only vectors/IDs/metadata are persisted in Chroma, not private source text.
    return chroma_client().get_or_create_collection(name=f"taxaura-{kind}-v1")


def _index(records: list[dict], kind: str) -> None:
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    embed = DefaultEmbeddingFunction()
    target = collection(kind)
    for offset in range(0, len(records), 32):
        batch = records[offset : offset + 32]
        target.upsert(
            ids=[r["id"] for r in batch],
            embeddings=embed([r["content"] for r in batch]),
            metadatas=[r["metadata"] for r in batch],
        )


async def index_chunks(chunks, kind: str) -> bool:
    if settings.chroma_mode == "disabled":
        return False
    records = [
        {
            "id": str(c.id),
            "content": c.content,
            "metadata": (
                {"user_id": str(c.user_id), "document_id": str(c.document_id)}
                if kind == "documents"
                else {"kind": "rule"}
            ),
        }
        for c in chunks
    ]
    try:
        await asyncio.to_thread(_index, records, kind)
        return True
    except Exception:
        logger.warning(
            "Chroma indexing unavailable; run the reindex command to recover", exc_info=True
        )
        return False


async def semantic_ids(question: str, kind: str, user_id: UUID | None = None) -> list[UUID]:
    if settings.chroma_mode == "disabled":
        return []
    if kind == "documents" and user_id is None:
        return []

    def query():
        target = collection(kind)
        result = target.query(
            query_texts=[question],
            n_results=6,
            where={"user_id": str(user_id)} if kind == "documents" else None,
            include=["distances"],
        )
        return [UUID(value) for value in result["ids"][0]]

    try:
        return await asyncio.to_thread(query)
    except Exception:  # noqa: BLE001 - optional dependency boundary
        logger.warning("Chroma query unavailable; falling back to PostgreSQL keywords")
        return []


async def delete_document_vectors(document_id: UUID, user_id: UUID) -> None:
    if settings.chroma_mode != "disabled":
        await asyncio.to_thread(
            lambda: collection("documents").delete(
                where={"$and": [{"document_id": str(document_id)}, {"user_id": str(user_id)}]}
            )
        )
