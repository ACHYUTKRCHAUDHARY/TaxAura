"""PostgreSQL-backed document queue; row locks release automatically on a crash."""

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import undefer

from aura.core.config import settings
from aura.core.enums import DocumentStatus
from aura.db.models import Document, DocumentChunk
from aura.db.session import AsyncSessionFactory
from aura.services.n8n_client import publish_workflow_event
from aura.services.text_processing import extract_text, split_text
from aura.services.vector_store import index_chunks

logger = logging.getLogger(__name__)


def _extract_document(content: bytes | None, storage_path: str, mime_type: str) -> str:
    if content is None:  # Compatibility with uploads created before durable storage.
        return extract_text(Path(storage_path), mime_type)
    with TemporaryDirectory(prefix="taxaura-") as directory:
        path = Path(directory) / "upload"
        path.write_bytes(content)
        path.chmod(0o600)
        return extract_text(path, mime_type)


async def process_document(document_id: UUID | None = None) -> bool:
    async with AsyncSessionFactory() as session:
        statement = (
            select(Document)
            .options(undefer(Document.file_content))
            .where(Document.processing_status == DocumentStatus.QUEUED)
            .order_by(Document.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if document_id is not None:
            statement = statement.where(Document.id == document_id)
        document = await session.scalar(statement)
        if document is None:
            return False
        # Hold the row lock until processing commits. A killed worker rolls back,
        # leaving QUEUED visible for another worker to claim without a stale lease.
        try:
            async with session.begin_nested():
                extracted = await asyncio.to_thread(
                    _extract_document,
                    document.file_content,
                    document.storage_path,
                    document.mime_type,
                )
                chunks = split_text(extracted)
                if not chunks:
                    raise ValueError("No readable text")
                await session.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
                )
                records = [
                    DocumentChunk(document_id=document.id, user_id=document.user_id, content=chunk)
                    for chunk in chunks
                ]
                session.add_all(records)
                document.extracted_text = extracted
                document.processing_status = DocumentStatus.COMPLETED
                document.processing_error = None
                await session.flush()
            event = "document.completed"
        except Exception:
            logger.exception("Document processing failed for %s", document_id)
            # Rollback of the savepoint expires ORM attributes; reload asynchronously.
            await session.refresh(document)
            document.processing_status = DocumentStatus.FAILED
            document.processing_error = (
                "Could not read this file. Try a text PDF or a clear PNG/JPEG image."
            )
            event = "document.failed"
        payload = {"document_id": str(document.id), "user_id": str(document.user_id)}
        if event == "document.completed":
            await index_chunks(records, "documents")
        await session.commit()
    try:
        await publish_workflow_event(event, payload)
    except Exception:  # noqa: BLE001 - optional dependency boundary
        logger.warning(
            "Workflow notification could not be delivered for %s", payload["document_id"]
        )
    return True


async def run_document_worker() -> None:
    while True:
        try:
            if await process_document():
                continue
        except Exception:
            logger.exception("Document queue unavailable; retrying on next poll")
        await asyncio.sleep(settings.worker_poll_seconds)
