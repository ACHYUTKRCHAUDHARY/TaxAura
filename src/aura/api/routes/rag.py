from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aura.api.dependencies import AdminUser, CurrentUser
from aura.db.session import get_session
from aura.schemas.rag import (
    RagAnswer,
    RagQuestion,
    TaxRuleIngestRequest,
    TaxRuleIngestResponse,
)
from aura.services.rag_service import answer_with_rag, ingest_tax_rule

router = APIRouter()


@router.post(
    "/rules",
    response_model=TaxRuleIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_tax_rule(
    payload: TaxRuleIngestRequest,
    _: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> TaxRuleIngestResponse:
    count = await ingest_tax_rule(payload, session)
    return TaxRuleIngestResponse(chunks_created=count)


@router.post("/ask", response_model=RagAnswer)
async def ask_rag(
    payload: RagQuestion,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RagAnswer:
    try:
        return await answer_with_rag(payload.question, current_user.id, session)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="RAG service is unavailable. Verify PostgreSQL, pgvector, and Ollama.",
        ) from error
