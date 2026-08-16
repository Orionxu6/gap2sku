"""EconomicsArtifact — deterministic unit economics (spec 10.6, 17).

All money is Decimal string. Calculation done in economics/calculator.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ConstraintCheck(BaseModel):
    constraint_id: str
    passed: bool
    actual: str
    expected: str
    operator: str


class SensitivityCase(BaseModel):
    label: str
    varied_input: str
    new_value: str
    contribution_margin: str
    contribution_margin_rate: str


class EconomicsArtifact(BaseModel):
    candidate_id: str
    retail_price: str = "0.00"
    factory_cost: str = "0.00"
    packaging_cost: str = "0.00"
    shipping_cost: str = "0.00"
    fulfillment_fee: str = "0.00"
    platform_fee: str = "0.00"
    marketing_assumption: str = "0.00"
    loss_allowance: str = "0.00"
    landed_cost: str = "0.00"
    contribution_margin: str = "0.00"
    contribution_margin_rate: str = "0.00"
    constraint_checks: list[ConstraintCheck] = Field(default_factory=list)
    sensitivity_cases: list[SensitivityCase] = Field(default_factory=list)
    assumption_version: str = "1.0.0"
    calculation_trace: list[str] = Field(default_factory=list)

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
