from decimal import Decimal

from aura.schemas.tax import TaxComparisonRequest
from aura.services.tax_calculator import compare_tax_regimes


def test_new_regime_rebate_for_twelve_lakh_salary() -> None:
    result = compare_tax_regimes(
        TaxComparisonRequest(
            annual_salary=Decimal(1200000),
            old_regime_deductions=Decimal(150000),
        )
    )
    assert result.new_regime.taxable_income == Decimal("1125000.00")
    assert result.new_regime.total_tax == Decimal("0.00")
    assert result.recommended_regime == "NEW"


def test_zero_income_has_zero_tax() -> None:
    result = compare_tax_regimes(TaxComparisonRequest(annual_salary=Decimal(0)))
    assert result.old_regime.total_tax == Decimal("0.00")
    assert result.new_regime.total_tax == Decimal("0.00")
