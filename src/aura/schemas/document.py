from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentUploadAccepted(BaseModel):
    document_id: UUID
    user_id: UUID
    filename: str
    status: str
    message: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    filename: str
    mime_type: str
    processing_status: str
    created_at: datetime
    processing_error: str | None = None


class DocumentTextResponse(BaseModel):
    id: UUID
    filename: str
    text: str
