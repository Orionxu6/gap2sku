"""Artifact Envelope — the common wrapper for all domain artifacts (spec 10.1)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArtifactType(str, Enum):
    PRODUCT_INTAKE = "ProductIntake"
    CATEGORY_PROFILE = "CategoryProfile"
    COMPLIANCE_POLICY_PACK = "CompliancePolicyPack"
    RESEARCH_PLAN = "ResearchPlan"
    OPPORTUNITY_BRIEF = "OpportunityBrief"
    CONSTRAINT = "Constraint"
    EVIDENCE = "Evidence"
    REVIEW_SNAPSHOT = "ReviewSnapshot"
    PAIN_POINT_SET = "PainPointSet"
    FEATURE_HYPOTHESIS = "FeatureHypothesis"
    SUPPLIER_CAPABILITY = "SupplierCapability"
    SUPPLIER_ASSESSMENT = "SupplierAssessment"
    ECONOMICS = "Economics"
    FEATURE_DECISION = "FeatureDecision"
    PRODUCT_SPEC = "ProductSpec"
    REVIEW_RESULT = "ReviewResult"
    CHANGE_EVENT = "ChangeEvent"
    IMPACT_PLAN = "ImpactPlan"
    DECISION_POLICY = "DecisionPolicy"
    CONFLICT_CARD = "ConflictCard"
    OPTION_CARD = "OptionCard"
    DECISION_BRIEF = "DecisionBrief"
    KNOWLEDGE_CITATION = "KnowledgeCitation"
    APPROVAL = "Approval"
    PRODUCT_CONCEPT_SET = "ProductConceptSet"
    SAMPLE_SPEC = "SampleSpec"
    RENDER_PROMPT = "RenderPromptRecord"
    RENDER_MANIFEST = "RenderManifest"
    RFQ_PACK = "RFQPack"
    SUPPLIER_QUOTE_SET = "SupplierQuoteSet"
    PUBLIC_SUPPLIER_SIGNAL_SET = "PublicSupplierSignalSet"
    COMPLIANCE_ASSESSMENT = "ComplianceAssessment"
    TEST_MATRIX = "TestMatrix"
    CLAIM_REGISTER = "ClaimRegister"
    PRODUCT_STORY = "ProductStoryBundle"
    DECISION_TO_SAMPLE_PACK = "DecisionToSamplePack"
    COLLABORATION_EVENT = "CollaborationEvent"


class ArtifactStatus(str, Enum):
    DRAFT = "DRAFT"
    VALID = "VALID"
    ACCEPTED = "ACCEPTED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArtifactEnvelope(BaseModel):
    """Unified envelope wrapping every artifact payload (spec 10.1)."""

    artifact_id: str
    artifact_type: ArtifactType
    artifact_version: int = Field(ge=1)
    schema_version: str = "1.0.0"
    policy_version: str = "policy-v1"
    project_id: str
    producer_agent: str
    producer_task_id: str
    status: ArtifactStatus = ArtifactStatus.VALID
    input_refs: list[str] = Field(default_factory=list)
    constraint_dependencies: list[str] = Field(default_factory=list)
    source_snapshot_ids: list[str] = Field(default_factory=list)
    data_mode: str = "REAL"
    content_hash: str = "sha256:PLACEHOLDER"
    created_at: str = Field(default_factory=utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", v):
            raise ValueError(f"artifact_id must match [A-Za-z0-9][A-Za-z0-9._-]*: {v!r}")
        return v

    def to_storage_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
