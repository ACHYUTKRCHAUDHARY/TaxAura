import logging
from asyncio import to_thread
from pathlib import Path
from uuid import UUID

from langchain_ollama import OllamaEmbeddings
from sqlalchemy import delete, select

from aura.core.config import settings
from aura.core.enums import DocumentStatus
from aura.db.models import Document, DocumentChunk
from aura.db.session import AsyncSessionFactory
from aura.services.n8n_client import publish_workflow_event
from aura.services.text_processing import extract_text, split_text

logger = logging.getLogger(__name__)


async def _publish_event_safely(event: str, payload: dict) -> None:
    try:
        await publish_workflow_event(event, payload)
    except Exception as error:  # noqa: BLE001 - n8n must not change processing result
        logger.warning("Could not publish %s event: %s", event, error)


async def process_document(document_id: UUID) -> None:
    async with AsyncSessionFactory() as session:
        document = await session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            return
        document.processing_status = DocumentStatus.PROCESSING
        await session.commit()
        try:
            extracted = await to_thread(
                extract_text,
                Path(document.storage_path),
                document.mime_type,
            )
            chunks = split_text(extracted)
            if not chunks:
                raise ValueError("No readable text was extracted from the document.")
            embeddings: list[list[float] | None]
            try:
                client = OllamaEmbeddings(
                    model=settings.ollama_embedding_model,
                    base_url=settings.ollama_base_url,
                )
                embeddings = await client.aembed_documents(chunks)
            except Exception as error:  # noqa: BLE001 - embeddings are an optional fallback
                logger.warning("Embedding generation failed for %s: %s", document_id, error)
                embeddings = [None] * len(chunks)
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )
            session.add_all(
                DocumentChunk(
                    document_id=document.id,
                    user_id=document.user_id,
                    content=chunk,
                    embedding=embedding,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            )
            document.extracted_text = extracted
            document.processing_status = DocumentStatus.COMPLETED
            await session.commit()
            await _publish_event_safely(
                "document.completed",
                {"document_id": str(document.id), "user_id": str(document.user_id)},
            )
        except Exception as error:
            logger.exception("Document processing failed for %s", document_id)
            await session.rollback()
            document = await session.scalar(select(Document).where(Document.id == document_id))
            if document:
                document.processing_status = DocumentStatus.FAILED
                await session.commit()
            await _publish_event_safely(
                "document.failed",
                {"document_id": str(document_id), "reason": str(error)},
            )
