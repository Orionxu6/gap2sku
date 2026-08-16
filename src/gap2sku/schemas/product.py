"""Category-agnostic product-definition and sample-decision contracts."""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntakeMode(str, Enum):
    OPPORTUNITY_DISCOVERY = "OPPORTUNITY_DISCOVERY"
    NEW_CONCEPT = "NEW_CONCEPT"
    EXISTING_SKU_UPGRADE = "EXISTING_SKU_UPGRADE"


class ProfileStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"


class ProductIntake(StrictModel):
    project_id: str
    mode: IntakeMode
    title: str
    target_market: str
    target_users: list[str]
    category_hint: str
    idea_or_problem: str
    hard_constraints: dict[str, Any]
    source_urls: list[str] = Field(default_factory=list)
    uploaded_artifact_refs: list[str] = Field(default_factory=list)


class SpecField(StrictModel):
    key: str
    label: str
    value_type: str
    unit: str | None = None
    required_for_sample: bool = True


class CategoryProfile(StrictModel):
    profile_id: str
    category_name: str
    version: str
    status: ProfileStatus
    risk_tier: str
    spec_fields: list[SpecField]
    manufacturing_processes: list[str]
    required_evidence: list[str]
    policy_pack_ref: str
    confirmed_by: str | None = None

    @property
    def go_eligible(self) -> bool:
        return self.status == ProfileStatus.CONFIRMED and bool(self.confirmed_by)


class PolicyRule(StrictModel):
    rule_id: str
    title: str
    source_uri: str
    source_version: str
    applies_when: str
    required_evidence: list[str]
    blocking: bool = True


class CompliancePolicyPack(StrictModel):
    pack_id: str
    version: str
    target_market: str
    category_profile_ref: str
    rules: list[PolicyRule]
    status: ProfileStatus


class ResearchWorkstream(StrictModel):
    owner: str
    objective: str
    allowed_sources: list[str]
    required_outputs: list[str]


class ResearchPlan(StrictModel):
    plan_id: str
    project_id: str
    profile_ref: str
    workstreams: list[ResearchWorkstream]
    fallback_mode: str = "EXPLICIT_REPLAY_SNAPSHOT"


class OpportunityBrief(StrictModel):
    brief_id: str
    project_id: str
    target_segment: str
    pain_point_refs: list[str]
    competitor_gaps: list[str]
    innovation_questions: list[str]
    evidence_refs: list[str]
    limitations: list[str]


class ProductConcept(StrictModel):
    concept_id: str
    title: str
    strategy: str
    pain_point_refs: list[str]
    differentiators: list[str]
    parameter_ranges: dict[str, Any]
    materials: list[str]
    tradeoffs: list[str]
    risk_flags: list[str]
    render_manifest_refs: list[str] = Field(default_factory=list)


class ProductConceptSet(StrictModel):
    concept_set_id: str
    project_id: str
    concepts: list[ProductConcept] = Field(min_length=3, max_length=3)
    selected_concept_id: str | None = None
    selection_reason: str | None = None


class SampleSpec(StrictModel):
    sample_spec_id: str
    project_id: str
    category_profile_ref: str
    selected_concept_ref: str
    parameters: dict[str, Any]
    materials: list[dict[str, Any]]
    dimensions: dict[str, Any]
    tolerances: dict[str, Any]
    test_requirements: list[str]
    lock_status: str = "DRAFT"
    locked_by: str | None = None
    spec_hash: str = ""

    @model_validator(mode="after")
    def validate_hash(self) -> SampleSpec:
        payload = self.model_dump(exclude={"spec_hash"}, mode="json")
        expected = "sha256:" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if self.spec_hash and self.spec_hash != expected:
            raise ValueError("spec_hash does not match SampleSpec payload")
        self.spec_hash = expected
        if self.lock_status == "LOCKED" and not self.locked_by:
            raise ValueError("LOCKED SampleSpec requires locked_by")
        return self


