"""Apply exact, default-ask MCP permissions to every Gap2SKU QwenPaw Worker.

The AgentTeams Worker CR creates the role-scoped MCP client, but QwenPaw v1.2.2
leaves new clients in ``ask`` mode.  Interactive approvals are unsuitable for
an unattended Team run.  This module enables only the reviewed tools below and
keeps both unknown and future tools disabled/ask.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkerMCPPolicy:
    worker: str
    client_key: str
    tools: tuple[str, ...]


COMMON_ARTIFACT_TOOLS = (
    "artifact.get",
    "artifact.get_current",
    "artifact.list",
    "artifact.list_current",
    "artifact.validate",
)


WORKER_POLICIES = (
    WorkerMCPPolicy(
        "gap2sku-product-architect",
        "gap2sku-leader-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.subgraph",
            "collaboration.submit_handoff",
            "context.build_bundle",
            "graph.get_subgraph",
            "knowledge.ingest",
            "knowledge.search",
            "observability.trace",
            "replan.preview",
            "state.create_run",
            "state.get_constraints",
            "state.get_project",
            "task.advance",
            "task.create",
        ),
    ),
    WorkerMCPPolicy(
        "gap2sku-market",
        "gap2sku-market-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.validate_local",
            "collaboration.submit_handoff",
            "evidence.get_competitor_records",
            "evidence.get_source",
            "evidence.search",
            "evidence.search_reviews",
            "fixtures.list_snapshots",
            "knowledge.ingest",
            "knowledge.search",
            "observability.trace",
            "state.get_constraints",
            "task.advance",
            "task.get",
            "task.list",
        ),
    ),
    WorkerMCPPolicy(
        "gap2sku-supply",
        "gap2sku-supply-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.get_feature_hypotheses",
            "artifact.validate_local",
            "collaboration.submit_handoff",
            "conflict.generate_options",
            "evidence.get_source",
            "evidence.get_supplier_records",
            "fixtures.list_snapshots",
            "knowledge.ingest",
            "knowledge.search",
            "observability.trace",
            "review.run",
            "state.get_constraints",
            "task.advance",
            "task.get",
            "task.list",
        ),
    ),
    WorkerMCPPolicy(
        "gap2sku-economics",
        "gap2sku-economics-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.validate_local",
            "collaboration.submit_handoff",
            "decision.evaluate",
            "economics.calculate",
            "economics.current",
            "economics.verify",
            "knowledge.ingest",
            "knowledge.search",
            "observability.trace",
            "state.get_constraints",
            "task.advance",
            "task.get",
            "task.list",
        ),
    ),
    WorkerMCPPolicy(
        "gap2sku-reviewer",
        "gap2sku-review-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.subgraph",
            "collaboration.submit_handoff",
            "evidence.get_source",
            "evidence.search",
            "graph.get_subgraph",
            "knowledge.ingest",
            "knowledge.search",
            "observability.trace",
            "replan.preview",
            "review.run",
            "review.run_rules",
            "task.advance",
            "task.get",
            "task.list",
        ),
    ),
    WorkerMCPPolicy(
        "gap2sku-prototype-designer",
        "gap2sku-prototype-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.diff",
            "artifact.validate_local",
            "collaboration.submit_handoff",
            "concept.generate",
            "image.generate",
            "image.get_manifest",
            "sample_spec.draft",
            "sample_spec.lock",
        ),
    ),
    WorkerMCPPolicy(
        "gap2sku-compliance",
        "gap2sku-compliance-tools",
        COMMON_ARTIFACT_TOOLS
        + (
            "artifact.validate_local",
            "collaboration.submit_handoff",
            "compliance.classify",
            "compliance.evaluate",
            "knowledge.search",
        ),
    ),
)


def _container_name(worker: str) -> str:
    return f"agentteams-worker-{worker}"


def _request(policy: WorkerMCPPolicy, path: str, *, method: str = "GET", body: Any = None) -> Any:
    command = [
        "docker",
        "exec",
        _container_name(policy.worker),
        "curl",
        "-fsS",
        "--max-time",
        "20",
    ]
    if method != "GET":
        command.extend(["-X", method, "-H", "Content-Type: application/json"])
    if body is not None:
        command.extend(["--data-binary", json.dumps(body, separators=(",", ":"), sort_keys=True)])
    command.append(f"http://127.0.0.1:8088/api/mcp/{path}/{policy.client_key}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{policy.worker}: QwenPaw MCP API request failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{policy.worker}: QwenPaw MCP API returned invalid JSON") from exc


def _policy_body(tools: tuple[str, ...]) -> dict[str, Any]:
    return {
        "default_effect": "ask",
        "client_overrides": [],
        "tool_defaults": [
            {"effect": "allow", "tool_name": tool_name}
            for tool_name in sorted(set(tools))
        ],
        "tool_overrides": [],
        "unmanaged_rules_count": 0,
    }


def configure_worker(policy: WorkerMCPPolicy) -> dict[str, Any]:
    listed = _request(policy, "tools")
    if not isinstance(listed, list):
        raise RuntimeError(f"{policy.worker}: MCP tool listing is not a list")
    available = {str(item.get("name")) for item in listed if isinstance(item, dict)}
    expected = set(policy.tools)
    missing = sorted(expected - available)
    if missing:
        raise RuntimeError(f"{policy.worker}: declared MCP tools are unavailable: {missing}")

    _request(policy, "tools", method="PUT", body={"tools": sorted(expected)})
    _request(policy, "policy", method="PUT", body=_policy_body(policy.tools))

    verified_tools = _request(policy, "tools")
    verified_policy = _request(policy, "policy")
    enabled = {
        str(item.get("name"))
        for item in verified_tools
        if isinstance(item, dict) and item.get("enabled") is True
    }
    tool_defaults = {
        str(item.get("tool_name")): str(item.get("effect"))
        for item in verified_policy.get("tool_defaults", [])
        if isinstance(item, dict)
    }
    if enabled != expected:
        raise RuntimeError(f"{policy.worker}: exact MCP whitelist verification failed")
    if verified_policy.get("default_effect") != "ask":
        raise RuntimeError(f"{policy.worker}: MCP default effect is not ask")
    if tool_defaults != {name: "allow" for name in expected}:
        raise RuntimeError(f"{policy.worker}: exact MCP allow policy verification failed")
    if verified_policy.get("client_overrides") or verified_policy.get("tool_overrides"):
        raise RuntimeError(f"{policy.worker}: wildcard or principal MCP overrides are forbidden")
    return {
        "worker": policy.worker,
        "client_key": policy.client_key,
        "default_effect": "ask",
        "enabled_tools": sorted(enabled),
        "unknown_tools_enabled": False,
        "exact_policy_verified": True,
    }


def configure_all(*, attempts: int = 15, retry_seconds: float = 2.0) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for policy in WORKER_POLICIES:
        last_error: RuntimeError | None = None
        for _ in range(attempts):
            try:
                reports.append(configure_worker(policy))
                break
            except RuntimeError as exc:
                last_error = exc
                time.sleep(retry_seconds)
        else:
            assert last_error is not None
            raise last_error
    report = {
        "configured": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "agentteams_version": "v1.2.2",
        "default_effect": "ask",
        "future_unknown_tools_allowed": False,
        "workers": reports,
    }
    output = Path("evidence/agentteams-mcp-policy.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=15)
    parser.add_argument("--retry-seconds", type=float, default=2.0)
    args = parser.parse_args()
    print(json.dumps(configure_all(attempts=args.attempts, retry_seconds=args.retry_seconds), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
