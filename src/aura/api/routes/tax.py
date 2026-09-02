from fastapi import APIRouter

from aura.api.dependencies import CurrentUser
from aura.schemas.tax import TaxComparisonRequest, TaxComparisonResponse
from aura.services.tax_calculator import compare_tax_regimes

router = APIRouter()


@router.post("/compare", response_model=TaxComparisonResponse)
async def compare_regimes(payload: TaxComparisonRequest, _: CurrentUser) -> TaxComparisonResponse:
    return compare_tax_regimes(payload)
