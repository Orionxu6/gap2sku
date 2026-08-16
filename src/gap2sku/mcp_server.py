"""Gap2SKU MCP Server — multi-role endpoints (spec 13).

One process, role-isolated endpoints:
  /market/mcp   /supply/mcp   /economics/mcp   /review/mcp   /leader/mcp

Each endpoint only exposes its whitelisted tools (spec 13.2).
Transport: Streamable HTTP (P1: full MCP SDK; P0: HTTP JSON for demo-core).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

from .artifacts.store import ArtifactStore
from .collaboration.models import CollaborationEvent
from .collaboration.store import CollaborationStore
from .context.router import ContextRouter
from .economics.calculator import EconomicsCalculator, EconomicsInput
from .evidence.reviews import ReviewWorkbookImporter
from .fixtures.generate import generate_fixture
from .graph.graph import ArtifactGraph
from .imaging.providers import ImageGenerationError, OfflineImageProvider, QwenImageProvider
from .knowledge.retriever import SQLiteKnowledgeRetriever
from .observability.trace import TraceEvent, TraceRecorder
from .pipeline import DomainCorePipeline
from .product.workflow import CategoryRegistry, ProductWorkflow
from .review.rules import ReviewerGate
from .schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from .schemas.product import (
    ProductIntake,
    PublicSupplierSignal,
    PublicSupplierSignalSet,
    RenderPromptRecord,
    SupplierQuoteSet,
)
from .tasking.models import TaskContract, TaskState
from .tasking.store import TaskStore

try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import FileResponse, JSONResponse, Response
    from starlette.routing import Mount, Route
    HAS_STARLETTE = True
except ImportError:
    HAS_STARLETTE = False


# --- Tool registry per role (spec 13.2) ---
def _build_tools(store: ArtifactStore, fixture_dir: Path) -> dict[str, dict[str, Callable]]:
    pipeline_state: dict[str, Any] = {"pipeline": None, "graph": ArtifactGraph(), "artifacts": []}
    product_workflow = ProductWorkflow("nap-pillow-cn-20260811-001")
    project_id = "nap-pillow-cn-20260811-001"
    task_store = TaskStore(store.db_path)
    knowledge = SQLiteKnowledgeRetriever(store.db_path.with_name("knowledge.db"))
    trace = TraceRecorder("evidence/nap-pillow/agentteams-trace.jsonl")

    def load_object(path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object: {path}")
        return value

    def fixtures_list_snapshots(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() != "SYNTHETIC":
            imported = ReviewWorkbookImporter("private/raw_reviews").import_all()
            return {
                "snapshots": ["nap-pillow-reviews-20260811-v1"],
                "report": imported.report,
                "data_mode": "REAL",
            }
        manifest = load_object(fixture_dir / "manifest.json")
        return {"snapshots": ["reviews-laptop-stand-us-synthetic-v1"], "manifest": manifest}

    def evidence_search_reviews(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() != "SYNTHETIC":
            imported = ReviewWorkbookImporter("private/raw_reviews").import_all()
            query = str(args.get("query") or args.get("keyword") or "")
            rows = [
                record.model_dump(mode="json")
                for record in imported.records
                if not query or query.lower() in record.content_excerpt.lower()
            ]
            limit = min(int(args.get("limit", 50)), 100)
            return {"reviews": rows[:limit], "data_mode": "REAL", "total": len(rows), "report": imported.report}
        reviews = [json.loads(line) for line in (fixture_dir / "reviews.synthetic.jsonl").read_text().splitlines() if line.strip()]
        keyword = args.get("keyword")
        if keyword:
            reviews = [r for r in reviews if keyword.lower() in r.get("text", "").lower()]
        return {"reviews": reviews[:50], "is_synthetic": True, "total": len(reviews)}

    def evidence_get_competitor_records(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() != "SYNTHETIC":
            imported = ReviewWorkbookImporter("private/raw_reviews").import_all()
            return {
                "source": "authorized_workbook_import",
                "category": "student nap pillow",
                "brand_distribution": imported.report["distribution"],
                "review_count": imported.report["total"],
                "duplicate_count": imported.report["duplicate_count"],
                "limitations": imported.report["limitations"],
                "data_mode": "REAL",
            }
        return load_object(fixture_dir / "competitors.synthetic.json")

    def evidence_get_supplier_records(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() != "SYNTHETIC":
            quotes = store.list_by_type("SupplierQuoteSet", project_id)
            return {
                "status": "CONFIRMED" if quotes else "MISSING",
                "quotes": [item.payload for item in quotes],
                "data_mode": "REAL",
                "next_action": "import real RFQ response" if not quotes else "review quote scope and validity",
            }
        return load_object(fixture_dir / "supplier_offers.synthetic.json")

    def state_get_constraints(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() == "SYNTHETIC":
            from .pipeline import default_constraints
            cs = default_constraints("laptop-stand-us-20260803-001")
            return cs.model_dump(mode="json")
        intakes = store.list_by_type(ArtifactType.PRODUCT_INTAKE.value, project_id)
        if intakes:
            payload = intakes[-1].payload
            return {
                "project_id": project_id,
                "title": payload.get("title"),
                "target_market": payload.get("target_market"),
                "target_users": payload.get("target_users", []),
                "hard_constraints": payload.get("hard_constraints", {}),
                "data_mode": "REAL",
            }
        return {
            "project_id": project_id,
            "hard_constraints": {"target_price_cny": [99, 119], "target_margin": 0.40,
                                 "launch_weeks": 12},
            "status": "REPLAY_FALLBACK",
            "data_mode": "REAL",
        }

    def artifact_validate_local(args: dict) -> dict:
        artifact_id = str(args.get("artifact_id", ""))
        if not artifact_id:
            return {"valid": False, "errors": ["artifact_id is required"]}
        artifact = store.get(artifact_id, args.get("version"))
        if not artifact:
            return {"valid": False, "errors": ["artifact not found"]}
        missing = [ref for ref in artifact.input_refs if store.get(ref) is None]
        return {
            "valid": not missing,
            "errors": [f"missing ref {ref}" for ref in missing],
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def artifact_get_feature_hypotheses(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() != "SYNTHETIC":
            rows = store.list_by_type(ArtifactType.FEATURE_HYPOTHESIS.value, project_id)
            if rows:
                return {"artifact_id": rows[-1].artifact_id, "data_mode": "REAL", **rows[-1].payload}
            concepts = store.list_by_type(ArtifactType.PRODUCT_CONCEPT_SET.value, project_id)
            if concepts:
                return {"artifact_id": concepts[-1].artifact_id, "data_mode": "REAL", **concepts[-1].payload}
            return {"status": "MISSING", "data_mode": "REAL", "next_action": "run market research"}
        return load_object(fixture_dir / "feature_taxonomy.v1.json")

    def economics_calculate(args: dict) -> dict:
        inp = EconomicsInput.from_dict(args)
        art = EconomicsCalculator.calculate(inp)
        return art.model_dump(mode="json")

    def economics_verify(args: dict) -> dict:
        inp = EconomicsInput.from_dict(args["input"])
        art_data = args["artifact"]
        from .schemas.economics import EconomicsArtifact
        art = EconomicsArtifact(**art_data)
        ok = EconomicsCalculator.verify(inp, art)
        return {"verified": ok}

    def review_run_rules(args: dict) -> dict:
        if str(args.get("data_mode", "REAL")).upper() != "SYNTHETIC":
            reviews = store.list_by_type("ReviewResult", project_id)
            if reviews:
                return reviews[-1].payload
            return {"review_result": "BLOCK", "reason": "ReviewResult artifact missing", "data_mode": "REAL"}
        # In offline mode, run pipeline then review
        if pipeline_state["pipeline"] is None:
            p = DomainCorePipeline(fixture_dir, store)
            p.run()
            pipeline_state["pipeline"] = p
            pipeline_state["artifacts"] = p.artifacts
            pipeline_state["graph"] = p.graph
        p = pipeline_state["pipeline"]
        spec_env = next((a for a in p.artifacts if a.artifact_type == ArtifactType.PRODUCT_SPEC), None)
        if not spec_env:
            return {"error": "no spec found"}
        from .schemas.spec import ProductSpec
        spec = ProductSpec(**spec_env.payload)
        review = ReviewerGate.run(p.artifacts, spec)
        return review.model_dump(mode="json")

    def graph_get_subgraph(args: dict) -> dict:
        ids = [str(item) for item in args.get("artifact_ids", [])]
        if not ids and args.get("artifact_id"):
            ids = [str(args["artifact_id"])]
        edges: list[dict[str, Any]] = []
        nodes: dict[str, dict[str, Any]] = {}
        frontier = set(ids)
        included = set(ids)
        for _ in range(max(0, min(int(args.get("depth", 2)), 5))):
            next_frontier: set[str] = set()
            for artifact_id in frontier:
                for edge in store.edges_from(artifact_id) + store.edges_to(artifact_id):
                    src, dst = str(edge["src_id"]), str(edge["dst_id"])
                    edges.append({"from": src, "to": dst, "relation": edge["relation"]})
                    next_frontier.update((src, dst))
            next_frontier -= included
            included |= next_frontier
            frontier = next_frontier
        for artifact_id in included:
            artifact = store.get(artifact_id)
            if artifact:
                nodes[artifact_id] = {
                    "id": artifact.artifact_id, "type": artifact.artifact_type.value,
                    "version": artifact.artifact_version, "status": artifact.status.value,
                }
        unique_edges = list({(e["from"], e["to"], e["relation"]): e for e in edges}.values())
        return {"nodes": list(nodes.values()), "edges": unique_edges}

    def artifact_diff(args: dict) -> dict:
        artifact_id = str(args.get("artifact_id", ""))
        left = store.get(artifact_id, int(args.get("left_version", 1)))
        right = store.get(artifact_id, int(args.get("right_version", 2)))
        if not left or not right:
            return {"error": "version not found"}
        keys = sorted(set(left.payload) | set(right.payload))
        return {
            "artifact_id": artifact_id,
            "changes": {
                key: {"left": left.payload.get(key), "right": right.payload.get(key)}
                for key in keys if left.payload.get(key) != right.payload.get(key)
            },
        }

    def context_build_bundle(args: dict) -> dict:
        artifacts = store.list_all(project_id)
        bundle, _ = ContextRouter.build_bundle(
            args.get("project_id", project_id),
            args.get("task_id", ""), args.get("role", "market"),
            artifacts or pipeline_state.get("artifacts", []),
        )
        return bundle.model_dump(mode="json")

    def state_create_run(args: dict) -> dict:
        if not bool(args.get("synthetic")):
            return {
                "created": False,
                "reason": "REAL project state is created by the governed pipeline; use task/artifact tools",
            }
        p = DomainCorePipeline(fixture_dir, store)
        result = p.run()
        pipeline_state["pipeline"] = p
        pipeline_state["artifacts"] = p.artifacts
        pipeline_state["graph"] = p.graph
        return result

    def state_get_project(args: dict) -> dict:
        run_path = Path("evidence/nap-pillow/run.json")
        run = json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}
        return {
            "project_id": project_id,
            "status": "active",
            "data_mode": "REAL",
            "recommendation": run.get("decision", {}).get("recommendation", "REVISE"),
            "artifact_count": len(store.list_all(project_id)),
        }

    def artifact_list_current(args: dict) -> dict:
        artifact_type = str(args.get("artifact_type", ""))
        rows = store.list_by_type(artifact_type, project_id) if artifact_type else store.list_all(project_id)
        return {
            "artifacts": [
                {
                    "artifact_id": item.artifact_id, "artifact_type": item.artifact_type,
                    "version": item.artifact_version, "status": item.status, "data_mode": item.data_mode,
                    "content_hash": item.content_hash,
                }
                for item in rows
            ],
            "project_id": project_id,
        }

    def artifact_get_current(args: dict) -> dict:
        artifact = store.get(str(args.get("artifact_id", "")), args.get("version"))
        return artifact.model_dump(mode="json") if artifact else {"error": "artifact not found"}

    def task_create(args: dict) -> dict:
        payload = args.get("payload", args)
        return task_store.create(TaskContract(**payload)).model_dump(mode="json")

    def task_get(args: dict) -> dict:
        task = task_store.get(str(args.get("task_id", "")))
        return task.model_dump(mode="json") if task else {"error": "task not found"}

    def task_list(args: dict) -> dict:
        state = TaskState(str(args["state"])) if args.get("state") else None
        return {
            "tasks": [
                task.model_dump(mode="json")
                for task in task_store.list(str(args.get("project_id", project_id)), state)
            ]
        }

    def task_advance_for(role: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        actor = role_agent[role]

        def advance(args: dict[str, Any]) -> dict[str, Any]:
            target = TaskState(str(args.get("state", args.get("to_state", ""))))
            task = task_store.advance(
                str(args.get("task_id", "")), target, actor,
                str(args.get("reason", "AgentTeams structured transition")),
                [str(item) for item in args.get("artifact_refs", [])],
            )
            return task.model_dump(mode="json")

        return advance

    def evidence_search(args: dict) -> dict:
        query = str(args.get("query", ""))
        limit = max(1, min(int(args.get("limit", 20)), 100))
        imported = ReviewWorkbookImporter("private/raw_reviews").import_all()
        rows = [
            item.model_dump(mode="json") for item in imported.records
            if not query or query.lower() in item.content_excerpt.lower()
        ]
        return {"evidence": rows[:limit], "total": len(rows), "data_mode": "REAL"}

    def evidence_get_source(args: dict) -> dict:
        evidence_id = str(args.get("evidence_id", ""))
        imported = ReviewWorkbookImporter("private/raw_reviews").import_all()
        match = next((item for item in imported.records if item.evidence_id == evidence_id), None)
        return match.model_dump(mode="json") if match else {"error": "evidence not found"}

    def supplier_discover(args: dict) -> dict:
        category = str(args.get("category", "")).lower()
        if not any(token in category for token in ("headphone", "headset", "耳机", "desk")):
            return {
                "signal_set": None,
                "notice": "no replay snapshot; use an authorized connector or user export",
            }
        snapshot = load_object(Path("data/public_signals/desk_headphone_hanger.json"))
        signals = []
        for row in snapshot["signals"]:
            encoded = json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
            signals.append(
                PublicSupplierSignal(
                    signal_id=row["signal_id"],
                    supplier_name=row["supplier_name"],
                    source_url=row["source_url"],
                    captured_at=snapshot["captured_at"],
                    source_hash="sha256:" + hashlib.sha256(encoded).hexdigest(),
                    observed_facts=row["observed_facts"],
                    limitations=row["limitations"],
                )
            )
        return {
            "signal_set": PublicSupplierSignalSet(
                signal_set_id=snapshot["snapshot_id"],
                project_id="desk-headphone-hanger-us-public-001",
                signals=signals,
            ).model_dump(mode="json"),
            "notice": "PUBLIC_LISTING_SIGNAL only; never a verified supplier quote",
        }

    def rfq_import_response(args: dict) -> dict:
        payload = args.get("payload")
        if not isinstance(payload, dict):
            return {"accepted": False, "error": "payload is required"}
        task = task_store.get(str(args.get("task_id", "")))
        actor = str(args.get("actor", ""))
        if not task or task.owner != "gap2sku-supply":
            return {"accepted": False, "error": "active Supply task required"}
        if actor not in {"gap2sku-supply", "human-manager"}:
            return {"accepted": False, "error": "actor is not authorized"}
        quote_set = SupplierQuoteSet(**payload)
        rfq = store.get(quote_set.rfq_ref)
        if not rfq or rfq.payload.get("sample_spec_hash") != quote_set.sample_spec_hash:
            return {"accepted": False, "error": "RFQ/spec hash mismatch"}
        invalid = [
            quote.quote_id
            for quote in quote_set.quotes
            if quote.data_mode != "REAL" or quote.verification_level != "SUPPLIER_RESPONSE"
        ]
        if invalid or not quote_set.source_document_hash.startswith("sha256:"):
            return {
                "accepted": False,
                "error": "REAL supplier response and source document SHA-256 required",
                "invalid_quote_ids": invalid,
            }
        body = quote_set.model_dump(mode="json")
        envelope = ArtifactEnvelope(
            artifact_id=quote_set.quote_set_id,
            artifact_type=ArtifactType.SUPPLIER_QUOTE_SET,
            artifact_version=1,
            project_id=quote_set.project_id,
            producer_agent="gap2sku-supply",
            producer_task_id=task.task_id,
            status=ArtifactStatus.VALID,
            input_refs=[quote_set.rfq_ref],
            content_hash="sha256:" + hashlib.sha256(
                json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            data_mode="REAL",
            payload=body,
        )
        committed = store.commit(
            envelope,
            store.project_revision(quote_set.project_id),
            f"rfq-import:{quote_set.quote_set_id}:{quote_set.source_document_hash}",
        )
        return {"accepted": True, "artifact": committed.model_dump(mode="json")}

    def knowledge_search(args: dict) -> dict:
        rows = knowledge.search(str(args.get("query", "")), int(args.get("limit", 5)))
        return {"citations": [row.model_dump(mode="json") for row in rows],
                "trust_level": "UNTRUSTED_RETRIEVAL"}

    def knowledge_ingest(args: dict) -> dict:
        citation_id = knowledge.ingest(
            str(args.get("title", "")), str(args.get("source_uri", "")), str(args.get("body", "")),
        )
        return {"citation_id": citation_id, "trust_level": "UNTRUSTED_RETRIEVAL",
                "can_authorize_business_fact": False}

    def observability_trace_for(role: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def record(args: dict[str, Any]) -> dict[str, Any]:
            event = TraceEvent(
                run_id=str(args.get("run_id", "agentteams-local")), project_id=project_id,
                task_id=str(args.get("task_id", "")), agent_name=role_agent[role],
                agent_role=role, tool_name=str(args.get("tool_name", "notification")),
                tool_call_id=str(args.get("tool_call_id", "")),
                artifact_id=str(args.get("artifact_id", "")),
                result_status=str(args.get("result_status", "RECORDED")),
            )
            trace.record(event)
            return {"recorded": True, "business_state_changed": False}

        return record

    def conflict_generate_options(args: dict) -> dict:
        conflict_id = str(args.get("conflict_id", ""))
        options = [
            row.payload for row in store.list_by_type(ArtifactType.OPTION_CARD.value, project_id)
            if row.payload.get("conflict_id") == conflict_id
        ]
        return {"conflict_id": conflict_id, "options": options,
                "generated": False, "reason": "returns versioned deterministic options only"}

    def decision_evaluate(args: dict) -> dict:
        briefs = store.list_by_type(ArtifactType.DECISION_BRIEF.value, project_id)
        return briefs[-1].payload if briefs else {"error": "DecisionBrief not found"}

    def sample_spec_lock(args: dict) -> dict:
        return {
            "locked": False, "human_checkpoint_required": True,
            "reason": "Prototype Worker cannot lock SampleSpec; Human Manager must bind the spec hash",
            "proposed_spec": args.get("payload", args),
        }

    def compliance_classify(args: dict) -> dict:
        payload = args.get("payload")
        intake = product_workflow.intake() if not isinstance(payload, dict) else ProductIntake(**payload)
        return CategoryRegistry.classify(intake).model_dump(mode="json")

    def replan_preview(args: dict) -> dict:
        path = str(args.get("changed_path", args.get("path", "")))
        affected = [
            row.artifact_id for row in store.list_all(project_id)
            if path in row.constraint_dependencies
        ]
        return {
            "change_id": str(args.get("change_id", "preview")), "changed_path": path,
            "recompute_artifacts": sorted(affected),
            "preserved_artifacts": sorted(
                row.artifact_id for row in store.list_all(project_id) if row.artifact_id not in affected
            ),
            "execute_requires_human_confirmation": True,
        }

    def economics_current(args: dict) -> dict:
        rows = store.list_by_type("EconomicsArtifact", project_id)
        return rows[-1].payload if rows else {
            "factory_cost_state": "MISSING", "gross_margin": None, "data_mode": "REAL",
            "warning": "No real RFQ/BOM; verified profit is unavailable",
        }

    def concept_generate(args: dict) -> dict:
        return product_workflow.concepts(args.get("pain_point_refs", [])).model_dump(mode="json")

    def sample_spec_draft(args: dict) -> dict:
        profile = CategoryRegistry.classify(product_workflow.intake())
        return product_workflow.sample_spec(profile, synthetic=True).model_dump(mode="json")

    def image_get_manifest(args: dict) -> dict:
        render_id = str(args.get("render_id", ""))
        rows = store.list_by_type(ArtifactType.RENDER_MANIFEST.value, project_id)
        match = next((row for row in reversed(rows) if row.payload.get("render_id") == render_id), None)
        return match.model_dump(mode="json") if match else {"error": "render manifest not found"}

    def image_generate(args: dict) -> dict:
        payload = args.get("payload")
        concept_id = str(args.get("concept_id", "concept-a"))
        prompt_rows = store.list_by_type(ArtifactType.RENDER_PROMPT.value, project_id)
        prompt_env = next(
            (row for row in reversed(prompt_rows) if row.payload.get("concept_ref") == concept_id),
            None,
        )
        if isinstance(payload, dict):
            record = RenderPromptRecord(**payload)
            prompt_env = next(
                (row for row in reversed(prompt_rows) if row.payload.get("prompt_id") == record.prompt_id),
                None,
            )
        elif prompt_env:
            record = RenderPromptRecord(**prompt_env.payload)
        else:
            return {"error": "versioned RenderPromptRecord not found", "event_type": "NEEDS_EVIDENCE"}

        if prompt_env is None:
            missing = [ref for ref in record.input_refs if store.get(ref) is None]
            if missing:
                return {"error": "RenderPromptRecord has missing input_refs", "missing_refs": missing}
            prompt_payload = record.model_dump(mode="json")
            prompt_id = f"agent-{record.prompt_id}"
            prompt_env = store.commit(
                ArtifactEnvelope(
                    artifact_id=prompt_id, artifact_type=ArtifactType.RENDER_PROMPT,
                    artifact_version=1, project_id=project_id,
                    producer_agent="gap2sku-prototype-designer",
                    producer_task_id=str(args.get("task_id", f"{project_id}-prototype-r002")),
                    status=ArtifactStatus.VALID, input_refs=record.input_refs,
                    policy_version="policy-v3.0.0", data_mode="SYNTHETIC",
                    content_hash="sha256:" + hashlib.sha256(
                        json.dumps(prompt_payload, sort_keys=True, ensure_ascii=False).encode()
                    ).hexdigest(), payload=prompt_payload,
                ),
                store.project_revision(project_id), f"render-prompt:{record.prompt_id}",
            )

        requested = str(args.get("provider", "auto")).lower()
        use_qwen = requested == "qwen" or (requested == "auto" and bool(os.environ.get("DASHSCOPE_API_KEY")))
        degraded_reason = ""
        try:
            adapter = QwenImageProvider() if use_qwen else OfflineImageProvider()
            manifest = adapter.generate(record)
            event_type = "IMAGE_GENERATED" if use_qwen else "REPLAY_RENDER"
        except ImageGenerationError as exc:
            if not use_qwen:
                return {"error": str(exc), "event_type": "MODEL_DEGRADED"}
            degraded_reason = str(exc)
            try:
                manifest = OfflineImageProvider().generate(record)
            except ImageGenerationError as fallback_exc:
                return {
                    "error": "online and replay image providers failed",
                    "provider_error": degraded_reason,
                    "fallback_error": str(fallback_exc),
                    "event_type": "MODEL_DEGRADED",
                }
            event_type = "MODEL_DEGRADED"

        manifest = manifest.model_copy(update={"prompt_ref": prompt_env.artifact_id})
        manifest_payload = manifest.model_dump(mode="json")
        artifact_id = f"agent-{manifest.render_id}"
        current = store.get(artifact_id)
        version = current.artifact_version + 1 if current else 1
        render_env = store.commit(
            ArtifactEnvelope(
                artifact_id=artifact_id, artifact_type=ArtifactType.RENDER_MANIFEST,
                artifact_version=version, project_id=project_id,
                producer_agent="gap2sku-prototype-designer",
                producer_task_id=str(args.get("task_id", f"{project_id}-prototype-r002")),
                status=ArtifactStatus.VALID, input_refs=[prompt_env.artifact_id],
                policy_version="policy-v3.0.0", data_mode="SYNTHETIC",
                content_hash="sha256:" + hashlib.sha256(
                    json.dumps(manifest_payload, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(), payload=manifest_payload,
            ),
            store.project_revision(project_id),
            f"render-manifest:{record.prompt_id}:{manifest.asset_hash}",
        )
        store.add_edge(
            prompt_env.artifact_id, prompt_env.artifact_version,
            render_env.artifact_id, render_env.artifact_version, "DERIVED_FROM",
        )
        return {
            "manifest": manifest_payload,
            "artifact_id": render_env.artifact_id,
            "artifact_version": render_env.artifact_version,
            "event_type": event_type,
            "fallback_reason": degraded_reason or None,
            "business_state_changed": False,
        }

    def compliance_evaluate(args: dict) -> dict:
        profile = CategoryRegistry.classify(product_workflow.intake())
        assessment, tests, claims = product_workflow.compliance(profile, synthetic=bool(args.get("synthetic", False)))
        return {"assessment": assessment.model_dump(mode="json"),
                "test_matrix": tests.model_dump(mode="json"),
                "claim_register": claims.model_dump(mode="json")}

    role_tools: dict[str, dict[str, Callable]] = {
        "market": {
            "fixtures.list_snapshots": fixtures_list_snapshots,
            "evidence.search_reviews": evidence_search_reviews,
            "evidence.get_competitor_records": evidence_get_competitor_records,
            "state.get_constraints": state_get_constraints,
            "artifact.validate_local": artifact_validate_local,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
        "supply": {
            "fixtures.list_snapshots": fixtures_list_snapshots,
            "evidence.get_supplier_records": evidence_get_supplier_records,
            "state.get_constraints": state_get_constraints,
            "artifact.get_feature_hypotheses": artifact_get_feature_hypotheses,
            "artifact.validate_local": artifact_validate_local,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
        "economics": {
            "state.get_constraints": state_get_constraints,
            "economics.calculate": economics_calculate,
            "economics.verify": economics_verify,
            "artifact.validate_local": artifact_validate_local,
            "economics.current": economics_current,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
        "review": {
            "review.run_rules": review_run_rules,
            "graph.get_subgraph": graph_get_subgraph,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
        "prototype": {
            "concept.generate": concept_generate,
            "sample_spec.draft": sample_spec_draft,
            "image.generate": image_generate,
            "image.get_manifest": image_get_manifest,
            "artifact.validate_local": artifact_validate_local,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
        "compliance": {
            "compliance.evaluate": compliance_evaluate,
            "knowledge.search": lambda args: {"citations": [], "trust_level": "UNTRUSTED_RETRIEVAL"},
            "artifact.validate_local": artifact_validate_local,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
        "leader": {
            "state.create_run": state_create_run,
            "state.get_project": state_get_project,
            "state.get_constraints": state_get_constraints,
            "context.build_bundle": context_build_bundle,
            "graph.get_subgraph": graph_get_subgraph,
            "artifact.list_current": artifact_list_current,
            "artifact.get_current": artifact_get_current,
        },
    }

    role_agent = {
        "market": "gap2sku-market", "supply": "gap2sku-supply",
        "economics": "gap2sku-economics", "review": "gap2sku-reviewer",
        "prototype": "gap2sku-prototype-designer", "compliance": "gap2sku-compliance",
        "leader": "gap2sku-product-architect",
    }

    shared_read = {
        "artifact.get": artifact_get_current,
        "artifact.list": artifact_list_current,
        "artifact.validate": artifact_validate_local,
    }
    for tool_map in role_tools.values():
        tool_map.update(shared_read)
    for role in ("market", "supply", "economics", "review"):
        role_tools[role].update({
            "task.get": task_get, "task.list": task_list, "task.advance": task_advance_for(role),
            "knowledge.search": knowledge_search, "knowledge.ingest": knowledge_ingest,
            "observability.trace": observability_trace_for(role),
        })
    role_tools["market"].update({"evidence.search": evidence_search, "evidence.get_source": evidence_get_source})
    role_tools["supply"].update({
        "evidence.get_source": evidence_get_source,
        "supplier.discover": supplier_discover,
        "rfq.import_response": rfq_import_response,
        "conflict.generate_options": conflict_generate_options,
        "review.run": review_run_rules,
    })
    role_tools["economics"]["decision.evaluate"] = decision_evaluate
    role_tools["review"].update({
        "artifact.subgraph": graph_get_subgraph, "replan.preview": replan_preview,
        "evidence.search": evidence_search, "evidence.get_source": evidence_get_source,
        "review.run": review_run_rules,
    })
    role_tools["prototype"].update({"sample_spec.lock": sample_spec_lock, "artifact.diff": artifact_diff})
    role_tools["compliance"].update({
        "compliance.classify": compliance_classify, "knowledge.search": knowledge_search,
    })
    role_tools["leader"].update({
        "task.create": task_create, "task.advance": task_advance_for("leader"),
        "artifact.subgraph": graph_get_subgraph, "replan.preview": replan_preview,
        "knowledge.search": knowledge_search, "knowledge.ingest": knowledge_ingest,
        "observability.trace": observability_trace_for("leader"),
    })

    def submitter(role: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def submit(args: dict[str, Any]) -> dict[str, Any]:
            summary = str(args.get("summary", "")).strip()
            artifact_refs = [str(item) for item in args.get("artifact_refs", []) if str(item)]
            data_mode = str(args.get("data_mode", "REAL")).upper()
            if not summary or not artifact_refs:
                return {"accepted": False, "error": "summary and artifact_refs are required"}
            if data_mode not in {"REAL", "SYNTHETIC", "MIXED"}:
                return {"accepted": False, "error": "data_mode must be REAL, SYNTHETIC, or MIXED"}
            collaboration = CollaborationStore(store.db_path)
            try:
                event = collaboration.append_event(CollaborationEvent(
                    event_id=f"evt-agentteams-{role}-{uuid.uuid4().hex}",
                    project_id=project_id,
                    task_id=str(args.get("task_id", f"{project_id}-{role}-advisory-r001")),
                    revision=max(1, int(args.get("revision", 1))),
                    event_type=str(args.get("event_type", "HANDOFF")),
                    sender=role_agent[role],
                    recipients=[str(item) for item in args.get("recipients", ["gap2sku-product-architect"])],
                    summary=summary,
                    artifact_refs=artifact_refs,
                    status=str(args.get("status", "submitted")),
                    data_mode=data_mode,
                    requested_action=str(args.get("requested_action", "review_handoff")),
                ))
                return {"accepted": True, "business_state_changed": False, "event": event.model_dump(mode="json")}
            finally:
                collaboration.close()

        return submit

    for role, tool_map in role_tools.items():
        tool_map["collaboration.submit_handoff"] = submitter(role)
    return role_tools


def create_app(fixture_dir: Path, store: ArtifactStore, include_official: bool = False) -> Starlette:
    tools = _build_tools(store, fixture_dir)
    routes: list[Any] = []
    session_managers: list[Any] = []

    if include_official:
        from mcp.server.fastmcp import FastMCP
        from mcp.server.transport_security import TransportSecuritySettings

        transport_security = TransportSecuritySettings(
            allowed_hosts=[
                "127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*",
                "host.docker.internal", "host.docker.internal:*",
            ],
        )

        def bind(handler: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def invoke(payload: dict[str, Any]) -> dict[str, Any]:
                return handler(payload)

            return invoke

        for role, tool_map in tools.items():
            role_mcp = FastMCP(
                f"Gap2SKU {role}",
                stateless_http=True,
                json_response=True,
                streamable_http_path="/mcp",
                transport_security=transport_security,
            )
            for tool_name, handler in tool_map.items():
                role_mcp.add_tool(bind(handler), name=tool_name)
            role_app = role_mcp.streamable_http_app()
            session_managers.append(role_mcp.session_manager)
            routes.append(Mount(f"/mcp/{role}", app=role_app))

    def make_handler(role: str, tool_map: dict) -> Callable:
        async def handler(request: Request) -> JSONResponse:
            body = await request.json()
            tool_name = body.get("tool") or body.get("name", "")
            args = body.get("args") or body.get("arguments", {})
            if tool_name not in tool_map:
                return JSONResponse({"ok": False, "error": f"tool {tool_name!r} not allowed for role {role!r}. allowed: {sorted(tool_map)}"}, status_code=403)
            try:
                result = tool_map[tool_name](args)
                return JSONResponse({"ok": True, "role": role, "tool": tool_name, "result": result})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return handler

    for role, tool_map in tools.items():
        routes.append(Route(f"/{role}/mcp", make_handler(role, tool_map), methods=["POST"]))

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "gap2sku-mcp", "roles": list(tools.keys())})

    async def list_tools(request: Request) -> JSONResponse:
        role = request.path_params["role"]
        return JSONResponse({"role": role, "tools": sorted(tools.get(role, {}))})

    async def agent_package(request: Request) -> Response:
        package_name = request.path_params["package_name"]
        allowed = {
            "leader.zip", "market.zip", "prototype.zip", "supply.zip",
            "economics.zip", "compliance.zip", "reviewer.zip",
        }
        if package_name not in allowed:
            return JSONResponse({"ok": False, "error": "agent package not found"}, status_code=404)
        package_path = Path(__file__).resolve().parents[2] / "packages" / package_name
        if not package_path.is_file():
            return JSONResponse({"ok": False, "error": "agent package unavailable"}, status_code=404)
        return FileResponse(package_path, media_type="application/zip", filename=package_name)

    routes.append(Route("/health", health, methods=["GET"]))
    routes.append(Route("/{role}/tools", list_tools, methods=["GET"]))
    routes.append(Route("/agent-packages/{package_name:str}", agent_package, methods=["GET"]))

    if include_official:
        from .mcp_official import create_mcp_server
        official = create_mcp_server(db_path=str(store.db_path))
        # Keep /{role}/mcp as the v0.1 JSON compatibility surface; /mcp is
        # the official SDK Streamable HTTP endpoint.
        official_app = official.streamable_http_app()
        session_managers.append(official.session_manager)
        routes.append(Mount("/", app=official_app))

    @asynccontextmanager
    async def lifespan(app: Starlette):  # type: ignore[no-untyped-def]
        async with AsyncExitStack() as stack:
            for manager in session_managers:
                await stack.enter_async_context(manager.run())
            yield

    return Starlette(routes=routes, lifespan=lifespan)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Gap2SKU MCP server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18090)
    parser.add_argument("--fixture", default="data/fixtures/laptop_stand")
    parser.add_argument("--db", default="shared/gap2sku.db")
    args = parser.parse_args()

    if not HAS_STARLETTE:
        print("[mcp] starlette/uvicorn not installed. Run: make bootstrap")
        return

    fixture_dir = Path(args.fixture)
    if not fixture_dir.exists():
        print(f"[mcp] fixture not found at {fixture_dir}, generating...")
        generate_fixture(fixture_dir)
    store = ArtifactStore(args.db)
    app = create_app(fixture_dir, store, include_official=True)
    print(f"[mcp] Gap2SKU MCP server on http://{args.host}:{args.port}")
    print("[mcp] Endpoints: /market/mcp /supply/mcp /economics/mcp /review/mcp /leader/mcp")
    print("[mcp] Health: GET /health")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
