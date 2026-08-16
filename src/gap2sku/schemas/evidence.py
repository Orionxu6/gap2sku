"""EvidenceRecord — market evidence provenance (spec 10.3)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    USER_UPLOAD = "user_upload"
    PUBLIC_PAGE = "public_page"
    OFFICIAL_API = "official_api"
    MANUAL_CONFIRMATION = "manual_confirmation"


class RightsStatus(str, Enum):
    SYNTHETIC = "synthetic"
    USER_AUTHORIZED = "user_authorized"
    PUBLIC_REFERENCE_ONLY = "public_reference_only"
    REDISTRIBUTION_ALLOWED = "redistribution_allowed"
    UNKNOWN = "unknown"


class EvidenceRecord(BaseModel):
    evidence_id: str
    source_type: SourceType
    source_id: str = ""
    source_url: str = ""
    snapshot_id: str
    observed_at: str = ""
    content_excerpt: str = ""
    content_hash: str = "sha256:PLACEHOLDER"
    locator: str = ""  # e.g. review index, span, offset
    rights_status: RightsStatus = RightsStatus.UNKNOWN
    is_synthetic: bool = False
    language: str = "en"
    file_hash: str = ""
    workbook: str = ""
    sheet: str = ""
    row_number: int | None = None
    collected_at: str = ""
    evidence_grade: str = "C"
    duplicate_of: str | None = None
    transformations: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    def to_payload(self) -> dict:
        return self.model_dump(mode="json")
