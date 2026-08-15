from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class FormulaTemplate(StrEnum):
    CAPACITY_CHARGE_L1 = "capacity_charge_l1"
    RTE_ADJUSTED_CAPACITY_CHARGE = "rte_adjusted_capacity_charge"
    EPC_PLUS_DISCOUNTED_OM = "epc_plus_discounted_om"


@dataclass(frozen=True, slots=True)
class FormulaResult:
    template: FormulaTemplate
    formula: str
    value: Decimal
    unit: str


def decimal_input(inputs: dict[str, float], name: str) -> Decimal:
    if name not in inputs:
        raise ValueError(f"{name} is required")
    return Decimal(str(inputs[name]))


def evaluate_formula(template: FormulaTemplate, inputs: dict[str, float]) -> FormulaResult:
    if template == FormulaTemplate.CAPACITY_CHARGE_L1:
        quoted_charge = decimal_input(inputs, "quoted_capacity_charge")
        if quoted_charge < 0:
            raise ValueError("quoted_capacity_charge cannot be negative")
        return FormulaResult(
            template=template,
            formula="quoted_capacity_charge",
            value=quoted_charge,
            unit="INR/MW/month",
        )
    if template == FormulaTemplate.RTE_ADJUSTED_CAPACITY_CHARGE:
        quoted_charge = decimal_input(inputs, "quoted_capacity_charge")
        baseline_rte = decimal_input(inputs, "baseline_rte_percent")
        guaranteed_rte = decimal_input(inputs, "guaranteed_rte_percent")
        if quoted_charge < 0 or not 0 <= baseline_rte <= 100 or not 0 < guaranteed_rte <= 100:
            raise ValueError("capacity charge and RTE inputs are outside permitted bounds")
        value = quoted_charge * (Decimal("1") + (baseline_rte - guaranteed_rte) / Decimal("100"))
        return FormulaResult(
            template=template,
            formula="quoted_capacity_charge * (1 + (baseline_rte - guaranteed_rte) / 100)",
            value=value,
            unit="INR/MW/month",
        )
    epc_lump_sum = decimal_input(inputs, "epc_lump_sum")
    annual_om = decimal_input(inputs, "annual_om")
    discount_rate = decimal_input(inputs, "discount_rate_percent") / Decimal("100")
    escalation = decimal_input(inputs, "om_escalation_percent") / Decimal("100")
    years = int(decimal_input(inputs, "om_term_years"))
    if epc_lump_sum < 0 or annual_om < 0 or discount_rate < 0 or years <= 0:
        raise ValueError("EPC, O&M, discount rate, and term inputs are outside permitted bounds")
    om_npv = sum(
        annual_om
        * (Decimal("1") + escalation) ** (year - 1)
        / (Decimal("1") + discount_rate) ** year
        for year in range(1, years + 1)
    )
    return FormulaResult(
        template=template,
        formula=(
            "epc_lump_sum + sum(annual_om * (1 + escalation)^(year - 1) / (1 + discount_rate)^year)"
        ),
        value=epc_lump_sum + om_npv,
        unit="INR",
    )


def rounded(value: Decimal, places: int) -> Decimal:
    return value.quantize(Decimal("1").scaleb(-places), rounding=ROUND_HALF_UP)
