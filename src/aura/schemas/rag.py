from pydantic import BaseModel, Field, HttpUrl


class TaxRuleIngestRequest(BaseModel):
    source_name: str = Field(min_length=2, max_length=255)
    source_url: HttpUrl | None = None
    content: str = Field(min_length=50, max_length=100_000)


class TaxRuleIngestResponse(BaseModel):
    chunks_created: int
    semantic_indexed: bool = False


class RagQuestion(BaseModel):
    question: str = Field(min_length=5, max_length=1_000)
    include_documents: bool = False


class RagSource(BaseModel):
    source_name: str
    source_url: str | None = None


class RagAnswer(BaseModel):
    answer: str
    sources: list[RagSource]
    mode: str = "extractive"
