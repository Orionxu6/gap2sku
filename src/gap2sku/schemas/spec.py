"""ProductSpec — versioned product specification (spec 10.8)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SpecApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ProductSpec(BaseModel):
    spec_id: str
    spec_version: int = 1
    spec_hash: str = "sha256:PLACEHOLDER"
    project_id: str
    business_constraints: list[str] = Field(default_factory=list)
    target_market: str = ""
    selected_supplier_option: str = ""
    accepted_features: list[str] = Field(default_factory=list)
    rejected_features: list[str] = Field(default_factory=list)
    deferred_features: list[str] = Field(default_factory=list)
    dimensions_and_materials: dict = Field(default_factory=dict)
    bom_and_cost: dict = Field(default_factory=dict)
    constraint_checks: list[dict] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    review_status: str = "PENDING"  # PENDING / PASS / REVISE / BLOCK
    approval_status: SpecApprovalStatus = SpecApprovalStatus.DRAFT
    created_at: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
