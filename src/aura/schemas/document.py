from uuid import UUID

from pydantic import BaseModel


class DocumentUploadAccepted(BaseModel):
    document_id: UUID
    user_id: UUID
    filename: str
    status: str
    message: str
