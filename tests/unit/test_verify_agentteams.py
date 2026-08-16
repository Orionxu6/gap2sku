from __future__ import annotations

import subprocess

from gap2sku.cli import verify_agentteams
from gap2sku.cli.connect_matrix import _agt, _nested
from gap2sku.collaboration.models import CollaborationEvent
from gap2sku.collaboration.store import CollaborationStore


def _event(event_id: str, *, created_at: str, data_mode: str = "REAL") -> CollaborationEvent:
    return CollaborationEvent(
        event_id=event_id,
        project_id="nap-pillow-cn-20260811-001",
        task_id="run-current/runtime-r1",
        revision=1,
        event_type="HANDOFF",
        sender="gap2sku-market",
        recipients=["gap2sku-product-architect"],
        summary="structured handoff",
        artifact_refs=["artifact-1"],
        status="SUBMITTED",
        data_mode=data_mode,
        created_at=created_at,
    )


def test_runtime_handoffs_rejects_replay_and_previous_live_runs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store = CollaborationStore("shared/nap_pillow.db")
    try:
        store.append_event(_event("evt-demo-replay", created_at="2026-08-14T08:00:00Z"))
        store.append_event(_event("evt-agentteams-old", created_at="2026-08-14T08:00:00Z"))
        store.append_event(_event(
            "evt-agentteams-synthetic", created_at="2026-08-14T10:00:00Z", data_mode="SYNTHETIC",
        ))
        store.append_event(_event("evt-agentteams-current", created_at="2026-08-14T10:00:00Z"))
    finally:
        store.close()

    events = verify_agentteams._runtime_handoffs(
        after="2026-08-14T09:00:00Z", run_id="run-current",
    )

    assert [event.event_id for event in events] == ["evt-agentteams-current"]


def test_runtime_handoffs_require_the_current_run_id(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store = CollaborationStore("shared/nap_pillow.db")
    try:
        old = _event("evt-agentteams-old-run", created_at="2026-08-14T10:00:00Z")
        old.task_id = "run-old/market"
        current = _event("evt-agentteams-current-run", created_at="2026-08-14T10:00:00Z")
        store.append_event(old)
        store.append_event(current)
    finally:
        store.close()

    events = verify_agentteams._runtime_handoffs(after=None, run_id="run-current")
    assert [event.event_id for event in events] == ["evt-agentteams-current-run"]


def test_agt_uses_v122_plural_resource_commands(monkeypatch) -> None:
    command: list[str] = []

    def fake_run(args, **kwargs):
        command.extend(args)
        return subprocess.CompletedProcess(args, 0, stdout='{"metadata":{"name":"demo"}}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _agt("worker", "demo")["metadata"]["name"] == "demo"
    assert command[4:7] == ["get", "workers", "demo"]


def test_nested_accepts_v122_flat_and_legacy_resource_shapes() -> None:
    assert _nested({"phase": "Active"}, "status", "phase") == "Active"
    assert _nested({"status": {"phase": "Ready"}}, "status", "phase") == "Ready"
    assert _nested({"skills": ["one"]}, "spec", "skills") == "['one']"
