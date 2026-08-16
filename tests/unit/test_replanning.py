"""Tests for Selective Re-planning (spec 19, 27.2)."""
from gap2sku.graph.graph import ArtifactGraph, EdgeRelation, GraphNode
from gap2sku.graph.impact import ImpactAnalyzer
from gap2sku.schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType


def _env(aid: str, atype: ArtifactType, deps: list[str] | None = None) -> ArtifactEnvelope:
    return ArtifactEnvelope(
        artifact_id=aid, artifact_type=atype, artifact_version=1,
        project_id="proj", producer_agent="agent", producer_task_id="t",
        status=ArtifactStatus.VALID, content_hash="sha256:x",
        constraint_dependencies=deps or [], payload={},
    )


def _build_graph() -> tuple[ArtifactGraph, list[ArtifactEnvelope]]:
    g = ArtifactGraph()
    arts = [
        _env("evidence-v1", ArtifactType.EVIDENCE, ["target_market"]),
        _env("pain-v1", ArtifactType.PAIN_POINT_SET, ["target_market"]),
        _env("feature-v1", ArtifactType.FEATURE_HYPOTHESIS),
        _env("supplier-cap-v1", ArtifactType.SUPPLIER_CAPABILITY, ["moq_max"]),
        _env("supplier-assess-v1", ArtifactType.SUPPLIER_ASSESSMENT, ["factory_cost_max", "moq_max"]),
        _env("econ-v1", ArtifactType.ECONOMICS, ["factory_cost_max", "target_margin_min"]),
        _env("decision-v1", ArtifactType.FEATURE_DECISION),
        _env("spec-v1", ArtifactType.PRODUCT_SPEC),
        _env("review-v1", ArtifactType.REVIEW_RESULT),
    ]
    for a in arts:
        g.add_node(GraphNode(id=a.artifact_id, type=a.artifact_type.value))
    # edges: evidence -> pain -> feature -> decision -> spec -> review
    g.add_edge("evidence-v1", "pain-v1", EdgeRelation.DERIVED_FROM)
    g.add_edge("pain-v1", "feature-v1", EdgeRelation.MOTIVATES)
    g.add_edge("feature-v1", "supplier-assess-v1", EdgeRelation.VALIDATED_BY)
    g.add_edge("supplier-cap-v1", "supplier-assess-v1", EdgeRelation.DERIVED_FROM)
    g.add_edge("supplier-assess-v1", "econ-v1", EdgeRelation.CONSTRAINS)
    g.add_edge("econ-v1", "decision-v1", EdgeRelation.CONSTRAINS)
    g.add_edge("decision-v1", "spec-v1", EdgeRelation.DERIVED_FROM)
    g.add_edge("spec-v1", "review-v1", EdgeRelation.REVIEWED_BY)
    return g, arts


def test_factory_cost_max_skips_market():
    g, arts = _build_graph()
    analyzer = ImpactAnalyzer(g, arts)
    plan = analyzer.analyze("business.factory_cost_max", "chg-001", "proj")
    assert "gap2sku-market" in plan.skipped_agents
    assert "evidence-v1" in plan.preserved_artifacts
    assert "pain-v1" in plan.preserved_artifacts
    assert "supplier-assess-v1" not in plan.preserved_artifacts
    assert "econ-v1" not in plan.preserved_artifacts


def test_new_tasks_use_r002():
    g, arts = _build_graph()
    analyzer = ImpactAnalyzer(g, arts)
    plan = analyzer.analyze("business.factory_cost_max", "chg-001", "proj")
    for t in plan.new_tasks:
        assert "r002" in t


def test_review_snapshot_reruns_market():
    g, arts = _build_graph()
    analyzer = ImpactAnalyzer(g, arts)
    plan = analyzer.analyze("data.review_snapshot", "chg-002", "proj")
    assert "gap2sku-market" not in plan.skipped_agents
    assert "evidence-v1" not in plan.preserved_artifacts


def test_target_margin_only_economics_spec_review():
    g, arts = _build_graph()
    analyzer = ImpactAnalyzer(g, arts)
    plan = analyzer.analyze("business.target_margin_min", "chg-003", "proj")
    assert "econ-v1" not in plan.preserved_artifacts
    assert "supplier-assess-v1" in plan.preserved_artifacts  # supply not affected
