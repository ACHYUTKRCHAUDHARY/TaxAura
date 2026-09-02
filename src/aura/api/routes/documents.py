from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aura.core.config import settings
from aura.db.models import Document, User
from aura.db.session import get_session
from aura.schemas.document import DocumentResponse, DocumentUploadAccepted
from aura.services.document_processor import process_document
from aura.services.file_storage import save_upload

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    user_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadAccepted:
    """Persist an upload and queue it for the future OCR/indexing worker."""
    if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG file.")

    content = await file.read()
    await file.seek(0)
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail=f"File must be at most {settings.max_upload_size_mb} MB."
        )

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    document_id = uuid4()
    saved_path, checksum = await save_upload(document_id, file)
    duplicate = await session.scalar(
        select(Document).where(Document.user_id == user_id, Document.checksum == checksum)
    )
    if duplicate is not None:
        Path(saved_path).unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="This document has already been uploaded.")
    document = Document(
        id=document_id,
        user_id=user_id,
        filename=file.filename or "unnamed-document",
        mime_type=file.content_type,
        storage_path=str(saved_path),
        checksum=checksum,
    )
    try:
        session.add(document)
        await session.commit()
    except Exception:
        await session.rollback()
        Path(saved_path).unlink(missing_ok=True)
        raise

    background_tasks.add_task(process_document, document_id)

    return DocumentUploadAccepted(
        document_id=document_id,
        user_id=user_id,
        filename=file.filename or "unnamed-document",
        status="QUEUED",
        message="Document accepted. OCR and indexing will run asynchronously.",
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Document:
    document = await session.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[Document]:
    result = await session.scalars(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result)
