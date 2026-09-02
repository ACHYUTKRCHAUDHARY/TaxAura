from decimal import ROUND_HALF_UP, Decimal

from aura.schemas.tax import RegimeResult, TaxComparisonRequest, TaxComparisonResponse

ZERO = Decimal(0)
CESS_RATE = Decimal("0.04")
OLD_STANDARD_DEDUCTION = Decimal(50000)
NEW_STANDARD_DEDUCTION = Decimal(75000)


def _slab_tax(income: Decimal, slabs: list[tuple[Decimal | None, Decimal]]) -> Decimal:
    tax = ZERO
    lower = ZERO
    for upper, rate in slabs:
        if income <= lower:
            break
        taxable_band = income - lower if upper is None else min(income, upper) - lower
        tax += taxable_band * rate
        if upper is None or income <= upper:
            break
        lower = upper
    return tax


def _result(taxable_income: Decimal, regime: str) -> RegimeResult:
    if regime == "OLD":
        slabs = [
            (Decimal(250000), ZERO),
            (Decimal(500000), Decimal("0.05")),
            (Decimal(1000000), Decimal("0.20")),
            (None, Decimal("0.30")),
        ]
        tax = _slab_tax(taxable_income, slabs)
        if taxable_income <= Decimal(500000):
            tax = max(ZERO, tax - min(tax, Decimal(12500)))
    else:
        slabs = [
            (Decimal(400000), ZERO),
            (Decimal(800000), Decimal("0.05")),
            (Decimal(1200000), Decimal("0.10")),
            (Decimal(1600000), Decimal("0.15")),
            (Decimal(2000000), Decimal("0.20")),
            (Decimal(2400000), Decimal("0.25")),
            (None, Decimal("0.30")),
        ]
        tax = _slab_tax(taxable_income, slabs)
        if taxable_income <= Decimal(1200000):
            tax = max(ZERO, tax - min(tax, Decimal(60000)))
    cess = tax * CESS_RATE
    money = lambda value: value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return RegimeResult(
        taxable_income=money(taxable_income),
        tax_before_cess=money(tax),
        cess=money(cess),
        total_tax=money(tax + cess),
    )


def compare_tax_regimes(payload: TaxComparisonRequest) -> TaxComparisonResponse:
    old_income = max(
        ZERO, payload.annual_salary - OLD_STANDARD_DEDUCTION - payload.old_regime_deductions
    )
    new_income = max(ZERO, payload.annual_salary - NEW_STANDARD_DEDUCTION)
    old = _result(old_income, "OLD")
    new = _result(new_income, "NEW")
    recommended = "OLD" if old.total_tax < new.total_tax else "NEW"
    saving = abs(old.total_tax - new.total_tax)
    return TaxComparisonResponse(
        assessment_year="AY 2026-27",
        old_regime=old,
        new_regime=new,
        recommended_regime=recommended,
        estimated_saving=saving,
        disclaimer="Educational estimate for a resident salaried individual below age 60 with income up to ₹50 lakh. Verify filing figures with a qualified tax professional.",
    )
