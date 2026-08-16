"""Tests for the deterministic Reviewer Gate."""
from gap2sku.review.rules import RULE_REGISTRY, ReviewerGate
from gap2sku.schemas.decision import DecisionStatus, FeatureDecision
from gap2sku.schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from gap2sku.schemas.spec import ProductSpec, SpecApprovalStatus


def _envelope(aid: str, atype: ArtifactType, payload: dict, agent: str = "gap2sku-product-architect") -> ArtifactEnvelope:
    return ArtifactEnvelope(
        artifact_id=aid, artifact_type=atype, artifact_version=1,
        project_id="test", producer_agent=agent, producer_task_id="t1",
        status=ArtifactStatus.VALID, content_hash="sha256:abc123",
        payload=payload,
    )


def _good_spec() -> ProductSpec:
    return ProductSpec(
        spec_id="product-spec-v1", spec_version=1, spec_hash="sha256:abc123",
        project_id="test", target_market="US", selected_supplier_option="SUP-B",
        accepted_features=["d1"], rejected_features=["d2"], deferred_features=[],
        constraint_checks=[{"constraint_id": "c1", "passed": True, "actual": "7.80", "expected": "8.00", "operator": "<="}],
        artifact_refs=["e1", "s1", "ec1"], review_status="PENDING",
        approval_status=SpecApprovalStatus.DRAFT,
    )


def test_all_rules_registered():
    assert set(RULE_REGISTRY.keys()) == {f"R{i:03d}" for i in range(1, 19)}


def test_pass_when_everything_valid():
    artifacts = [
        _envelope("e1", ArtifactType.EVIDENCE, {"snapshot_id": "snap1", "locator": "l1", "is_synthetic": True, "source_type": "synthetic_fixture", "rights_status": "synthetic"}),
        _envelope("d1", ArtifactType.FEATURE_DECISION,
                  FeatureDecision(feature_id="f1", status=DecisionStatus.ACCEPT,
                                  market_refs=["p1"], supply_refs=["s1"], economics_refs=["ec1"],
                                  rationale="ok").model_dump()),
        _envelope("ec1", ArtifactType.ECONOMICS, {"calculation_trace": ["x=1"]}),
    ]
    spec = _good_spec()
    result = ReviewerGate.run(artifacts, spec)
    assert result.decision.value == "PASS"


def test_block_on_r003_hard_constraint_violation():
    spec = _good_spec()
    spec.constraint_checks = [{"constraint_id": "c1", "passed": False, "actual": "9.00", "expected": "8.00", "operator": "<="}]
    result = ReviewerGate.run([], spec)
    assert result.decision.value == "BLOCK"
    assert any(e.rule_id == "R003" for e in result.errors)


def test_block_on_r004_accept_without_evidence():
    artifacts = [
        _envelope("d1", ArtifactType.FEATURE_DECISION,
                  FeatureDecision(feature_id="f1", status=DecisionStatus.ACCEPT,
                                  market_refs=[], supply_refs=[], economics_refs=[]).model_dump()),
    ]
    result = ReviewerGate.run(artifacts, _good_spec())
    assert result.decision.value == "BLOCK"
    assert any(e.rule_id == "R004" for e in result.errors)


def test_block_on_r007_no_trace():
    artifacts = [
        _envelope("ec1", ArtifactType.ECONOMICS, {"calculation_trace": []}),
    ]
    result = ReviewerGate.run(artifacts, _good_spec())
    assert any(e.rule_id == "R007" for e in result.errors)


def test_block_on_r010_hash_mismatch():
    artifacts = [
        _envelope("r1", ArtifactType.REVIEW_RESULT, {"spec_hash": "sha256:wrong"}),
    ]
    spec = _good_spec()
    result = ReviewerGate.run(artifacts, spec)
    assert any(e.rule_id == "R010" for e in result.errors)


def test_block_on_r012_wrong_committer():
    artifacts = [
        _envelope("spec1", ArtifactType.PRODUCT_SPEC, {}, agent="gap2sku-market"),
    ]
    result = ReviewerGate.run(artifacts, _good_spec())
    assert any(e.rule_id == "R012" for e in result.errors)