class RenderPromptRecord(StrictModel):
    prompt_id: str
    project_id: str
    concept_ref: str
    sample_spec_hash: str | None
    provider: str
    model: str
    seed: int
    prompt: str
    negative_prompt: str
    input_refs: list[str]
    synthetic_label: str = "SYNTHETIC_CONCEPT"


class RenderManifest(StrictModel):
    render_id: str
    prompt_ref: str
    provider: str
    model: str
    seed: int
    asset_uri: str
    asset_hash: str
    sample_spec_hash: str | None
    data_mode: str
    label: str = "SYNTHETIC_CONCEPT"


class RFQPack(StrictModel):
    rfq_id: str
    project_id: str
    sample_spec_ref: str
    sample_spec_hash: str
    render_refs: list[str]
    quantity: int
    target_moq: int
    target_lead_days: int
    packaging_requirements: list[str]
    trade_terms: list[str]
    questions: list[str]
    status: str


class SupplierQuote(StrictModel):
    quote_id: str
    supplier_name: str
    source_ref: str
    verification_level: str
    amount: str
    currency: str
    moq: int | None = None
    lead_days: int | None = None
    data_mode: str


class SupplierQuoteSet(StrictModel):
    quote_set_id: str
    project_id: str
    rfq_ref: str
    sample_spec_hash: str
    received_at: str
    source_document_hash: str
    quotes: list[SupplierQuote]
    comparison_status: str


class PublicSupplierSignal(StrictModel):
    """A public listing observation, never a supplier quote or capability proof."""

    signal_id: str
    supplier_name: str
    source_url: str
    captured_at: str
    source_hash: str
    observed_facts: dict[str, Any]
    evidence_class: str = "PUBLIC_LISTING_SIGNAL"
    verification_level: str = "UNVERIFIED_PUBLIC_SIGNAL"
    limitations: list[str]


class PublicSupplierSignalSet(StrictModel):
    signal_set_id: str
    project_id: str
    signals: list[PublicSupplierSignal]
    use_policy: str = "SHORTLIST_AND_RFQ_TARGET_ONLY"
    quote_state: str = "MISSING"


class ComplianceCheck(StrictModel):
    check_id: str
    title: str
    result: str
    policy_refs: list[str]
    evidence_refs: list[str]
    remediation: list[str]


class ComplianceAssessment(StrictModel):
    assessment_id: str
    project_id: str
    classification: str
    profile_status: ProfileStatus
    checks: list[ComplianceCheck]
    overall_result: str
    unverified_items: list[str]


class TestCase(StrictModel):
    test_id: str
    name: str
    method: str
    acceptance_criteria: str
    sample_size: int
    status: str
    evidence_refs: list[str] = Field(default_factory=list)


class TestMatrix(StrictModel):
    matrix_id: str
    project_id: str
    tests: list[TestCase]


class Claim(StrictModel):
    claim_id: str
    text: str
    status: str
    evidence_refs: list[str]
    prohibited_until_verified: bool = True


class ClaimRegister(StrictModel):
    register_id: str
    project_id: str
    claims: list[Claim]


class ProductStoryBundle(StrictModel):
    bundle_id: str
    project_id: str
    version: int
    recommendation: str
    data_mode: str
    title: str
    subtitle: str
    hero_render_ref: str | None
    sections: dict[str, Any]
    artifact_refs: list[str]
    views: list[str] = Field(default_factory=lambda: ["internal", "supplier", "judge"])


class DecisionToSamplePack(StrictModel):
    pack_id: str
    project_id: str
    recommendation: str
    selected_concept_ref: str
    sample_spec_ref: str
    rfq_pack_ref: str
    economics_ref: str
    compliance_ref: str
    test_matrix_ref: str
    review_ref: str
    story_ref: str
    pending_tasks: list[str]
    artifact_refs: list[str]
