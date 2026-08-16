from __future__ import annotations

from dataclasses import dataclass, field

from ..artifacts.store import ArtifactStore
from ..schemas.envelope import ArtifactStatus
from ..tasking.models import TaskContract, TaskState
from ..tasking.store import TaskStore
from .models import ApprovalRecord, ReviewReport


@dataclass
class GateResult:
    accepted: bool
    errors: list[str] = field(default_factory=list)


class AcceptanceGate:
    def __init__(self, tasks: TaskStore, artifacts: ArtifactStore) -> None:
        self.tasks = tasks
        self.artifacts = artifacts

    def check(
        self, task_id: str, review: ReviewReport, required_artifact_refs: list[str],
        approval: ApprovalRecord | None = None,
    ) -> GateResult:
        errors: list[str] = []
        task = self.tasks.get(task_id)
        if not task or task.state != TaskState.SUBMITTED:
            errors.append("task must be SUBMITTED")
        if review.review_result != "PASS":
            errors.append(f"review result is {review.review_result}, not PASS")
        for ref in required_artifact_refs:
            artifact = self.artifacts.get(ref)
            if not artifact:
                errors.append(f"missing artifact: {ref}")
            elif artifact.status not in {ArtifactStatus.VALID, ArtifactStatus.ACCEPTED}:
                errors.append(f"artifact {ref} is {artifact.status.value}")
        if approval is not None and (
            approval.spec_hash != review.product_spec_hash
            or approval.policy_version != review.policy_version
        ):
            errors.append("approval does not match spec hash and policy version")
        return GateResult(accepted=not errors, errors=errors)

    def accept(self, task_id: str, result: GateResult, artifact_refs: list[str]) -> None:
        if not result.accepted:
            raise ValueError("acceptance gate failed: " + "; ".join(result.errors))
        self.tasks.advance(task_id, TaskState.ACCEPTED, "acceptance-gate", "all gates passed", artifact_refs)


class FailureLoopback:
    OWNER_BY_RULE_PREFIX = {
        "MKT": "gap2sku-market", "SUP": "gap2sku-supply",
        "ECO": "gap2sku-economics", "POL": "gap2sku-compliance",
        "SEC": "gap2sku-product-architect",
        "CMP": "gap2sku-compliance", "TEST": "gap2sku-compliance",
    }

    @classmethod
    def create_revision_tasks(cls, report: ReviewReport, tasks: TaskStore) -> list[str]:
        created: list[str] = []
        for finding in report.findings:
            if finding.result not in {"FAIL", "BLOCK"}:
                continue
            owner = finding.owner or cls.OWNER_BY_RULE_PREFIX.get(finding.rule_id[:3], "gap2sku-product-architect")
            parent = tasks.get(report.task_id)
            if parent is None:
                continue
            suffix = finding.rule_id.lower().replace("_", "-")
            revision = tasks.create(TaskContract(
                task_id=f"{parent.project_id}-remediation-{suffix}-r{parent.revision + 1:03d}",
                project_id=parent.project_id, owner=owner, revision=parent.revision + 1,
                state=TaskState.PENDING, depends_on=[], input_refs=finding.artifact_refs,
                expected_artifact_types=[], acceptance_criteria=finding.remediation,
                idempotency_key=f"loopback:{report.review_id}:{finding.finding_id}",
                parent_task_id=parent.task_id,
            ))
            created.append(revision.task_id)
        return sorted(set(created))
