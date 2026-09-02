import logging
from uuid import UUID

from langchain_ollama import ChatOllama, OllamaEmbeddings
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aura.core.config import settings
from aura.db.models import TaxRuleChunk
from aura.schemas.rag import RagAnswer, RagSource, TaxRuleIngestRequest
from aura.services.text_processing import split_text

logger = logging.getLogger(__name__)


async def ingest_tax_rule(payload: TaxRuleIngestRequest, session: AsyncSession) -> int:
    chunks = split_text(payload.content)
    embedding_client = OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )
    try:
        embeddings: list[list[float] | None] = await embedding_client.aembed_documents(chunks)
    except Exception as error:  # noqa: BLE001 - keyword-only ingestion remains usable
        logger.warning("Embedding generation unavailable during ingestion: %s", error)
        embeddings = [None] * len(chunks)
    session.add_all(
        TaxRuleChunk(
            source_name=payload.source_name,
            source_url=str(payload.source_url) if payload.source_url else None,
            content=chunk,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    )
    await session.commit()
    return len(chunks)


async def _retrieve_rules(question: str, session: AsyncSession) -> list[TaxRuleChunk]:
    keyword_statement = text("""
        SELECT id FROM tax_rule_chunks
        WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :question)
        ORDER BY ts_rank(
            to_tsvector('english', content),
            plainto_tsquery('english', :question)
        ) DESC
        LIMIT 5
    """)
    keyword_ids = [
        row.id for row in (await session.execute(keyword_statement, {"question": question}))
    ]
    ids = list(keyword_ids)
    try:
        embedding_client = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )
        embedding = await embedding_client.aembed_query(question)
        vector_statement = text("""
            SELECT id FROM tax_rule_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 5
        """)
        vector_text = "[" + ",".join(str(value) for value in embedding) + "]"
        vector_ids = [
            row.id for row in (await session.execute(vector_statement, {"embedding": vector_text}))
        ]
        ids.extend(vector_ids)
    except Exception as error:  # noqa: BLE001 - keyword retrieval is the supported fallback
        logger.warning("Semantic retrieval unavailable; using keyword results: %s", error)
    unique_ids = list(dict.fromkeys(ids))[:6]
    if not unique_ids:
        return []
    chunks = await session.scalars(select(TaxRuleChunk).where(TaxRuleChunk.id.in_(unique_ids)))
    by_id = {chunk.id: chunk for chunk in chunks}
    return [by_id[chunk_id] for chunk_id in unique_ids if chunk_id in by_id]


async def answer_with_rag(
    question: str,
    user_id: UUID | None,
    session: AsyncSession,
) -> RagAnswer:
    chunks = await _retrieve_rules(question, session)
    if not chunks:
        return RagAnswer(
            answer="I could not find a verified tax-rule source for this question.",
            sources=[],
        )
    context = "\n\n".join(
        f"SOURCE: {chunk.source_name}\nURL: {chunk.source_url or 'Not provided'}\n{chunk.content}"
        for chunk in chunks
    )
    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )
    prompt = (
        "Answer only from the supplied verified context. If it is insufficient, say so. "
        "Do not calculate a final tax liability. Mention source names.\n\n"
        f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"
    )
    response = await model.ainvoke(prompt)
    sources = list(
        {
            (chunk.source_name, chunk.source_url): RagSource(
                source_name=chunk.source_name,
                source_url=chunk.source_url,
            )
            for chunk in chunks
        }.values()
    )
    return RagAnswer(answer=str(response.content), sources=sources)
