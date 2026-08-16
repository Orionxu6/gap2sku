"""ReviewResult — Reviewer Gate output (spec 10.9, 18)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ReviewDecision(str, Enum):
    PASS = "PASS"
    REVISE = "REVISE"
    BLOCK = "BLOCK"


class ReviewError(BaseModel):
    rule_id: str
    artifact_refs: list[str] = Field(default_factory=list)
    message: str
    severity: str = "ERROR"  # ERROR / WARNING


class ReviewResult(BaseModel):
    review_id: str
    spec_id: str
    spec_hash: str
    decision: ReviewDecision
    errors: list[ReviewError] = Field(default_factory=list)
    warnings: list[ReviewError] = Field(default_factory=list)
    reviewer_agent: str = "gap2sku-reviewer"
    created_at: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
