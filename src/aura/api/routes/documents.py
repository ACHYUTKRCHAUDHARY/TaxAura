from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aura.api.dependencies import CurrentUser
from aura.core.config import settings
from aura.db.models import Document, User
from aura.db.session import get_session
from aura.schemas.document import DocumentResponse, DocumentTextResponse, DocumentUploadAccepted
from aura.services.file_storage import InvalidFileSignatureError, UploadTooLargeError, save_upload
from aura.services.vector_store import delete_document_vectors

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadAccepted:
    if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG file.")
    document_id = uuid4()
    try:
        saved_path, checksum = await save_upload(document_id, file)
    except UploadTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except InvalidFileSignatureError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    try:
        # Serialize uploads per user so duplicate checks and quotas are atomic.
        await session.scalar(select(User).where(User.id == current_user.id).with_for_update())
        duplicate = await session.scalar(
            select(Document.id).where(
                Document.user_id == current_user.id, Document.checksum == checksum
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="This document has already been uploaded.")
        count = await session.scalar(
            select(func.count()).select_from(Document).where(Document.user_id == current_user.id)
        )
        if count >= settings.max_documents_per_user:
            raise HTTPException(
                status_code=409, detail="Document limit reached. Delete an existing upload first."
            )
        session.add(
            Document(
                id=document_id,
                user_id=current_user.id,
                filename=(file.filename or "unnamed-document")[:255],
                mime_type=file.content_type,
                storage_path="database",
                file_content=Path(saved_path).read_bytes(),
                checksum=checksum,
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        Path(saved_path).unlink(missing_ok=True)
        await file.close()
    return DocumentUploadAccepted(
        document_id=document_id,
        user_id=current_user.id,
        filename=(file.filename or "unnamed-document")[:255],
        status="QUEUED",
        message="Document accepted. Text extraction and indexing will run asynchronously.",
    )


async def owned_document(
    document_id: UUID, user_id: UUID, session: AsyncSession, lock: bool = False
) -> Document:
    statement = select(Document).where(Document.id == document_id, Document.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    document = await session.scalar(statement)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID, current_user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> Document:
    return await owned_document(document_id, current_user.id, session)


@router.get("/{document_id}/text", response_model=DocumentTextResponse)
async def document_text(
    document_id: UUID, current_user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> DocumentTextResponse:
    document = await owned_document(document_id, current_user.id, session)
    if document.processing_status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Document text is not ready yet.")
    return DocumentTextResponse(
        id=document.id, filename=document.filename, text=document.extracted_text or ""
    )


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document(
    document_id: UUID, current_user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> Document:
    document = await owned_document(document_id, current_user.id, session, lock=True)
    if document.processing_status != "FAILED":
        raise HTTPException(status_code=409, detail="Only failed documents can be retried.")
    document.processing_status = "QUEUED"
    document.processing_error = None
    await session.commit()
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID, current_user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> None:
    document = await owned_document(document_id, current_user.id, session, lock=True)
    try:
        await delete_document_vectors(document.id, current_user.id)
    except Exception as error:
        raise HTTPException(
            status_code=503, detail="Vector cleanup unavailable. Please retry deletion shortly."
        ) from error
    legacy_path = document.storage_path
    await session.delete(document)
    await session.commit()
    if legacy_path != "database":
        Path(legacy_path).unlink(missing_ok=True)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[Document]:
    return list(
        await session.scalars(
            select(Document)
            .where(Document.user_id == current_user.id)
            .order_by(Document.created_at.desc())
        )
    )
