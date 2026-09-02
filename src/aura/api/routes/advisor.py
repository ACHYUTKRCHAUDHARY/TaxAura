from fastapi import APIRouter, HTTPException

from aura.schemas.advisor import AdvisorAnswer, AdvisorQuestion
from aura.services.tax_advisor_agent import answer_question

router = APIRouter()


@router.post("/ask", response_model=AdvisorAnswer)
async def ask_tax_advisor(payload: AdvisorQuestion) -> AdvisorAnswer:
    try:
        return AdvisorAnswer(answer=await answer_question(str(payload.user_id), payload.question))
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Tax advisor is unavailable. Ensure Ollama is running and its configured model is installed.",
        ) from error
