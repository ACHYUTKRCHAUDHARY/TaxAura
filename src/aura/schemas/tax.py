from decimal import Decimal

from pydantic import BaseModel, Field


class TaxComparisonRequest(BaseModel):
    annual_salary: Decimal = Field(ge=0, le=5_000_000)
    old_regime_deductions: Decimal = Field(default=0, ge=0, le=2_000_000)


class RegimeResult(BaseModel):
    taxable_income: Decimal
    tax_before_cess: Decimal
    cess: Decimal
    total_tax: Decimal


class TaxComparisonResponse(BaseModel):
    assessment_year: str
    old_regime: RegimeResult
    new_regime: RegimeResult
    recommended_regime: str
    estimated_saving: Decimal
    disclaimer: str
