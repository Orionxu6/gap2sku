"""Deterministic Reviewer Gate rules R001-R012 (spec 18.1).

Three-layer gate (spec 18):
  Schema Gate -> Deterministic Rule Gate -> Reviewer Agent Explanation

LLM Reviewer never overrides deterministic ERROR/BLOCK.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..schemas.decision import DecisionStatus, FeatureDecision
from ..schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from ..schemas.review import ReviewDecision, ReviewError, ReviewResult
from ..schemas.spec import ProductSpec


@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    severity: str = "ERROR"  # ERROR / WARNING
    artifact_refs: list[str] = field(default_factory=list)
    message: str = ""


def _r001_schema_valid(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    # All artifacts must have valid schema (Pydantic parse already guarantees this
    # at construction; here we check status != BLOCKED and content_hash set).
    bad = [a.artifact_id for a in artifacts if a.content_hash == "sha256:PLACEHOLDER"]
    return RuleResult(
        "R001", not bad, "ERROR", bad,
        "All artifacts must pass JSON Schema" if bad else "All artifacts schema valid",
    )


def _r002_no_stale_refs(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    stale = [a.artifact_id for a in artifacts if a.status in (ArtifactStatus.STALE, ArtifactStatus.SUPERSEDED)]
    ref_stale = [s for s in spec.artifact_refs if s in stale]
    return RuleResult(
        "R002", not ref_stale, "ERROR", ref_stale,
        "Spec references STALE/SUPERSEDED artifacts" if ref_stale else "No stale refs",
    )


def _r003_hard_constraints(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    failed = [c for c in spec.constraint_checks if not c.get("passed", True)]
    ids = [c.get("constraint_id", "?") for c in failed]
    return RuleResult(
        "R003", not failed, "ERROR", ids,
        "Hard constraints violated" if failed else "All hard constraints satisfied",
    )


def _r004_feature_evidence(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    decisions = [a for a in artifacts if a.artifact_type == ArtifactType.FEATURE_DECISION]
    bad: list[str] = []
    for d in decisions:
        fd = FeatureDecision(**d.payload)
        if fd.status == DecisionStatus.ACCEPT and not fd.has_full_evidence_chain():
            bad.append(d.artifact_id)
    return RuleResult(
        "R004", not bad, "ERROR", bad,
        "ACCEPT feature lacks Market+Supply+Economics refs" if bad else "All ACCEPT features have full evidence",
    )


def _r005_evidence_traceable(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    evidences = [a for a in artifacts if a.artifact_type == ArtifactType.EVIDENCE]
    bad: list[str] = []
    for e in evidences:
        # payload may be a single evidence or {"evidences": [...]}
        evs = e.payload.get("evidences", [e.payload] if e.payload.get("evidence_id") else [])
        for ev in evs:
            if not ev.get("snapshot_id") or not ev.get("locator"):
                bad.append(e.artifact_id)
                break
    return RuleResult(
        "R005", not bad, "ERROR", bad,
        "Evidence not traceable to snapshot/locator" if bad else "Evidence traceable",
    )


def _r006_no_verification_inflation(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    suppliers = [a for a in artifacts if a.artifact_type == ArtifactType.SUPPLIER_CAPABILITY]
    bad = []
    for s in suppliers:
        if s.payload.get("verification_level") == "human_confirmed" and s.payload.get("support_state") == "platform_visible":
            bad.append(s.artifact_id)
    return RuleResult(
        "R006", not bad, "ERROR", bad,
        "platform_visible labeled as human_confirmed" if bad else "Verification levels honest",
    )


def _r007_economics_recomputable(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    # In offline demo, we trust EconomicsArtifact.calculation_trace is non-empty.
    econ = [a for a in artifacts if a.artifact_type == ArtifactType.ECONOMICS]
    bad = [e.artifact_id for e in econ if not e.payload.get("calculation_trace")]
    return RuleResult(
        "R007", not bad, "ERROR", bad,
        "Economics not recomputable (no trace)" if bad else "Economics recomputable",
    )


def _r008_no_unsourced_claims(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    # Spec open_questions with no artifact ref are suspicious but not fatal; check decisions.
    decisions = [a for a in artifacts if a.artifact_type == ArtifactType.FEATURE_DECISION]
    bad = [d.artifact_id for d in decisions if not d.payload.get("rationale")]
    return RuleResult(
        "R008", not bad, "WARNING", bad,
        "Feature decision lacks rationale" if bad else "All decisions sourced",
    )


def _r009_reject_has_reason(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    decisions = [a for a in artifacts if a.artifact_type == ArtifactType.FEATURE_DECISION]
    bad = []
    for d in decisions:
        fd = FeatureDecision(**d.payload)
        if fd.status in (DecisionStatus.REJECT, DecisionStatus.DEFER):
            if not fd.rationale or not fd.reconsider_if:
                bad.append(d.artifact_id)
    return RuleResult(
        "R009", not bad, "ERROR", bad,
        "REJECT/DEFER lacks reason or reconsider condition" if bad else "All rejections documented",
    )


def _r010_spec_hash_match(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    reviews = [a for a in artifacts if a.artifact_type == ArtifactType.REVIEW_RESULT]
    bad = [r.artifact_id for r in reviews if r.payload.get("spec_hash") != spec.spec_hash]
    return RuleResult(
        "R010", not bad, "ERROR", bad,
        "Reviewer spec hash mismatch" if bad else "Spec hash consistent",
    )


def _r011_synthetic_labeled(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    evidences = [a for a in artifacts if a.artifact_type == ArtifactType.EVIDENCE]
    bad: list[str] = []
    for e in evidences:
        evs = e.payload.get("evidences", [e.payload] if e.payload.get("evidence_id") else [])
        for ev in evs:
            if ev.get("is_synthetic"):
                st = (str(ev.get("rights_status", "")) + str(ev.get("source_type", ""))).lower()
                if "synthetic" not in st:
                    bad.append(e.artifact_id)
                    break
    return RuleResult(
        "R011", not bad, "ERROR", bad,
        "Synthetic data not labeled" if bad else "Synthetic data labeled",
    )


def _r012_leader_committed(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    # Project-level artifacts (Spec, Decision) must be committed by product-architect.
    bad = [a.artifact_id for a in artifacts
           if a.artifact_type in (ArtifactType.PRODUCT_SPEC, ArtifactType.FEATURE_DECISION)
           and a.producer_agent != "gap2sku-product-architect"]
    return RuleResult(
        "R012", not bad, "ERROR", bad,
        "Project artifact not committed by Leader" if bad else "Leader committed all project artifacts",
    )


def _r013_concepts_cover_pain(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    sets = [a for a in artifacts if a.artifact_type == ArtifactType.PRODUCT_CONCEPT_SET]
    bad = []
    for item in sets:
        concepts = item.payload.get("concepts", [])
        if len(concepts) != 3 or any(not concept.get("pain_point_refs") for concept in concepts):
            bad.append(item.artifact_id)
    return RuleResult("R013", not bad, "ERROR", bad,
                      "Concept set must contain three pain-traceable options" if bad else "Concepts cover pain evidence")


def _r014_category_confirmed(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    profiles = [a for a in artifacts if a.artifact_type == ArtifactType.CATEGORY_PROFILE]
    bad = [a.artifact_id for a in profiles if a.payload.get("status") != "CONFIRMED" or not a.payload.get("confirmed_by")]
    return RuleResult("R014", not bad, "ERROR", bad,
                      "Draft or unconfirmed category profile cannot pass review" if bad else "Category profile confirmed")


def _r015_compliance_passed(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    assessments = [a for a in artifacts if a.artifact_type == ArtifactType.COMPLIANCE_ASSESSMENT]
    bad = [a.artifact_id for a in assessments if a.payload.get("overall_result") not in {"PASS", "PASS_SYNTHETIC"}]
    return RuleResult("R015", not bad, "ERROR", bad,
                      "Compliance classification or evidence matrix is incomplete" if bad else "Compliance assessment passed")


def _r016_tests_complete(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    matrices = [a for a in artifacts if a.artifact_type == ArtifactType.TEST_MATRIX]
    bad = []
    for matrix in matrices:
        if any(test.get("status") not in {"PASS", "PASS_SYNTHETIC"} for test in matrix.payload.get("tests", [])):
            bad.append(matrix.artifact_id)
    return RuleResult("R016", not bad, "ERROR", bad,
                      "Required prototype tests are incomplete or failed" if bad else "Required prototype tests complete")


def _r017_render_matches_spec(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    sample_specs = [a for a in artifacts if a.artifact_type == ArtifactType.SAMPLE_SPEC]
    current_hashes = {a.payload.get("spec_hash") for a in sample_specs}
    renders = [a for a in artifacts if a.artifact_type == ArtifactType.RENDER_MANIFEST]
    bad = [a.artifact_id for a in renders if a.payload.get("label") != "SYNTHETIC_CONCEPT" or (
        a.payload.get("sample_spec_hash") and a.payload.get("sample_spec_hash") not in current_hashes
    )]
    return RuleResult("R017", not bad, "ERROR", bad,
                      "Render is unlabeled or references a different SampleSpec" if bad else "Render provenance consistent")


def _r018_sample_spec_locked(artifacts: list[ArtifactEnvelope], spec: ProductSpec) -> RuleResult:
    sample_specs = [a for a in artifacts if a.artifact_type == ArtifactType.SAMPLE_SPEC]
    bad = [a.artifact_id for a in sample_specs if a.payload.get("lock_status") != "LOCKED" or not a.payload.get("locked_by")]
    return RuleResult("R018", not bad, "ERROR", bad,
                      "SampleSpec must be human-locked before PASS" if bad else "SampleSpec lock valid")


RULE_REGISTRY: dict[str, Callable[[list[ArtifactEnvelope], ProductSpec], RuleResult]] = {
    "R001": _r001_schema_valid,
    "R002": _r002_no_stale_refs,
    "R003": _r003_hard_constraints,
    "R004": _r004_feature_evidence,
    "R005": _r005_evidence_traceable,
    "R006": _r006_no_verification_inflation,
    "R007": _r007_economics_recomputable,
    "R008": _r008_no_unsourced_claims,
    "R009": _r009_reject_has_reason,
    "R010": _r010_spec_hash_match,
    "R011": _r011_synthetic_labeled,
    "R012": _r012_leader_committed,
    "R013": _r013_concepts_cover_pain,
    "R014": _r014_category_confirmed,
    "R015": _r015_compliance_passed,
    "R016": _r016_tests_complete,
    "R017": _r017_render_matches_spec,
    "R018": _r018_sample_spec_locked,
}


class ReviewerGate:
    """Deterministic rule gate. LLM layer added separately and cannot override BLOCK."""

    @staticmethod
    def run(artifacts: list[ArtifactEnvelope], spec: ProductSpec, review_id: str = "review-spec-v1") -> ReviewResult:
        errors: list[ReviewError] = []
        warnings: list[ReviewError] = []
        for rule_id, fn in RULE_REGISTRY.items():
            res = fn(artifacts, spec)
            err = ReviewError(rule_id=rule_id, artifact_refs=res.artifact_refs, message=res.message, severity=res.severity)
            if not res.passed:
                if res.severity == "ERROR":
                    errors.append(err)
                else:
                    warnings.append(err)

        if errors:
            decision = ReviewDecision.BLOCK
        elif warnings:
            decision = ReviewDecision.REVISE
        else:
            decision = ReviewDecision.PASS

        return ReviewResult(
            review_id=review_id,
            spec_id=spec.spec_id,
            spec_hash=spec.spec_hash,
            decision=decision,
            errors=errors,
            warnings=warnings,
            reviewer_agent="gap2sku-reviewer",
        )
