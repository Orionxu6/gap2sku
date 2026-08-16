"""Write Cloud Studio evidence only after every required runtime gate is proven."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

EXPECTED_SENDERS = {
    "gap2sku-product-architect",
    "gap2sku-market",
    "gap2sku-prototype-designer",
    "gap2sku-supply",
    "gap2sku-economics",
    "gap2sku-compliance",
    "gap2sku-reviewer",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def _http_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:  # noqa: S310 - fixed local health endpoints
        loaded = json.load(response)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object from {url}")
    return loaded


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(root: Path, *, started_at: str) -> dict[str, Any]:
    paths = {
        "runtime": root / "evidence/agentteams-runtime-verification.json",
        "nap_real": root / "evidence/nap-pillow/run.json",
        "nap_synthetic": root / "evidence/nap-pillow-synthetic/run.json",
        "durability_no_go": root / "evidence/nap-pillow/no-go-run.json",
        "new_category_public": root / "evidence/new-category-public/run.json",
        "new_category_synthetic": root / "evidence/new-category-synthetic/run.json",
        "golden_regression": root / "evidence/demo-core-run.json",
        "replan": root / "evidence/demo-replan-plan.json",
    }
    documents = {name: _read_json(path) for name, path in paths.items()}
    runtime = documents["runtime"]
    runtime_checks = runtime.get("checks", {})
    structured = runtime_checks.get("structured_handoffs", {})
    workers = runtime_checks.get("workers", {})
    team = runtime_checks.get("team", {})
    workbench = _http_json("http://127.0.0.1:8080/api/status")
    mcp = _http_json("http://127.0.0.1:18090/health")
    progress = workbench.get("active_run_progress", {})
    run_id = structured.get("run_id")

    checks: dict[str, bool] = {
        "runtime_end_to_end": runtime.get("end_to_end_verified") is True,
        "runtime_verified": runtime.get("runtime_verified") is True,
        "agentteams_v1_2_2": (
            runtime.get("agentteams_version_expected") == "v1.2.2"
            and runtime_checks.get("manager_version_pinned") is True
        ),
        "seven_workers_ready": (
            runtime_checks.get("seven_workers_ready") is True
            and isinstance(workers, dict)
            and set(workers) == EXPECTED_SENDERS
            and all(item.get("ready") and item.get("skills") for item in workers.values())
        ),
        "team_room_active": (
            runtime_checks.get("team_active") is True
            and team.get("room_present") is True
            and team.get("leader_ready") is True
        ),
        "seven_current_handoffs": (
            structured.get("complete") is True
            and structured.get("event_count", 0) >= 7
            and set(structured.get("senders", [])) == EXPECTED_SENDERS
            and bool(run_id)
        ),
        "handoffs_after_cloud_start": (
            isinstance(structured.get("after"), str)
            and _parse_time(structured["after"]) >= _parse_time(started_at)
        ),
        "workbench_live_matrix": (
            workbench.get("collaboration_mode") == "AGENTTEAMS_LIVE"
            and workbench.get("matrix_connected") is True
            and workbench.get("end_to_end_verified") is True
            and workbench.get("active_run_id") == run_id
            and progress.get("completed", 0) >= 7
            and progress.get("total") == 7
        ),
        "mcp_healthy": mcp.get("ok") is True and len(mcp.get("roles", [])) == 7,
        "nap_real_revise": (
            documents["nap_real"].get("recommendation") == "REVISE"
            and documents["nap_real"].get("data_mode") == "REAL"
            and documents["nap_real"].get("evidence_count") == 389
        ),
        "nap_synthetic_go": (
            documents["nap_synthetic"].get("recommendation") == "GO"
            and documents["nap_synthetic"].get("data_mode") == "SYNTHETIC"
        ),
        "durability_no_go": (
            documents["durability_no_go"].get("business_state") == "NO-GO"
            and documents["durability_no_go"].get("chat_is_business_state") is False
        ),
        "new_category_public_revise": (
            documents["new_category_public"].get("recommendation") == "REVISE"
            and documents["new_category_public"].get("artifact_count") == 24
            and documents["new_category_public"].get("public_signals_used_as_quote") is False
            and documents["new_category_public"].get("verified_profit") is None
        ),
        "new_category_synthetic_go": (
            documents["new_category_synthetic"].get("recommendation") == "GO"
            and documents["new_category_synthetic"].get("artifact_count") == 25
            and bool(documents["new_category_synthetic"].get("approval_ref"))
        ),
        "golden_regression_pass": (
            documents["golden_regression"].get("artifact_count") == 16
            and documents["golden_regression"].get("review", {}).get("decision") == "PASS"
        ),
        "local_replan_market_zero": (
            documents["replan"].get("market_agent_calls") == 0
            and documents["replan"].get("preserved_count", 0) > 0
        ),
    }
    return {
        "verified": all(checks.values()),
        "verification_scope": "CLOUD_STUDIO_E2E",
        "verified_at": _utcnow(),
        "cloud_run_started_at": started_at,
        "agentteams_run_id": run_id,
        "agentteams_version": "v1.2.2",
        "workers": 7,
        "checks": checks,
        "results": {
            "nap_real": "REVISE",
            "nap_synthetic": "GO",
            "durability_branch": "NO-GO",
            "new_category_public": "REVISE",
            "new_category_synthetic": "GO",
        },
        "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
        "input_sha256": {name: _sha256(path) for name, path in paths.items()},
        "secret_values_recorded": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--out", type=Path, default=Path("evidence/cloud-studio-e2e.json"))
    args = parser.parse_args()
    report = build_report(args.root, started_at=args.started_at)
    output = args.out if args.out.is_absolute() else args.root / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["verified"]:
        failed = sorted(name for name, passed in report["checks"].items() if not passed)
        raise SystemExit(f"Cloud Studio E2E gates failed: {failed}")


if __name__ == "__main__":
    main()
