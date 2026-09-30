"""pgvector repository: database-ranked results with authorization inside SQL."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aura.db.models import Document, DocumentChunk, TaxRuleChunk
from aura.services import embeddings

logger = logging.getLogger(__name__)


async def index_chunks(chunks) -> bool:
    """Populate ORM rows in the caller's transaction; never commit separately.

    Embedding failures leave source text available for keyword retrieval and reindex.
    Database failures are NOT swallowed: the caller rolls back the transaction.
    """
    if not chunks:
        return True
    try:
        vectors = await embeddings.embed([chunk.content for chunk in chunks])
    except Exception:  # noqa: BLE001 - isolate optional model inference, not database errors
        logger.warning("Embedding generation unavailable; run the reindex command to recover")
        return False
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk.embedding = vector
        chunk.embedding_model = embeddings.MODEL_ID
    return True


async def query_vector(question: str) -> list[float] | None:
    try:
        return (await embeddings.embed([question]))[0]
    except Exception:  # noqa: BLE001 - isolate optional model inference, not database errors
        logger.warning("Query embedding unavailable; using PostgreSQL keyword retrieval")
        return None


def _keywords(column, question):
    document = func.to_tsvector("english", column)
    query = func.websearch_to_tsquery("english", question)
    return document.op("@@")(query), func.ts_rank(document, query).desc()


async def retrieve_rules(question: str, session: AsyncSession, limit: int = 6):
    vector = await query_vector(question)
    hits = []
    if vector is not None:
        hits = list(
            await session.scalars(
                select(TaxRuleChunk)
                .where(
                    TaxRuleChunk.embedding.is_not(None),
                    TaxRuleChunk.embedding_model == embeddings.MODEL_ID,
                )
                .order_by(TaxRuleChunk.embedding.cosine_distance(vector))
                .limit(limit)
            )
        )
    # Backfilled or temporarily unembedded records remain discoverable by keywords.
    if len(hits) < limit:
        match, rank = _keywords(TaxRuleChunk.content, question)
        hits.extend(
            await session.scalars(
                select(TaxRuleChunk)
                .where(match, TaxRuleChunk.id.not_in([c.id for c in hits]))
                .order_by(rank)
                .limit(limit - len(hits))
            )
        )
    return hits


async def retrieve_documents(
    question: str, user_id: UUID | None, session: AsyncSession, limit: int = 4
):
    if user_id is None:
        return []
    vector = await query_vector(question)
    ownership = (
        DocumentChunk.user_id == user_id,
        Document.user_id == user_id,
        Document.processing_status == "COMPLETED",
    )
    hits = []
    if vector is not None:
        # Materialize the authorized subset FIRST, then compute exact cosine top-K.
        # This avoids ANN post-filter starvation when many other users have closer hits.
        owned = (
            select(DocumentChunk.id, DocumentChunk.embedding)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                *ownership,
                DocumentChunk.embedding.is_not(None),
                DocumentChunk.embedding_model == embeddings.MODEL_ID,
            )
            .cte("owned_chunks")
            .prefix_with("MATERIALIZED")
        )
        hits = list(
            (
                await session.execute(
                    select(DocumentChunk, Document.filename)
                    .join(Document, Document.id == DocumentChunk.document_id)
                    .join(owned, owned.c.id == DocumentChunk.id)
                    .where(*ownership)
                    .order_by(owned.c.embedding.cosine_distance(vector))
                    .limit(limit)
                )
            ).all()
        )
    if len(hits) < limit:
        match, rank = _keywords(DocumentChunk.content, question)
        hits.extend(
            (
                await session.execute(
                    select(DocumentChunk, Document.filename)
                    .join(Document, Document.id == DocumentChunk.document_id)
                    .where(*ownership, match, DocumentChunk.id.not_in([c.id for c, _ in hits]))
                    .order_by(rank)
                    .limit(limit - len(hits))
                )
            ).all()
        )
    return hits
