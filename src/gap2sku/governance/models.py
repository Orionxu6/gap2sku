from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DecisionRecommendation(str, Enum):
    GO = "GO"
    REVISE = "REVISE"
    NO_GO = "NO-GO"


class EvidenceState(str, Enum):
    CONFIRMED = "CONFIRMED"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"


class DecisionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = "gap2sku-default"
    version: str = "policy-v3.0.0"
    price_min_cny: int = 99
    price_max_cny: int = 119
    require_real_supplier_quote_for_go: bool = True
    require_bom_for_go: bool = True
    require_durability_test_for_adjustable_mechanism: bool = True
    require_material_test_for_child_claims: bool = True
    require_human_approval_for_go: bool = True
    require_confirmed_category_profile_for_go: bool = True
    require_locked_sample_spec_for_go: bool = True
    require_compliance_pass_for_go: bool = True
    no_go_after_repeated_critical_test_failure: bool = True
    max_revision_rounds: int = 3
    immutable_fields: list[str] = Field(default_factory=lambda: [
        "require_real_supplier_quote_for_go", "require_bom_for_go",
        "require_durability_test_for_adjustable_mechanism",
        "require_material_test_for_child_claims", "require_human_approval_for_go",
        "require_confirmed_category_profile_for_go", "require_locked_sample_spec_for_go",
        "require_compliance_pass_for_go", "no_go_after_repeated_critical_test_failure",
    ])


class ConflictCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    title: str
    conflict_type: str
    claims: list[str]
    evidence_refs: list[str]
    policy_refs: list[str]
    unresolved_gaps: list[str]
    severity: str
    status: str = "OPEN"


class OptionCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str
    conflict_id: str
    title: str
    tradeoffs: list[str]
    required_evidence: list[str]
    policy_checks: dict[str, bool | str]
    recommendation: str


class ReviewFinding(BaseModel):
    finding_id: str
    rule_id: str
    severity: str
    result: str
    owner: str
    message: str
    artifact_refs: list[str] = Field(default_factory=list)
    remediation: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    task_id: str
    revision: int
    product_spec_ref: str
    product_spec_hash: str
    policy_version: str
    review_result: str
    findings: list[ReviewFinding]
    unverified_checks: list[str] = Field(default_factory=list)
    reviewed_at: str = Field(default_factory=utcnow)


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    spec_hash: str
    policy_version: str
    approver: str
    reason: str
    decision: str
    approved_at: str = Field(default_factory=utcnow)


class DecisionBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief_id: str
    project_id: str
    recommendation: DecisionRecommendation
    evidence_summary: list[str]
    conflict_refs: list[str]
    option_refs: list[str]
    risk_summary: list[str]
    pending_confirmations: list[str]
    revision_tasks: list[str]
    policy_version: str
    data_mode: str
    approval_required: bool
    no_go_reasons: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=utcnow)
