from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from gap2sku.contracts.loader import ContractError, ContractLoader
from gap2sku.fixtures.generate import generate_fixture

ENV = {
    "GAP2SKU_AGENT_CONTRACT_LOADER": "strict", "MODEL_PROVIDER": "qwen",
    "LEADER_MODEL_NAME": "qwen-plus", "MARKET_MODEL_NAME": "qwen-plus",
    "SUPPLY_MODEL_NAME": "qwen-plus", "ECONOMICS_MODEL_NAME": "qwen-plus",
    "REVIEWER_MODEL_NAME": "qwen-plus", "DEMO_SEED": "1",
    "PROTOTYPE_MODEL_NAME": "qwen-plus", "COMPLIANCE_MODEL_NAME": "qwen-plus",
}


def test_compile_seven_contracts(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    report = ContractLoader("/Users/orionxu/Documents/gap2sku/agent_packages/raw", tmp_path / "build").compile(ENV)
    assert report["valid"] and report["agent_count"] == 7
    leader = next(agent for agent in report["agents"] if agent["agent_id"] == "gap2sku-product-architect")
    assert leader["event_routes"]["DECISION_RECORD"] == ["audit-manager", "human-manager"]
    assert all(leader["event_routes"].values())
    assert leader["skills"] == [
        "product-spec-synthesis", "impact-aware-replanning", "agent-contract-validation",
        "evidence-conflict-decision",
    ]
    assert (tmp_path / "build/leader/SOUL.md").exists()
    assert "\nevent_routing:" not in Path(
        "/Users/orionxu/Documents/gap2sku/agent_packages/raw/leader/agent.yaml"
    ).read_text(encoding="utf-8")
    assert "\nevent_routing:" in (tmp_path / "build/leader/agent.yaml").read_text(encoding="utf-8")
    for package in (tmp_path / "packages").glob("*.zip"):
        with zipfile.ZipFile(package) as archive:
            assert all(not name.endswith("}") for name in archive.namelist())


def test_loader_env_and_missing_schema_fail(tmp_path) -> None:
    with pytest.raises(ContractError, match="GAP2SKU_AGENT_CONTRACT_LOADER"):
        ContractLoader("agent_packages/raw", tmp_path / "build").load_all({})
    shutil.copytree("agent_packages/raw", tmp_path / "raw")
    loader = ContractLoader(tmp_path / "raw", tmp_path / "build2")
    loader.normalize_sources()
    (tmp_path / "build2/market/schemas/task-contract.schema.json").unlink()
    # load_all normalizes again, proving the compiler repairs declared source omissions.
    assert len(loader.load_all(ENV)) == 7


def test_every_compiled_capability_exists_on_the_role_mcp(tmp_path, monkeypatch) -> None:
    from gap2sku.artifacts.store import ArtifactStore
    from gap2sku.mcp_server import _build_tools

    monkeypatch.chdir(tmp_path)
    report = ContractLoader(
        "/Users/orionxu/Documents/gap2sku/agent_packages/raw", tmp_path / "build"
    ).compile(ENV)
    fixture_dir = tmp_path / "fixture"
    generate_fixture(fixture_dir, seed=9)
    store = ArtifactStore(tmp_path / "runtime.db")
    role_tools = _build_tools(store, fixture_dir)
    role_by_agent = {
        "gap2sku-product-architect": "leader", "gap2sku-market": "market",
        "gap2sku-prototype-designer": "prototype", "gap2sku-supply": "supply",
        "gap2sku-economics": "economics", "gap2sku-compliance": "compliance",
        "gap2sku-reviewer": "review",
    }
    for agent in report["agents"]:
        expected = {
            capability
            for capabilities in agent["capability_mapping"].values()
            for capability in capabilities
        }
        actual = set(role_tools[role_by_agent[agent["agent_id"]]])
        assert expected <= actual, f"{agent['agent_id']} missing {sorted(expected - actual)}"
    store.close()
