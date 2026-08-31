from uuid import UUID
from pydantic import BaseModel, Field

class AdvisorQuestion(BaseModel):
    user_id: UUID
    question: str = Field(min_length=5, max_length=1_000)

class AdvisorAnswer(BaseModel):
    answer: str
