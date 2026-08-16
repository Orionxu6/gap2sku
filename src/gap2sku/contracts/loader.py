from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ContractError(RuntimeError):
    pass


TOOL_CAPABILITY_MAP = {
    "market_evidence_mcp": ["evidence.search", "evidence.get_source"],
    "review_mining_mcp": ["evidence.search_reviews"],
    "competitor_data_mcp": ["evidence.search_reviews"],
    "trend_data_mcp": ["knowledge.search"],
    "supplier_evidence_mcp": ["evidence.get_source", "supplier.discover", "rfq.import_response"],
    "supplier_assessment_mcp": ["artifact.validate"],
    "manufacturability_mcp": ["conflict.generate_options"],
    "certification_registry_mcp": ["knowledge.search"],
    "sample_quality_mcp": ["review.run"],
    "packaging_logistics_mcp": ["knowledge.search"],
    "economics_calculator": ["decision.evaluate"],
    "fee_policy_mcp": ["knowledge.search"],
    "logistics_rate_mcp": ["knowledge.search"],
    "fx_rate_mcp": ["knowledge.search"],
    "review_rule_engine": ["review.run"],
    "artifact_graph": ["artifact.subgraph", "replan.preview"],
    "artifact_store": ["artifact.get", "artifact.list", "artifact.validate"],
    "evidence_store": ["evidence.get_source", "evidence.search"],
    "economics_verifier": ["review.run"],
    "task_store": ["task.get", "task.list", "task.advance"],
    "task_queue": ["task.create", "task.advance"],
    "state_machine": ["task.advance"],
    "schema_validator": ["artifact.validate"],
    "memory": ["knowledge.search", "knowledge.ingest"],
    "notification": ["observability.trace"],
    "image_generation_mcp": ["image.generate", "image.get_manifest"],
    "sample_spec_mcp": ["sample_spec.lock", "artifact.diff"],
    "compliance_policy_mcp": ["compliance.classify", "compliance.evaluate"],
}

