"""Constraint — business hard/soft constraints (spec 10.2).

Money constraints use Decimal string values, never binary float.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConstraintOperator(str, Enum):
    LE = "<="
    LT = "<"
    GE = ">="
    GT = ">"
    EQ = "=="
    NE = "!="


class Constraint(BaseModel):
    constraint_id: str
    path: str  # e.g. "business.factory_cost_max"
    operator: ConstraintOperator
    value: str  # Decimal string for money, plain string for others
    unit: str = ""
    hard: bool = True
    source: str = "user"
    version: int = 1

    @field_validator("value")
    @classmethod
    def _value_str(cls, v: Any) -> str:
        # Always store as string; if a number sneaks in, normalize.
        if isinstance(v, float):
            raise ValueError("money/numeric constraint value must be string, not float")
        return str(v)

    def numeric_value(self) -> Decimal | None:
        try:
            return Decimal(self.value)
        except Exception:
            return None

    def check(self, actual: str | int | float | Decimal) -> bool:
        """Evaluate this constraint against an actual value."""
        actual_d = Decimal(str(actual))
        expected = self.numeric_value()
        if expected is None:
            raise ValueError(f"constraint {self.constraint_id} value {self.value!r} is not numeric")
        match self.operator:
            case ConstraintOperator.LE:
                return actual_d <= expected
            case ConstraintOperator.LT:
                return actual_d < expected
            case ConstraintOperator.GE:
                return actual_d >= expected
            case ConstraintOperator.GT:
                return actual_d > expected
            case ConstraintOperator.EQ:
                return actual_d == expected
            case ConstraintOperator.NE:
                return actual_d != expected


class ConstraintSet(BaseModel):
    """Versioned collection of constraints for a project."""

    project_id: str
    version: int = 1
    constraints: list[Constraint] = Field(default_factory=list)

    def get(self, constraint_id: str) -> Constraint | None:
        for c in self.constraints:
            if c.constraint_id == constraint_id:
                return c
        return None

    def by_path(self, path: str) -> list[Constraint]:
        return [c for c in self.constraints if c.path == path]

    def hard(self) -> list[Constraint]:
        return [c for c in self.constraints if c.hard]
