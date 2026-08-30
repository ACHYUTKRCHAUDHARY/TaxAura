from uuid import UUID

from pydantic import BaseModel


class DocumentUploadAccepted(BaseModel):
    user_id: UUID
    filename: str
    status: str
    message: str
