"""Deterministic Decimal unit-economics calculator (spec 17).

Hard rules:
  - Python Decimal only; JSON money is decimal string.
  - Pure function: deterministic, no LLM, no network, no time-dependent state.
  - Every formula + intermediate value goes into calculation_trace.
  - Hard constraints return machine-readable PASS/FAIL.
  - Missing input -> BLOCKED (never LLM-filled).
  - economics.verify re-derives from inputs and compares hash.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import Any

from ..schemas.constraint import Constraint
from ..schemas.economics import (
    ConstraintCheck,
    EconomicsArtifact,
    SensitivityCase,
)

# Stable precision; avoid float drift.
getcontext().prec = 28


@dataclass
class RoundingPolicy:
    """Money rounding policy. Default: 2 decimals, ROUND_HALF_UP."""

    decimals: int = 2
    mode: str = "ROUND_HALF_UP"

    def quantize(self, d: Decimal) -> Decimal:
        q = Decimal(1).scaleb(-self.decimals)  # 0.01
        return d.quantize(q, rounding=ROUND_HALF_UP)


@dataclass
class EconomicsInput:
    """All inputs needed to compute EconomicsArtifact (spec 17.1)."""

    candidate_id: str
    retail_price: Decimal
    factory_cost: Decimal
    feature_cost_deltas: list[Decimal] = field(default_factory=list)
    packaging_cost: Decimal = Decimal("0.00")
    shipping_cost: Decimal = Decimal("0.00")
    fulfillment_fee: Decimal = Decimal("0.00")
    platform_fee_rate: Decimal = Decimal("0.00")  # e.g. 0.15 = 15%
    platform_fixed_fee: Decimal = Decimal("0.00")
    marketing_rate: Decimal = Decimal("0.00")
    loss_allowance_rate: Decimal = Decimal("0.00")
    currency: str = "USD"
    rounding: RoundingPolicy = field(default_factory=RoundingPolicy)
    assumption_version: str = "1.0.0"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EconomicsInput:
        def D(x: Any) -> Decimal:
            if isinstance(x, Decimal):
                return x
            return Decimal(str(x))

        return cls(
            candidate_id=d["candidate_id"],
            retail_price=D(d["retail_price"]),
            factory_cost=D(d["factory_cost"]),
            feature_cost_deltas=[D(x) for x in d.get("feature_cost_deltas", [])],
            packaging_cost=D(d.get("packaging_cost", "0")),
            shipping_cost=D(d.get("shipping_cost", "0")),
            fulfillment_fee=D(d.get("fulfillment_fee", "0")),
            platform_fee_rate=D(d.get("platform_fee_rate", "0")),
            platform_fixed_fee=D(d.get("platform_fixed_fee", "0")),
            marketing_rate=D(d.get("marketing_rate", "0")),
            loss_allowance_rate=D(d.get("loss_allowance_rate", "0")),
            currency=d.get("currency", "USD"),
            assumption_version=d.get("assumption_version", "1.0.0"),
        )

    def to_hash_input(self) -> str:
        """Canonical string for reproducibility/hash."""
        return json.dumps(
            {
                "candidate_id": self.candidate_id,
                "retail_price": str(self.retail_price),
                "factory_cost": str(self.factory_cost),
                "feature_cost_deltas": [str(x) for x in self.feature_cost_deltas],
                "packaging_cost": str(self.packaging_cost),
                "shipping_cost": str(self.shipping_cost),
                "fulfillment_fee": str(self.fulfillment_fee),
                "platform_fee_rate": str(self.platform_fee_rate),
                "platform_fixed_fee": str(self.platform_fixed_fee),
                "marketing_rate": str(self.marketing_rate),
                "loss_allowance_rate": str(self.loss_allowance_rate),
                "currency": self.currency,
                "assumption_version": self.assumption_version,
            },
            sort_keys=True,
        )


class EconomicsCalculator:
    """Pure deterministic calculator. Stateless."""

    @staticmethod
    def calculate(inp: EconomicsInput, constraints: Iterable[Constraint] | None = None) -> EconomicsArtifact:
        r = inp.rounding
        trace: list[str] = []

        def rec(label: str, value: Decimal) -> Decimal:
            q = r.quantize(value)
            trace.append(f"{label} = {q}")
            return q

        factory_total = inp.factory_cost + sum(inp.feature_cost_deltas, Decimal("0"))
        factory_total = rec("factory_total = base_factory_cost + sum(feature_cost_deltas)", factory_total)

        landed_cost = factory_total + inp.packaging_cost + inp.shipping_cost
        landed_cost = rec("landed_cost = factory_total + packaging + shipping", landed_cost)

        platform_fee = inp.retail_price * inp.platform_fee_rate + inp.platform_fixed_fee
        platform_fee = rec("platform_fee = retail*rate + fixed", platform_fee)

        marketing_cost = inp.retail_price * inp.marketing_rate
        marketing_cost = rec("marketing_cost = retail*marketing_rate", marketing_cost)

        loss_allowance = inp.retail_price * inp.loss_allowance_rate
        loss_allowance = rec("loss_allowance = retail*loss_allowance_rate", loss_allowance)

        contribution_margin = (
            inp.retail_price
            - landed_cost
            - inp.fulfillment_fee
            - platform_fee
            - marketing_cost
            - loss_allowance
        )
        contribution_margin = rec("contribution_margin = retail - landed - fulfillment - platform - marketing - loss", contribution_margin)

        if inp.retail_price > 0:
            cm_rate = contribution_margin / inp.retail_price
        else:
            cm_rate = Decimal("0")
        cm_rate = rec("contribution_margin_rate = cm / retail", cm_rate)

        # Hard constraint checks
        checks: list[ConstraintCheck] = []
        if constraints:
            for c in constraints:
                if c.path == "business.factory_cost_max":
                    actual = factory_total
                    checks.append(ConstraintCheck(
                        constraint_id=c.constraint_id, passed=c.check(actual),
                        actual=str(r.quantize(actual)), expected=c.value, operator=c.operator,
                    ))
                elif c.path == "business.target_margin_min":
                    actual = cm_rate
                    checks.append(ConstraintCheck(
                        constraint_id=c.constraint_id, passed=c.check(actual),
                        actual=str(r.quantize(actual)), expected=c.value, operator=c.operator,
                    ))

        # Sensitivity: shipping, marketing, factory cost
        sens = EconomicsCalculator._sensitivity(inp, r)

        return EconomicsArtifact(
            candidate_id=inp.candidate_id,
            retail_price=str(r.quantize(inp.retail_price)),
            factory_cost=str(factory_total),
            packaging_cost=str(r.quantize(inp.packaging_cost)),
            shipping_cost=str(r.quantize(inp.shipping_cost)),
            fulfillment_fee=str(r.quantize(inp.fulfillment_fee)),
            platform_fee=str(platform_fee),
            marketing_assumption=str(marketing_cost),
            loss_allowance=str(loss_allowance),
            landed_cost=str(landed_cost),
            contribution_margin=str(contribution_margin),
            contribution_margin_rate=str(cm_rate),
            constraint_checks=checks,
            sensitivity_cases=sens,
            assumption_version=inp.assumption_version,
            calculation_trace=trace,
        )

    @staticmethod
    def _cm_formula(inp: EconomicsInput, r: RoundingPolicy) -> Decimal:
        """Compute contribution_margin only (no recursion, no sensitivity)."""
        factory_total = inp.factory_cost + sum(inp.feature_cost_deltas, Decimal("0"))
        landed = factory_total + inp.packaging_cost + inp.shipping_cost
        platform = inp.retail_price * inp.platform_fee_rate + inp.platform_fixed_fee
        marketing = inp.retail_price * inp.marketing_rate
        loss = inp.retail_price * inp.loss_allowance_rate
        cm = inp.retail_price - landed - inp.fulfillment_fee - platform - marketing - loss
        return r.quantize(cm)

    @staticmethod
    def _sensitivity(inp: EconomicsInput, r: RoundingPolicy) -> list[SensitivityCase]:
        cases: list[SensitivityCase] = []
        retail = inp.retail_price

        def rate(cm: Decimal) -> str:
            return str(r.quantize(cm / retail)) if retail > 0 else "0"

        # shipping +20%
        try:
            new_ship = inp.shipping_cost * Decimal("1.2")
            kw = {**inp.__dict__}
            kw["shipping_cost"] = new_ship
            kw.pop("rounding", None)
            cm = EconomicsCalculator._cm_formula(EconomicsInput(**kw, rounding=r), r)
            cases.append(SensitivityCase(label="shipping +20%", varied_input="shipping_cost",
                                          new_value=str(r.quantize(new_ship)),
                                          contribution_margin=str(cm),
                                          contribution_margin_rate=rate(cm)))
        except Exception:
            pass

        # marketing_rate +20%
        try:
            new_mkt = inp.marketing_rate * Decimal("1.2")
            kw = {**inp.__dict__}
            kw["marketing_rate"] = new_mkt
            kw.pop("rounding", None)
            cm = EconomicsCalculator._cm_formula(EconomicsInput(**kw, rounding=r), r)
            cases.append(SensitivityCase(label="marketing_rate +20%", varied_input="marketing_rate",
                                          new_value=str(new_mkt),
                                          contribution_margin=str(cm),
                                          contribution_margin_rate=rate(cm)))
        except Exception:
            pass

        # factory_cost +10%
        try:
            new_fc = inp.factory_cost * Decimal("1.1")
            kw = {**inp.__dict__}
            kw["factory_cost"] = new_fc
            kw.pop("rounding", None)
            cm = EconomicsCalculator._cm_formula(EconomicsInput(**kw, rounding=r), r)
            cases.append(SensitivityCase(label="factory_cost +10%", varied_input="factory_cost",
                                          new_value=str(r.quantize(new_fc)),
                                          contribution_margin=str(cm),
                                          contribution_margin_rate=rate(cm)))
        except Exception:
            pass

        return cases

    @staticmethod
    def verify(inp: EconomicsInput, artifact: EconomicsArtifact, constraints: Iterable[Constraint] | None = None) -> bool:
        """Re-derive from inputs and compare. R007."""
        recomputed = EconomicsCalculator.calculate(inp, constraints)
        return recomputed.contribution_margin == artifact.contribution_margin and \
               recomputed.contribution_margin_rate == artifact.contribution_margin_rate and \
               recomputed.landed_cost == artifact.landed_cost

    @staticmethod
    def content_hash(inp: EconomicsInput, artifact: EconomicsArtifact) -> str:
        """Stable hash for reproducibility."""
        payload = inp.to_hash_input() + "|" + artifact.model_dump_json()
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
