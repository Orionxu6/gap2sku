from __future__ import annotations

import pytest

from gap2sku.tasking.models import TaskContract, TaskState
from gap2sku.tasking.store import TaskNotReady, TaskPermissionDenied, TaskStore


def task(task_id: str, owner: str = "gap2sku-market", depends_on: list[str] | None = None) -> TaskContract:
    return TaskContract(
        task_id=task_id, project_id="p1", owner=owner, depends_on=depends_on or [],
        idempotency_key=f"idem-{task_id}",
    )


def test_idempotency_and_transitions(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.db")
    first = store.create(task("market-r001"))
    duplicate = store.create(task("other-id").model_copy(update={"idempotency_key": first.idempotency_key}))
    assert duplicate.task_id == first.task_id
    store.advance(first.task_id, TaskState.READY, first.owner, "ready")
    store.advance(first.task_id, TaskState.RUNNING, first.owner, "start")
    store.advance(first.task_id, TaskState.SUBMITTED, first.owner, "done")
    with pytest.raises(TaskPermissionDenied):
        store.advance(first.task_id, TaskState.ACCEPTED, first.owner, "self approve")
    accepted = store.advance(first.task_id, TaskState.ACCEPTED, "acceptance-gate", "gate")
    assert accepted.state == TaskState.ACCEPTED
    assert len(store.events(first.task_id)) == 5


def test_owner_and_dependency_guards(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.db")
    store.create(task("upstream"))
    downstream = store.create(task("downstream", depends_on=["upstream"]))
    with pytest.raises(TaskNotReady):
        store.advance(downstream.task_id, TaskState.READY, downstream.owner, "too early")
    with pytest.raises(TaskPermissionDenied):
        store.advance("upstream", TaskState.READY, "gap2sku-supply", "wrong owner")


def test_revision_is_new_task(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.db")
    original = store.create(task("market-r001"))
    revised = store.create_revision(original.task_id, original.owner, "review finding")
    assert revised.task_id == "market-r002"
    assert revised.parent_task_id == original.task_id
    assert store.get(original.task_id).revision == 1
