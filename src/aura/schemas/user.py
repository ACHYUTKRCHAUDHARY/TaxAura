from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: FullName
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
