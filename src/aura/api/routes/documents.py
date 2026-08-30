from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aura.core.config import settings
from aura.db.models import Document, User
from aura.db.session import get_session
from aura.schemas.document import DocumentUploadAccepted
from aura.services.file_storage import save_upload

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(user_id: UUID, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)) -> DocumentUploadAccepted:
    """Persist an upload and queue it for the future OCR/indexing worker."""
    if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG file.")

    content = await file.read()
    await file.seek(0)
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File must be at most {settings.max_upload_size_mb} MB.")

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    document_id = uuid4()
    saved_path, checksum = await save_upload(document_id, file)
    document = Document(id=document_id, user_id=user_id, filename=file.filename or "unnamed-document", mime_type=file.content_type, storage_path=str(saved_path), checksum=checksum)
    try:
        session.add(document)
        await session.commit()
    except Exception:
        await session.rollback()
        Path(saved_path).unlink(missing_ok=True)
        raise

    return DocumentUploadAccepted(
        document_id=document_id,
        user_id=user_id,
        filename=file.filename or "unnamed-document",
        status="QUEUED",
        message="Document accepted. OCR and indexing will run asynchronously.",
    )