AUDIT_EVENTS = {"DECISION_RECORD", "MODEL_DEGRADED", "BUDGET_WARNING"}
LEADER_RUNTIME_ROUTES = {
    "TASK_ASSIGNMENT": [
        "gap2sku-market", "gap2sku-supply", "gap2sku-economics",
        "gap2sku-prototype-designer", "gap2sku-compliance", "gap2sku-reviewer",
    ],
    "CONSULT": [
        "gap2sku-market", "gap2sku-supply", "gap2sku-economics",
        "gap2sku-prototype-designer", "gap2sku-compliance", "gap2sku-reviewer",
    ],
    "DECISION_REQUEST": ["gap2sku-reviewer", "human-manager"],
    "DECISION_RECORD": ["audit-manager", "human-manager"],
    "EARLY_NO_GO_SIGNAL": ["gap2sku-reviewer", "human-manager"],
    "HUMAN_DECISION_REQUIRED": ["human-manager"],
    "REVISION_REQUIRED": [
        "gap2sku-market", "gap2sku-supply", "gap2sku-economics",
        "gap2sku-prototype-designer", "gap2sku-compliance", "gap2sku-reviewer",
    ],
    "HANDOFF": ["gap2sku-reviewer", "human-manager"],
    "MODEL_DEGRADED": ["audit-manager", "human-manager"],
    "BUDGET_WARNING": ["audit-manager", "human-manager"],
}
RUNTIME_SKILLS_BY_AGENT = {
    "gap2sku-product-architect": [
        "product-spec-synthesis", "impact-aware-replanning", "agent-contract-validation",
        "evidence-conflict-decision",
    ],
    "gap2sku-market": ["market-evidence-mining", "evidence-conflict-decision"],
    "gap2sku-prototype-designer": ["product-concept-synthesis", "evidence-conflict-decision"],
    "gap2sku-supply": ["supplier-capability-assessment", "evidence-conflict-decision"],
    "gap2sku-economics": ["unit-economics-evaluation", "evidence-conflict-decision"],
    "gap2sku-compliance": ["compliance-safety-assessment", "evidence-conflict-decision"],
    "gap2sku-reviewer": [
        "evidence-review-gate", "agent-contract-validation", "evidence-conflict-decision",
    ],
}
WORKER_CONFIG_BY_AGENT = {
    "gap2sku-product-architect": "worker-product-architect.yaml",
    "gap2sku-market": "worker-market.yaml",
    "gap2sku-prototype-designer": "worker-prototype-designer.yaml",
    "gap2sku-supply": "worker-supply.yaml",
    "gap2sku-economics": "worker-economics.yaml",
    "gap2sku-compliance": "worker-compliance.yaml",
    "gap2sku-reviewer": "worker-reviewer.yaml",
}
ALLOWED_TOP_LEVEL = {
    "meta", "runtime_adapter", "model", "planner", "event_aliases",
    "event_subscriptions", "event_emissions", "event_routing", "event_contract",
    "completion_signal", "io", "state_machine", "hard_constraints",
    "human_checkpoints", "budget", "skills", "tools", "tool_denials",
    "memory_scope", "degradation", "observability", "eval", "evidence_policy",
    "supply_policy", "economics_policy", "review_policy", "escalation_triggers",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class LoadedContract:
    name: str
    root: Path
    data: dict[str, Any]
    source_hash: str


class ContractLoader:
    REQUIRED_FILES = {"agent.yaml", "AGENTS.md", "MEMORY.md", "memory.scope", "rubrics.md", "SOUL.md"}

    def __init__(self, raw_dir: str | Path, build_dir: str | Path = "agent_packages/build") -> None:
        self.raw_dir = Path(raw_dir)
        self.build_dir = Path(build_dir)

    @staticmethod
    def _parse_yaml(path: Path) -> dict[str, Any]:
        try:
            import yaml  # type: ignore[import-untyped]
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except ImportError:
            ruby = subprocess.run(
                ["ruby", "-ryaml", "-rjson", "-e", "puts JSON.generate(YAML.load_file(ARGV[0]))", str(path)],
                check=True, capture_output=True, text=True,
            )
            value = json.loads(ruby.stdout)
        if not isinstance(value, dict):
            raise ContractError(f"agent.yaml must contain an object: {path}")
        return value

    def normalize_sources(self) -> list[Path]:
        roots: list[Path] = []
        self.build_dir.mkdir(parents=True, exist_ok=True)
        for source in sorted(p for p in self.raw_dir.iterdir() if p.is_dir()):
            destination = self.build_dir / source.name
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
            duplicate_soul = destination / "SOUL.md.md"
            if duplicate_soul.exists() and not (destination / "SOUL.md").exists():
                duplicate_soul.rename(destination / "SOUL.md")
            contract_text = (destination / "agent.yaml").read_text(encoding="utf-8")
            if source.name == "leader" and "\nevent_routing:" not in contract_text:
                route_lines = ["", "# Gap2SKU normalized runtime routing; locked source remains unchanged.", "event_routing:"]
                for event, targets in LEADER_RUNTIME_ROUTES.items():
                    route_lines.append(f"  {event}: [{', '.join(targets)}]")
                contract_text += "\n".join(route_lines) + "\n"
                (destination / "agent.yaml").write_text(contract_text, encoding="utf-8")
            schema_refs = self._schema_refs((destination / "agent.yaml").read_text(encoding="utf-8"))
            for relative in schema_refs:
                self._write_schema(destination / relative)
            roots.append(destination)
        return roots

    def load_all(self, env: dict[str, str] | None = None) -> list[LoadedContract]:
        environment = env or dict(os.environ)
        if environment.get("GAP2SKU_AGENT_CONTRACT_LOADER") not in {"1", "strict", "gap2sku.agent/v1"}:
            raise ContractError("GAP2SKU_AGENT_CONTRACT_LOADER must explicitly enable gap2sku.agent/v1")
        roots = self.normalize_sources()
        loaded: list[LoadedContract] = []
        agent_ids: set[str] = set()
        for root in roots:
            data = self._parse_yaml(root / "agent.yaml")
            unknown = set(data) - ALLOWED_TOP_LEVEL
            if unknown:
                raise ContractError(f"{root.name}: unknown top-level fields {sorted(unknown)}")
            adapter = data.get("runtime_adapter", {})
            if adapter.get("contract") != "gap2sku.agent/v1" or adapter.get("on_missing") != "fail_startup":
                raise ContractError(f"{root.name}: strict runtime adapter required")
            refs = [
                data.get("meta", {}).get(key)
                for key in ("soul_ref", "protocol_ref", "rubric_ref", "memory_scope_ref")
            ] + self._schema_refs((root / "agent.yaml").read_text(encoding="utf-8"))
            missing = [ref for ref in refs if ref and not (root / str(ref)).resolve().is_file()]
            if missing:
                raise ContractError(f"{root.name}: missing references {missing}")
            agent_id = str(data.get("meta", {}).get("agent_id", ""))
            if not agent_id or agent_id in agent_ids:
                raise ContractError(f"{root.name}: empty or duplicate agent_id {agent_id!r}")
            agent_ids.add(agent_id)
            self._check_model_env(root.name, data, environment)
            self._check_permissions(root.name, data)
            self._check_budget(root.name, data)
            loaded.append(LoadedContract(root.name, root, data, self._tree_hash(root)))
        if len(loaded) != 7:
            raise ContractError(f"expected five locked plus two first-party agent contracts, got {len(loaded)}")
        return loaded

    @staticmethod
    def _schema_refs(text: str) -> list[str]:
        # Inline YAML mappings end references with `}` (and may use commas).
        # Those delimiters are syntax, never part of the referenced filename.
        matches = re.findall(r"schema_ref:\s*([^\s#,}\]]+)", text)
        return sorted(set(match.strip("'\"").removeprefix("./") for match in matches))

    @staticmethod
    def _write_schema(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        title = path.stem.removesuffix(".schema")
        common: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"https://gap2sku.local/schemas/{path.name}",
            "title": title, "type": "object", "additionalProperties": False,
            "properties": {"schema_version": {"type": "string"}},
        }
        if path.name == "task-contract.schema.json":
            common.update({
                "required": ["task_id", "project_id", "owner", "revision", "state", "idempotency_key"],
                "properties": {
                    "task_id": {"type": "string"}, "project_id": {"type": "string"},
                    "owner": {"type": "string"}, "revision": {"type": "integer", "minimum": 1},
                    "state": {"enum": ["PENDING", "READY", "RUNNING", "SUBMITTED", "ACCEPTED", "REVISE", "BLOCKED", "FAILED", "CANCELLED"]},
                    "idempotency_key": {"type": "string"}, "input_refs": {"type": "array", "items": {"type": "string"}},
                },
            })
        elif path.name == "collab-event.schema.json":
            common.update({
                "required": ["event_id", "event_type", "task_id", "revision", "from_role", "to_roles", "confidence", "data_mode", "requested_action"],
                "properties": {
                    "event_id": {"type": "string"}, "event_type": {"type": "string"},
                    "task_id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1},
                    "from_role": {"type": "string"}, "to_roles": {"type": "array", "items": {"type": "string"}},
                    "artifact_refs": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "data_mode": {"enum": ["REAL", "SYNTHETIC", "MIXED"]},
                    "requested_action": {"type": "string"}, "payload": {"type": "object"},
                },
            })
        else:
            # The source package's required_fields remain authoritative in
            # agent.yaml; the generated envelope is strict and versioned.
            common["properties"] = {
                "schema_version": {"type": "string"},
                "artifact_id": {"type": "string"}, "task_id": {"type": "string"},
                "revision": {"type": "integer", "minimum": 1},
                "data_mode": {"enum": ["REAL", "SYNTHETIC", "MIXED"]},
                "payload": {"type": "object"}, "evidence_refs": {"type": "array", "items": {"type": "string"}},
            }
            common["required"] = ["schema_version", "artifact_id", "task_id", "revision", "data_mode", "payload"]
        path.write_text(json.dumps(common, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _check_model_env(name: str, data: dict[str, Any], environment: dict[str, str]) -> None:
        text = json.dumps(data, ensure_ascii=False)
        required = set(re.findall(r"\$\{([A-Z0-9_]+)\}", text))
        missing = sorted(key for key in required if not environment.get(key))
        if missing:
            raise ContractError(f"{name}: missing environment variables {missing}")

    @staticmethod
    def _check_permissions(name: str, data: dict[str, Any]) -> None:
        skills = data.get("skills", {})
        if skills.get("default_policy") != "deny" or skills.get("unknown_skill_behavior") != "deny_and_emit_permission_event":
            raise ContractError(f"{name}: Skill policy must default-deny")
        unknown_tools = [tool.get("name") for tool in data.get("tools", []) if tool.get("name") not in TOOL_CAPABILITY_MAP]
        if unknown_tools:
            raise ContractError(f"{name}: unmapped contract tools {unknown_tools}")

    @staticmethod
    def _check_budget(name: str, data: dict[str, Any]) -> None:
        budget = data.get("budget")
        if not isinstance(budget, dict) or not budget:
            raise ContractError(f"{name}: budget section required")

    @staticmethod
    def event_routes(contract: LoadedContract) -> dict[str, list[str]]:
        routes = contract.data.get("event_routing", {})
        output: dict[str, list[str]] = {}
        for event in contract.data.get("event_emissions", []):
            configured = routes.get(event, [])
            if isinstance(configured, list):
                output[event] = configured
            elif isinstance(configured, dict):
                output[event] = configured.get("allowed_targets", ["gap2sku-product-architect"])
            else:
                output[event] = []
            if event in AUDIT_EVENTS and not output[event]:
                output[event] = ["audit-manager", "human-manager"]
        return output

    @staticmethod
    def _tree_hash(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def compile(self, env: dict[str, str] | None = None) -> dict[str, Any]:
        contracts = self.load_all(env)
        repo_root = self.raw_dir.resolve().parents[1]
        available_skills = {
            path.parent.name
            for base in (repo_root / "skills", repo_root / "contributions/skills")
            if base.exists()
            for path in base.glob("*/SKILL.md")
        }
        required_runtime_skills = {
            skill for skills in RUNTIME_SKILLS_BY_AGENT.values() for skill in skills
        }
        missing_runtime_skills = sorted(required_runtime_skills - available_skills)
        if missing_runtime_skills:
            raise ContractError(f"runtime Skill packages missing: {missing_runtime_skills}")
        package_dir = Path("packages")
        package_dir.mkdir(parents=True, exist_ok=True)
        identity: list[dict[str, Any]] = []
        workers: list[str] = []
        for contract in contracts:
            agent_id = contract.data["meta"]["agent_id"]
            package_path = package_dir / f"{contract.name}.zip"
            with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(p for p in contract.root.rglob("*") if p.is_file()):
                    archive.write(path, f"{contract.name}/{path.relative_to(contract.root)}")
            tools = [tool["name"] for tool in contract.data.get("tools", [])]
            contract_skills = [skill["id"] for skill in contract.data.get("skills", {}).get("allowed", [])]
            runtime_skills = RUNTIME_SKILLS_BY_AGENT[agent_id]
            worker_config = repo_root / "configs/agentteams" / WORKER_CONFIG_BY_AGENT[agent_id]
            if not worker_config.is_file():
                raise ContractError(f"{agent_id}: AgentTeams Worker config missing")
            assigned_skills = self._parse_yaml(worker_config).get("spec", {}).get("skills", [])
            if assigned_skills != runtime_skills:
                raise ContractError(
                    f"{agent_id}: Worker skills {assigned_skills} do not match {runtime_skills}"
                )
            identity.append({
                "agent_id": agent_id, "role": contract.data["meta"].get("role"),
                "contract_version": contract.data["meta"].get("version"),
                "package": str(package_path), "package_sha256": _sha256(package_path),
                "source_tree_sha256": contract.source_hash,
                "skills": runtime_skills, "contract_skill_names": contract_skills,
                "skill_assignment_consistent": True, "tools": tools,
                "capability_mapping": {name: TOOL_CAPABILITY_MAP[name] for name in tools},
                "event_routes": self.event_routes(contract),
            })
            workers.append(agent_id)
        report = {
            "contract": "gap2sku.agent/v1", "valid": True,
            "agent_count": len(identity), "agents": identity,
            "team": {"name": "gap2sku-definition", "leader": "gap2sku-product-architect", "members": workers},
            "audit_routes": {event: ["audit-manager", "human-manager"] for event in sorted(AUDIT_EVENTS)},
        }
        Path("evidence").mkdir(exist_ok=True)
        Path("evidence/agent-contract-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return report
