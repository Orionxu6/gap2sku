"""Deterministic unit economics (spec section 17).

All calculations use Decimal. LLM never computes costs/margins.
The calculator is a pure function: same inputs -> same outputs + hash.
"""
from .calculator import EconomicsCalculator, EconomicsInput, RoundingPolicy

__all__ = ["EconomicsCalculator", "EconomicsInput", "RoundingPolicy"]
