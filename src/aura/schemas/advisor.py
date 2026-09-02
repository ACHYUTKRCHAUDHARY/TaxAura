from pydantic import BaseModel, Field


class AdvisorQuestion(BaseModel):
    question: str = Field(min_length=5, max_length=1_000)


class AdvisorAnswer(BaseModel):
    answer: str
