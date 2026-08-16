"""SupplierCapability — supplier offer for a feature (spec 10.5)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SupportState(str, Enum):
    LISTED = "listed"
    CONFIRMED = "confirmed"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class VerificationLevel(str, Enum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    PLATFORM_VISIBLE = "platform_visible"
    DOCUMENT_VERIFIED = "document_verified"
    HUMAN_CONFIRMED = "human_confirmed"


class SupplierCapability(BaseModel):
    supplier_id: str
    offer_id: str
    feature_id: str = ""
    support_state: SupportState = SupportState.UNKNOWN
    existing_mold: bool = False
    moq: int = 0
    base_unit_cost: str = "0.00"  # Decimal string
    cost_delta: str = "0.00"  # Decimal string
    lead_time_days: int = 0
    source_ids: list[str] = Field(default_factory=list)
    verification_level: VerificationLevel = VerificationLevel.SYNTHETIC_FIXTURE
    open_questions: list[str] = Field(default_factory=list)
    observed_at: str = ""

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")


class SupplierAssessment(BaseModel):
    """Filtered/ranked supplier options against constraints."""

    assessment_id: str
    accepted_options: list[SupplierCapability] = Field(default_factory=list)
    rejected_options: list[SupplierCapability] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
