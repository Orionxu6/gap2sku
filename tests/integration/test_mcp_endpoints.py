"""Integration test: MCP server endpoints (spec 13, 27.4)."""
from pathlib import Path

import pytest

from gap2sku.fixtures.generate import generate_fixture


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("fixture")
    generate_fixture(d, seed=42)
    return d


@pytest.fixture(scope="module")
def app(fixture_dir, tmp_path_factory):
    pytest.importorskip("starlette")
    from gap2sku.artifacts.store import ArtifactStore
    from gap2sku.mcp_server import create_app
    db = tmp_path_factory.mktemp("db") / "test.db"
    store = ArtifactStore(str(db))
    return create_app(fixture_dir, store)


@pytest.fixture
def client(app):
    from starlette.testclient import TestClient
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_agent_packages_are_served_from_an_exact_read_only_allowlist(client):
    package = client.get("/agent-packages/market.zip")
    assert package.status_code == 200
    assert package.headers["content-type"] == "application/zip"
    assert package.content.startswith(b"PK")
    assert client.get("/agent-packages/unknown.zip").status_code == 404


def test_market_can_list_snapshots(client):
    r = client.post("/market/mcp", json={"tool": "fixtures.list_snapshots", "args": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_real_role_tools_never_fall_back_to_laptop_fixture(client):
    competitors = client.post(
        "/market/mcp", json={"tool": "evidence.get_competitor_records", "args": {}}
    ).json()["result"]
    constraints = client.post(
        "/market/mcp", json={"tool": "state.get_constraints", "args": {}}
    ).json()["result"]
    hypotheses = client.post(
        "/supply/mcp", json={"tool": "artifact.get_feature_hypotheses", "args": {}}
    ).json()["result"]
    assert competitors["review_count"] == 389
    assert competitors["data_mode"] == "REAL"
    assert constraints["project_id"] == "nap-pillow-cn-20260811-001"
    assert "laptop" not in str(constraints).lower()
    assert hypotheses["data_mode"] == "REAL"
    assert "laptop" not in str(hypotheses).lower()


def test_market_cannot_call_leader_tool(client):
    r = client.post("/market/mcp", json={"tool": "state.create_run", "args": {}})
    assert r.status_code == 403


def test_role_submits_structured_handoff_without_mutating_business_state(client):
    response = client.post("/market/mcp", json={
        "tool": "collaboration.submit_handoff",
        "args": {
            "task_id": "nap-market-advisory-r001", "revision": 1,
            "summary": "真实评论支持痛点，但不证明供应能力。",
            "artifact_refs": ["nap-pain-points-v1"], "data_mode": "REAL",
        },
    })
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["accepted"] is True
    assert result["business_state_changed"] is False
    assert result["event"]["sender"] == "gap2sku-market"


def test_reviewer_cannot_call_market_tool(client):
    r = client.post("/review/mcp", json={"tool": "evidence.search_reviews", "args": {}})
    assert r.status_code == 403


def test_prototype_and_compliance_role_surfaces(client):
    prototype = client.get("/prototype/tools")
    compliance = client.get("/compliance/tools")
    assert prototype.status_code == 200
    assert {"concept.generate", "sample_spec.draft", "image.generate"} <= set(prototype.json()["tools"])
    assert {"compliance.evaluate", "knowledge.search"} <= set(compliance.json()["tools"])


def test_prototype_image_tool_persists_versioned_replay_manifest(client):
    generated = client.post("/prototype/mcp", json={
        "tool": "image.generate",
        "args": {
            "provider": "offline",
            "payload": {
                "prompt_id": "prompt-concept-a-runtime-v2",
                "project_id": "nap-pillow-cn-20260811-001",
                "concept_ref": "concept-a",
                "sample_spec_hash": None,
                "provider": "qwen-or-offline-replay",
                "model": "qwen-image-2.0",
                "seed": 17,
                "prompt": "午睡枕概念渲染",
                "negative_prompt": "品牌、认证标志",
                "input_refs": [],
            },
        },
    })
    assert generated.status_code == 200
    result = generated.json()["result"]
    assert result["event_type"] == "REPLAY_RENDER"
    assert result["manifest"]["label"] == "SYNTHETIC_CONCEPT"
    assert result["artifact_id"].startswith("agent-render-")
    fetched = client.post("/prototype/mcp", json={
        "tool": "image.get_manifest",
        "args": {"render_id": result["manifest"]["render_id"]},
    })
    assert fetched.json()["result"]["payload"]["asset_hash"].startswith("sha256:")


def test_streamable_http_role_mcp_is_real_and_minimal(fixture_dir, tmp_path) -> None:
    from starlette.testclient import TestClient

    from gap2sku.artifacts.store import ArtifactStore
    from gap2sku.mcp_server import create_app

    app = create_app(fixture_dir, ArtifactStore(tmp_path / "role-mcp.db"), include_official=True)
    headers = {"accept": "application/json, text/event-stream"}
    with TestClient(app, base_url="http://127.0.0.1") as role_client:
        initialized = role_client.post(
            "/mcp/market/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"},
                },
            },
        )
        assert initialized.status_code == 200
        listed = role_client.post(
            "/mcp/market/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        assert "evidence.search_reviews" in names
        assert "economics.calculate" not in names


def test_economics_calculate(client):
    r = client.post("/economics/mcp", json={
        "tool": "economics.calculate",
        "args": {
            "candidate_id": "test",
            "retail_price": "39.99", "factory_cost": "6.30",
            "feature_cost_deltas": ["0.80"], "packaging_cost": "0.80",
            "shipping_cost": "2.20", "fulfillment_fee": "3.50",
            "platform_fee_rate": "0.15", "marketing_rate": "0.08",
            "loss_allowance_rate": "0.03",
        }
    })
    assert r.status_code == 200
    data = r.json()["result"]
    assert Decimal(data["contribution_margin"]) > 0


from decimal import Decimal
