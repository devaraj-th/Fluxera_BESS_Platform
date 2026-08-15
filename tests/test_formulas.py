from decimal import Decimal

import pytest
from packages.domain.formulas import FormulaTemplate, evaluate_formula, rounded


def test_rte_adjusted_capacity_charge_is_deterministic() -> None:
    result = evaluate_formula(
        FormulaTemplate.RTE_ADJUSTED_CAPACITY_CHARGE,
        {
            "quoted_capacity_charge": 100_000,
            "baseline_rte_percent": 85,
            "guaranteed_rte_percent": 80,
        },
    )
    assert rounded(result.value, 2) == Decimal("105000.00")
    assert result.unit == "INR/MW/month"


def test_formula_rejects_missing_and_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="guaranteed_rte_percent"):
        evaluate_formula(
            FormulaTemplate.RTE_ADJUSTED_CAPACITY_CHARGE,
            {"quoted_capacity_charge": 1, "baseline_rte_percent": 85},
        )
    with pytest.raises(ValueError, match="permitted"):
        evaluate_formula(
            FormulaTemplate.RTE_ADJUSTED_CAPACITY_CHARGE,
            {
                "quoted_capacity_charge": 1,
                "baseline_rte_percent": 101,
                "guaranteed_rte_percent": 80,
            },
        )
