from __future__ import annotations

from gap2sku.artifacts.store import ArtifactStore
from gap2sku.governance.decision import DecisionEngine
from gap2sku.governance.gates import AcceptanceGate, FailureLoopback
from gap2sku.governance.models import (
    ApprovalRecord,
    DecisionPolicy,
    EvidenceState,
    ReviewFinding,
    ReviewReport,
)
from gap2sku.pipeline import _envelope
from gap2sku.schemas.envelope import ArtifactType
from gap2sku.tasking.models import TaskContract, TaskState
from gap2sku.tasking.store import TaskStore


def report(result: str = "REVISE") -> ReviewReport:
    findings = [] if result == "PASS" else [ReviewFinding(
        finding_id="f1", rule_id="SUP-001", severity="ERROR", result="FAIL",
        owner="gap2sku-supply", message="missing RFQ", remediation=["get RFQ"],
    )]
    return ReviewReport(
        review_id="r1", task_id="decision-r001", revision=1,
        product_spec_ref="spec", product_spec_hash="hash1",
        policy_version="policy-v3.0.0", review_result=result, findings=findings,
    )


def test_real_missing_supply_cannot_go() -> None:
    brief = DecisionEngine.evaluate(
        project_id="p", policy=DecisionPolicy(), review=report(),
        supplier_quote=EvidenceState.MISSING, bom=EvidenceState.MISSING,
        durability_test=EvidenceState.MISSING, material_test=EvidenceState.MISSING,
        conflict_refs=["c1"], option_refs=["o1"], data_mode="REAL",
    )
    assert brief.recommendation.value == "REVISE"
    assert len(brief.pending_confirmations) == 4


def test_approval_bound_to_hash_and_policy() -> None:
    approval = ApprovalRecord(
        approval_id="a", spec_hash="hash1", policy_version="policy-v3.0.0",
        approver="manager", reason="reviewed", decision="APPROVE",
    )
    assert DecisionEngine.approval_valid(approval, "hash1", "policy-v3.0.0")
    assert not DecisionEngine.approval_valid(approval, "hash2", "policy-v3.0.0")


def test_gate_and_failure_loopback(tmp_path) -> None:
    tasks = TaskStore(tmp_path / "state.db")
    artifacts = ArtifactStore(tmp_path / "state.db")
    task = tasks.create(TaskContract(
        task_id="decision-r001", project_id="p", owner="gap2sku-product-architect",
        idempotency_key="decision",
    ))
    tasks.advance(task.task_id, TaskState.READY, task.owner, "ready")
    tasks.advance(task.task_id, TaskState.RUNNING, task.owner, "run")
    tasks.advance(task.task_id, TaskState.SUBMITTED, task.owner, "submit")
    spec = _envelope("spec", ArtifactType.PRODUCT_SPEC, "p", task.owner, task.task_id, {"x": 1})
    artifacts.commit(spec, 0, "spec")
    gate = AcceptanceGate(tasks, artifacts)
    passed = gate.check(task.task_id, report("PASS"), ["spec"])
    assert passed.accepted
    gate.accept(task.task_id, passed, ["spec"])

    tasks2 = TaskStore(tmp_path / "loop.db")
    tasks2.create(TaskContract(
        task_id="decision-r001", project_id="p", owner="gap2sku-product-architect",
        idempotency_key="decision",
    ))
    created = FailureLoopback.create_revision_tasks(report(), tasks2)
    assert created == ["p-remediation-sup-001-r002"]
