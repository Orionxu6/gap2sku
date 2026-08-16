from __future__ import annotations

from gap2sku.collaboration.models import CollaborationEvent, MatrixMessageRecord
from gap2sku.collaboration.store import CollaborationStore
from gap2sku.governance.decision import DecisionEngine
from gap2sku.governance.models import DecisionPolicy, EvidenceState, ReviewReport
from gap2sku.product.workflow import CategoryRegistry, ProductWorkflow
from gap2sku.schemas.product import IntakeMode, ProductIntake, ProfileStatus, RFQPack
from gap2sku.story.service import ProductStoryService


def test_unknown_category_is_draft_and_not_go_eligible() -> None:
    intake = ProductIntake(
        project_id="new-p", mode=IntakeMode.OPPORTUNITY_DISCOVERY, title="新产品",
        target_market="US", target_users=["adult"], category_hint="unmapped device",
        idea_or_problem="发现机会", hard_constraints={"price": 50},
    )
    profile = CategoryRegistry.classify(intake)
    assert profile.status == ProfileStatus.DRAFT
    assert not profile.go_eligible
    assert CategoryRegistry.research_plan(intake, profile).fallback_mode == "EXPLICIT_REPLAY_SNAPSHOT"


def test_sample_spec_hash_is_locked_to_payload() -> None:
    workflow = ProductWorkflow("p")
    profile = CategoryRegistry.classify(workflow.intake())
    spec = workflow.sample_spec(profile, synthetic=True)
    assert spec.lock_status == "LOCKED"
    assert spec.spec_hash.startswith("sha256:")


def test_repeated_critical_failure_is_no_go() -> None:
    report = ReviewReport(
        review_id="r", task_id="t", revision=1, product_spec_ref="s",
        product_spec_hash="h", policy_version="policy-v3.0.0", review_result="REVISE", findings=[],
    )
    brief = DecisionEngine.evaluate(
        project_id="p", policy=DecisionPolicy(), review=report,
        supplier_quote=EvidenceState.CONFIRMED, bom=EvidenceState.CONFIRMED,
        durability_test=EvidenceState.CONFIRMED, material_test=EvidenceState.CONFIRMED,
        conflict_refs=[], option_refs=[], data_mode="REAL", repeated_critical_test_failure=True,
    )
    assert brief.recommendation.value == "NO-GO"
    assert brief.no_go_reasons


def test_collaboration_store_history_and_structured_events(tmp_path) -> None:
    store = CollaborationStore(tmp_path / "collab.db")
    store.append_message(MatrixMessageRecord(
        message_id="$1", room_id="!r", project_id="p", sender_id="@market:test",
        sender_role="gap2sku-market", body="done", origin_server_ts=1,
    ))
    store.append_event(CollaborationEvent(
        event_id="e1", project_id="p", task_id="t-r001", revision=1,
        event_type="HANDOFF", sender="gap2sku-market", recipients=["gap2sku-product-architect"],
        summary="submitted", artifact_refs=["a1"], status="accepted", data_mode="REAL",
        matrix_message_id="$1",
    ))
    assert store.list_messages("p")[0].message_id == "$1"
    assert store.list_events("p")[0].artifact_refs == ["a1"]
    store.close()


def test_story_views_share_bundle_and_supplier_is_redacted() -> None:
    workflow = ProductWorkflow("p")
    profile = CategoryRegistry.classify(workflow.intake())
    concepts = workflow.concepts(["pain"])
    sample = workflow.sample_spec(profile, synthetic=True)
    compliance, tests, _ = workflow.compliance(profile, synthetic=True)
    rfq = RFQPack(
        rfq_id="rfq", project_id="p", sample_spec_ref="s", sample_spec_hash=sample.spec_hash,
        render_refs=["r"], quantity=3, target_moq=500, target_lead_days=30,
        packaging_requirements=[], trade_terms=["EXW"], questions=[], status="READY_SYNTHETIC",
    )
    bundle = ProductStoryService.build(
        project_id="p", recommendation="GO", data_mode="SYNTHETIC", concepts=concepts,
        sample_spec=sample, rfq=rfq, compliance=compliance, tests=tests,
        economics={"margin": "40%"}, evidence={"count": 10}, review={"result": "PASS"},
    )
    supplier = ProductStoryService.for_view(bundle, "supplier")
    assert "economics" not in supplier["sections"]
    assert "supplier_rfq" in supplier["sections"]
