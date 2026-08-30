from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from aura.core.config import settings
from aura.schemas.document import DocumentUploadAccepted

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(user_id: UUID, file: UploadFile = File(...)) -> DocumentUploadAccepted:
    """Accept a tax document; persistent storage and OCR are added next."""
    if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG file.")

    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File must be at most {settings.max_upload_size_mb} MB.")

    return DocumentUploadAccepted(
        user_id=user_id,
        filename=file.filename or "unnamed-document",
        status="QUEUED",
        message="Document accepted. OCR and indexing will run asynchronously.",
    )
