"""ChangeEvent — constraint change triggering selective re-plan (spec 10.10, 19)."""
from __future__ import annotations

from pydantic import BaseModel


class ChangeEvent(BaseModel):
    change_id: str
    project_id: str
    changed_by: str = "human"
    path: str  # e.g. "business.factory_cost_max"
    old_value: str
    new_value: str
    old_version: int = 1
    new_version: int = 2
    reason: str = ""
    created_at: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
