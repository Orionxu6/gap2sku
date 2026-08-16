"""Verify the local AgentTeams runtime without exposing credentials."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gap2sku.cli.connect_matrix import WORKERS, _agt, _nested
from gap2sku.collaboration.store import CollaborationStore

LIVE_EVENT_PREFIX = "evt-agentteams-"
LIVE_EVENT_TYPES = {"HANDOFF", "DECISION_RECORD"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _runtime_handoffs(*, after: str | None, run_id: str | None = None) -> list[Any]:
    """Return only real structured Worker events created by this runtime run.

    Deterministic demo/replay events deliberately use different IDs.  The
    timestamp boundary prevents a previous successful live run from satisfying
    a later verification attempt.
    """
    store = CollaborationStore("shared/nap_pillow.db")
    try:
        events = store.list_events("nap-pillow-cn-20260811-001", limit=500)
    finally:
        store.close()
    return [
        event for event in events
        if event.event_id.startswith(LIVE_EVENT_PREFIX)
        and event.event_type in LIVE_EVENT_TYPES
        and event.data_mode == "REAL"
        and (after is None or event.created_at >= after)
        and (run_id is None or run_id in event.task_id)
    ]


def _phase(resource: dict[str, Any]) -> str:
    return (_nested(resource, "status", "phase") or _nested(resource, "status", "state")).upper()


def _container_running(name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _manager_image() -> str:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.Config.Image}}", "agentteams-manager"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _controller_version() -> str:
    result = subprocess.run(
        ["docker", "exec", "agentteams-manager", "agt", "version"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def verify(
    *, wait_events: int = 0, after: str | None = None, run_id: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["manager_container_running"] = _container_running("agentteams-manager")
    checks["manager_image"] = _manager_image()
    checks["manager_version"] = checks["manager_image"].rsplit(":", 1)[-1]
    checks["manager_version_pinned"] = checks["manager_version"] == "v1.2.2"
    # The official v1.2.2 embedded controller currently self-reports "dev".
    # Record that diagnostic separately; the immutable image tag is the release
    # identity used by the official installer and by this pinning check.
    checks["controller_reported_version"] = _controller_version()
    worker_reports: dict[str, Any] = {}
    for name in WORKERS:
        resource = _agt("worker", name)
        phase = _phase(resource)
        matrix_user = _nested(resource, "status", "matrixUserID")
        nested_spec = resource.get("spec")
        spec: dict[str, Any] = nested_spec if isinstance(nested_spec, dict) else resource
        skills = spec.get("skills", [])
        worker_reports[name] = {
            "phase": phase,
            "ready": phase in {"READY", "ACTIVE", "RUNNING"},
            "matrix_identity_present": bool(matrix_user),
            "skills": skills,
        }
    team = _agt("team", "gap2sku-definition")
    human = _agt("human", "gap2sku-observer")
    nested_team_status = team.get("status")
    team_status: dict[str, Any] = (
        nested_team_status if isinstance(nested_team_status, dict) else team
    )
    checks["workers"] = worker_reports
    checks["seven_workers_ready"] = len(worker_reports) == 7 and all(
        item["ready"] for item in worker_reports.values()
    )
    checks["seven_matrix_identities"] = all(
        item["matrix_identity_present"] for item in worker_reports.values()
    )
    checks["team"] = {
        "phase": _phase(team),
        "room_present": bool(team_status.get("teamRoomID")),
        "leader_ready": bool(team_status.get("leaderReady")),
        "ready_workers": team_status.get("readyWorkers"),
        "total_workers": team_status.get("totalWorkers"),
    }
    checks["team_active"] = (
        checks["team"]["phase"] in {"ACTIVE", "READY", "RUNNING"}
        and checks["team"]["room_present"]
    )
    checks["observer"] = {
        "phase": _phase(human),
        "matrix_identity_present": bool(_nested(human, "status", "matrixUserID")),
        "credentials_present": bool(_nested(human, "status", "initialPassword")),
    }
    checks["observer_ready"] = checks["observer"]["matrix_identity_present"]

    structured: dict[str, Any] = {
        "required": wait_events > 0,
        "after": after,
        "run_id": run_id,
        "event_id_prefix": LIVE_EVENT_PREFIX,
        "senders": [],
        "complete": wait_events == 0,
    }
    if wait_events > 0:
        deadline = time.monotonic() + wait_events
        required = set(WORKERS)
        while time.monotonic() < deadline:
            events = _runtime_handoffs(after=after, run_id=run_id)
            senders = {event.sender for event in events}
            structured = {
                "required": True,
                "after": after,
                "run_id": run_id,
                "event_id_prefix": LIVE_EVENT_PREFIX,
                "senders": sorted(senders),
                "missing": sorted(required - senders),
                "event_count": len(events),
                "complete": required <= senders,
            }
            if structured["complete"]:
                break
            time.sleep(2)
    checks["structured_handoffs"] = structured
    runtime_checks = [
        checks["manager_container_running"], checks["seven_workers_ready"],
        checks["manager_version_pinned"],
        checks["seven_matrix_identities"], checks["team_active"], checks["observer_ready"],
    ]
    runtime_verified = all(runtime_checks)
    verified = runtime_verified and checks["structured_handoffs"]["complete"]
    report = {
        "verified": verified,
        "runtime_verified": runtime_verified,
        "end_to_end_verified": runtime_verified and wait_events > 0 and structured["complete"],
        "verification_scope": "RUNTIME_AND_HANDOFFS" if wait_events > 0 else "RUNTIME_RESOURCES",
        "generated_at": _utcnow(),
        "agentteams_version_expected": "v1.2.2",
        "secret_values_recorded": False,
        "checks": checks,
    }
    if write_report:
        output = Path("evidence/agentteams-runtime-verification.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-events", type=int, default=0, help="seconds to wait for all seven handoffs")
    parser.add_argument(
        "--after", default=None,
        help="ISO-8601 UTC lower bound for structured runtime events from this demo run",
    )
    parser.add_argument("--run-id", default=None, help="unique run identifier required in every handoff task_id")
    parser.add_argument(
        "--no-write", action="store_true",
        help="check current resources without replacing the durable end-to-end evidence report",
    )
    args = parser.parse_args()
    report = verify(
        wait_events=args.wait_events,
        after=args.after,
        run_id=args.run_id,
        write_report=not args.no_write,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
