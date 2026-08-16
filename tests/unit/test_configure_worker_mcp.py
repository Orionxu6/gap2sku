from __future__ import annotations

import json
import subprocess

from gap2sku.cli.configure_worker_mcp import (
    WORKER_POLICIES,
    _policy_body,
    configure_worker,
)


def test_every_worker_policy_is_exact_and_default_ask() -> None:
    assert len(WORKER_POLICIES) == 7
    for policy in WORKER_POLICIES:
        assert "collaboration.submit_handoff" in policy.tools
        assert len(policy.tools) == len(set(policy.tools))
        body = _policy_body(policy.tools)
        assert body["default_effect"] == "ask"
        assert body["client_overrides"] == []
        assert body["tool_overrides"] == []
        assert {item["tool_name"] for item in body["tool_defaults"]} == set(policy.tools)
        assert {item["effect"] for item in body["tool_defaults"]} == {"allow"}


def test_configure_worker_does_not_enable_future_tool(monkeypatch) -> None:
    policy = WORKER_POLICIES[0]
    enabled = set(policy.tools) | {"future.dangerous_tool"}
    exact_policy = _policy_body(policy.tools)

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        nonlocal enabled
        url = args[-1]
        is_put = "-X" in args
        if "/api/mcp/tools/" in url:
            if is_put:
                body = json.loads(args[args.index("--data-binary") + 1])
                enabled = set(body["tools"])
            rows = [
                {"name": name, "enabled": name in enabled}
                for name in sorted(set(policy.tools) | {"future.dangerous_tool"})
            ]
            return subprocess.CompletedProcess(args, 0, json.dumps(rows), "")
        return subprocess.CompletedProcess(args, 0, json.dumps(exact_policy), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    report = configure_worker(policy)
    assert report["exact_policy_verified"] is True
    assert report["unknown_tools_enabled"] is False
    assert "future.dangerous_tool" not in report["enabled_tools"]
