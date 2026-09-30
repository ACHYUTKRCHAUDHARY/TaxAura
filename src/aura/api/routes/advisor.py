from fastapi import APIRouter, HTTPException

from aura.api.dependencies import CurrentUser
from aura.schemas.advisor import AdvisorAnswer, AdvisorQuestion
from aura.services.tax_advisor_agent import answer_question

router = APIRouter()


@router.post("/ask", response_model=AdvisorAnswer)
async def ask_tax_advisor(payload: AdvisorQuestion, current_user: CurrentUser) -> AdvisorAnswer:
    try:
        return AdvisorAnswer(answer=await answer_question(str(current_user.id), payload.question))
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Tax advisor is unavailable. Check Gemini configuration, model availability, and API quota.",
        ) from error
