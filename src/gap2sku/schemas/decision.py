"""FeatureDecision — accept/reject/defer a feature (spec 10.7)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class DecisionStatus(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DEFER = "DEFER"


class FeatureDecision(BaseModel):
    feature_id: str
    status: DecisionStatus
    market_refs: list[str] = Field(default_factory=list)
    supply_refs: list[str] = Field(default_factory=list)
    economics_refs: list[str] = Field(default_factory=list)
    violated_constraints: list[str] = Field(default_factory=list)
    rationale: str = ""
    reconsider_if: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def _range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        return v

    def has_full_evidence_chain(self) -> bool:
        """R004: ACCEPT requires Market + Supply + Economics refs."""
        return bool(self.market_refs and self.supply_refs and self.economics_refs)

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
