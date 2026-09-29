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


def test_marginal_relief_above_twelve_lakh_taxable_income() -> None:
    result = compare_tax_regimes(TaxComparisonRequest(annual_salary=Decimal(1300000)))
    assert result.new_regime.taxable_income == Decimal("1225000.00")
    assert result.new_regime.tax_before_cess == Decimal("25000.00")
    assert result.new_regime.total_tax == Decimal("26000.00")


def test_marginal_relief_does_not_reduce_normal_tax_far_above_threshold() -> None:
    result = compare_tax_regimes(TaxComparisonRequest(annual_salary=Decimal(1675000)))
    assert result.new_regime.tax_before_cess == Decimal("120000.00")
