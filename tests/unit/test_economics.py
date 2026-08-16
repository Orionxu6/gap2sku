"""Tests for deterministic Decimal economics (spec 17, 27.1)."""
from decimal import Decimal

from gap2sku.economics.calculator import EconomicsCalculator, EconomicsInput
from gap2sku.schemas.constraint import Constraint, ConstraintOperator


def _input(**overrides) -> EconomicsInput:
    base = dict(
        candidate_id="test-cand",
        retail_price=Decimal("39.99"),
        factory_cost=Decimal("6.30"),
        feature_cost_deltas=[Decimal("0.80"), Decimal("0.30"), Decimal("0.40")],
        packaging_cost=Decimal("0.80"),
        shipping_cost=Decimal("2.20"),
        fulfillment_fee=Decimal("3.50"),
        platform_fee_rate=Decimal("0.15"),
        marketing_rate=Decimal("0.08"),
        loss_allowance_rate=Decimal("0.03"),
    )
    base.update(overrides)
    return EconomicsInput(**base)


def test_calculate_is_deterministic():
    inp = _input()
    a = EconomicsCalculator.calculate(inp)
    b = EconomicsCalculator.calculate(inp)
    assert a.contribution_margin == b.contribution_margin
    assert a.contribution_margin_rate == b.contribution_margin_rate


def test_calculation_trace_non_empty():
    art = EconomicsCalculator.calculate(_input())
    assert len(art.calculation_trace) > 0  # R007


def test_factory_total_sums_deltas():
    art = EconomicsCalculator.calculate(_input())
    # 6.30 + 0.80 + 0.30 + 0.40 = 7.80
    assert Decimal(art.factory_cost) == Decimal("7.80")


def test_contribution_margin_positive():
    art = EconomicsCalculator.calculate(_input())
    assert Decimal(art.contribution_margin) > 0


def test_hard_constraint_pass():
    inp = _input()  # factory_total 7.80 <= 8.00
    constraints = [Constraint(constraint_id="factory_cost_max", path="business.factory_cost_max",
                              operator=ConstraintOperator.LE, value="8.00", hard=True)]
    art = EconomicsCalculator.calculate(inp, constraints)
    assert art.constraint_checks[0].passed is True


def test_hard_constraint_fail():
    inp = _input(factory_cost=Decimal("8.50"))
    constraints = [Constraint(constraint_id="factory_cost_max", path="business.factory_cost_max",
                              operator=ConstraintOperator.LE, value="8.00", hard=True)]
    art = EconomicsCalculator.calculate(inp, constraints)
    assert art.constraint_checks[0].passed is False


def test_verify_recomputable():
    inp = _input()
    art = EconomicsCalculator.calculate(inp)
    assert EconomicsCalculator.verify(inp, art) is True  # R007


def test_sensitivity_cases_present():
    art = EconomicsCalculator.calculate(_input())
    assert len(art.sensitivity_cases) >= 3  # shipping, marketing, factory


def test_no_float_in_output():
    art = EconomicsCalculator.calculate(_input())
    # All money fields must be strings (decimal), not float
    for field in ["retail_price", "factory_cost", "landed_cost", "contribution_margin"]:
        assert isinstance(getattr(art, field), str)
