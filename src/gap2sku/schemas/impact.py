"""ImpactPlan — selective re-planning output (spec 19.3)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ImpactAction(str, Enum):
    PRESERVED = "PRESERVED"
    STALE = "STALE"
    RECOMPUTE = "RECOMPUTE"
    SKIPPED = "SKIPPED"
    EXTERNAL_CONFIRMATION = "EXTERNAL_CONFIRMATION"


class ImpactPlan(BaseModel):
    change_id: str
    preserved_artifacts: list[str] = Field(default_factory=list)
    stale_artifacts: list[str] = Field(default_factory=list)
    recompute_artifacts: list[str] = Field(default_factory=list)
    new_tasks: list[str] = Field(default_factory=list)
    skipped_agents: list[str] = Field(default_factory=list)
    reason: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
