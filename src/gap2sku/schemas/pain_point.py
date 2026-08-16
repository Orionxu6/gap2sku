"""PainPoint — user pain with frequency numerator/denominator/method (spec 10.4)."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PainPoint(BaseModel):
    pain_point_id: str
    label: str
    frequency_count: int = 0
    frequency_denominator: int = 0
    frequency_method: str = ""
    severity: str = "medium"  # low/medium/high
    affected_product_count: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    feature_hypotheses: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def _conf_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        return v

    @field_validator("frequency_denominator")
    @classmethod
    def _denom_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("frequency_denominator must be >= 0")
        return v

    def frequency_ratio(self) -> float | None:
        if self.frequency_denominator == 0:
            return None
        return self.frequency_count / self.frequency_denominator


class PainPointSet(BaseModel):
    """Container for a set of pain points produced by Market Agent."""

    set_id: str
    pain_points: list[PainPoint] = Field(default_factory=list)
    snapshot_id: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
