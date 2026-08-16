"""FeatureHypothesis — candidate feature derived from pain points."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FeatureStatus(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DEFER = "DEFER"


class FeatureHypothesis(BaseModel):
    feature_id: str
    label: str
    description: str = ""
    pain_point_refs: list[str] = Field(default_factory=list)
    status: FeatureStatus = FeatureStatus.HYPOTHESIS
    cost_delta: str = "0.00"  # Decimal string, incremental factory cost
    rationale: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
