from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .artifacts.store import ArtifactStore
from .evidence.reviews import ReviewWorkbookImporter
from .governance.decision import DecisionEngine
from .governance.models import DecisionPolicy, EvidenceState, ReviewReport
from .imaging.providers import ImageGenerationError, OfflineImageProvider, QwenImageProvider
from .knowledge.retriever import SQLiteKnowledgeRetriever
from .observability.metrics import Metrics
from .product.workflow import CategoryRegistry, ProductWorkflow
from .schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from .schemas.product import (
    ProductIntake,
    ProductStoryBundle,
    PublicSupplierSignal,
    PublicSupplierSignalSet,
    RenderPromptRecord,
    SampleSpec,
    SupplierQuoteSet,
)
from .story.service import ProductStoryService
from .tasking.models import TaskContract, TaskState
from .tasking.store import TaskStore


def create_mcp_server(
    db_path: str = "shared/nap_pillow.db",
    source_dir: str = "private/raw_reviews",
    evidence_dir: str = "evidence/nap-pillow",
    host: str = "127.0.0.1",
    port: int = 18090,
) -> Any:
    """Build the official MCP SDK server. Import is delayed for offline core runs."""
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.server.transport_security import TransportSecuritySettings
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("official mcp package is required; run make bootstrap") from exc

    mcp = FastMCP(
        "Gap2SKU v3", stateless_http=True, json_response=True,
        host=host, port=port, streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(
            allowed_hosts=[
                "127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*",
                "host.docker.internal", "host.docker.internal:*",
            ],
        ),
    )
    tasks = TaskStore(db_path)
    artifacts = ArtifactStore(db_path)
    knowledge = SQLiteKnowledgeRetriever(Path(db_path).with_name("knowledge.db"))
    workflow = ProductWorkflow("nap-pillow-cn-20260811-001")

    @mcp.tool(name="task.create")
    def task_create(payload: dict[str, Any]) -> dict[str, Any]:
        return tasks.create(TaskContract(**payload)).model_dump(mode="json")

    @mcp.tool(name="task.get")
    def task_get(task_id: str) -> dict[str, Any] | None:
        task = tasks.get(task_id)
        return task.model_dump(mode="json") if task else None

    @mcp.tool(name="task.list")
    def task_list(project_id: str) -> list[dict[str, Any]]:
        return [task.model_dump(mode="json") for task in tasks.list(project_id)]

    @mcp.tool(name="task.advance")
    def task_advance(task_id: str, state: str, actor: str, reason: str) -> dict[str, Any]:
        return tasks.advance(task_id, TaskState(state), actor, reason).model_dump(mode="json")

    @mcp.tool(name="task.events")
    def task_events(task_id: str) -> list[dict[str, Any]]:
        return [event.model_dump(mode="json") for event in tasks.events(task_id)]

    @mcp.tool(name="artifact.get")
    def artifact_get(artifact_id: str, version: int | None = None) -> dict[str, Any] | None:
        artifact = artifacts.get(artifact_id, version)
        return artifact.model_dump(mode="json") if artifact else None

    @mcp.tool(name="artifact.list")
    def artifact_list(project_id: str) -> list[dict[str, Any]]:
        return [artifact.model_dump(mode="json") for artifact in artifacts.list_all(project_id)]

    @mcp.tool(name="artifact.validate")
    def artifact_validate(artifact_id: str) -> dict[str, Any]:
        artifact = artifacts.get(artifact_id)
        if not artifact:
            return {"valid": False, "errors": ["not found"]}
        missing = [ref for ref in artifact.input_refs if artifacts.get(ref) is None]
        return {"valid": not missing, "errors": [f"missing ref {ref}" for ref in missing]}

    @mcp.tool(name="artifact.subgraph")
    def artifact_subgraph(artifact_id: str) -> dict[str, Any]:
        return {"from": artifacts.edges_from(artifact_id), "to": artifacts.edges_to(artifact_id)}

    @mcp.tool(name="artifact.diff")
    def artifact_diff(artifact_id: str, left_version: int, right_version: int) -> dict[str, Any]:
        left, right = artifacts.get(artifact_id, left_version), artifacts.get(artifact_id, right_version)
        if not left or not right:
            return {"error": "version not found"}
        keys = sorted(set(left.payload) | set(right.payload))
        return {"changes": {key: {"left": left.payload.get(key), "right": right.payload.get(key)} for key in keys if left.payload.get(key) != right.payload.get(key)}}

    @mcp.tool(name="evidence.import_reviews")
    def evidence_import_reviews() -> dict[str, Any]:
        return ReviewWorkbookImporter(source_dir).import_all().report

    @mcp.tool(name="evidence.search")
    def evidence_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
        result = ReviewWorkbookImporter(source_dir).import_all().records
        return [record.model_dump(mode="json") for record in result if query in record.content_excerpt][:limit]

    @mcp.tool(name="evidence.get_source")
    def evidence_get_source(evidence_id: str) -> dict[str, Any] | None:
        result = ReviewWorkbookImporter(source_dir).import_all().records
        record = next((item for item in result if item.evidence_id == evidence_id), None)
        return record.model_dump(mode="json") if record else None

    @mcp.tool(name="supplier.discover")
    def supplier_discover(category: str) -> dict[str, Any]:
        """Return captured public signals, explicitly outside the quote evidence class."""
        normalized = category.lower()
        if not any(token in normalized for token in ("headphone", "headset", "耳机", "desk")):
            return {
                "signal_set": None,
                "notice": "no built-in replay snapshot for this category; use an authorized connector or user export",
            }
        source = Path("data/public_signals/desk_headphone_hanger.json")
        snapshot = json.loads(source.read_text(encoding="utf-8"))
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
        signal_set = PublicSupplierSignalSet(
            signal_set_id=snapshot["snapshot_id"],
            project_id="desk-headphone-hanger-us-public-001",
            signals=signals,
        )
        return {
            "signal_set": signal_set.model_dump(mode="json"),
            "notice": "PUBLIC_LISTING_SIGNAL only; shortlist/RFQ target, never verified cost",
        }

    @mcp.tool(name="conflict.list")
    def conflict_list(project_id: str) -> list[dict[str, Any]]:
        return [a.model_dump(mode="json") for a in artifacts.list_by_type("ConflictCard", project_id)]

    @mcp.tool(name="conflict.generate_options")
    def conflict_generate_options(conflict_id: str) -> dict[str, Any]:
        return {"conflict_id": conflict_id, "allowed": False, "reason": "Options are versioned artifacts; run the decision pipeline or create a revision task"}

    @mcp.tool(name="decision.evaluate")
    def decision_evaluate(review_payload: dict[str, Any], data_mode: str = "REAL") -> dict[str, Any]:
        report = ReviewReport(**review_payload)
        state = EvidenceState.CONFIRMED if data_mode == "SYNTHETIC" else EvidenceState.MISSING
        return DecisionEngine.evaluate(
            project_id="nap-pillow-cn-20260811-001", policy=DecisionPolicy(), review=report,
            supplier_quote=state, bom=state, durability_test=state, material_test=state,
            conflict_refs=[], option_refs=[], data_mode=data_mode,
        ).model_dump(mode="json")

    @mcp.tool(name="review.get_findings")
    def review_get_findings(project_id: str) -> list[dict[str, Any]]:
        return [a.payload for a in artifacts.list_by_type("ReviewResult", project_id)]

    @mcp.tool(name="observability.metrics")
    def observability_metrics() -> dict[str, Any]:
        return Metrics.from_trace(Path(evidence_dir) / "trace.jsonl")

    @mcp.tool(name="knowledge.ingest")
    def knowledge_ingest(title: str, source_uri: str, body: str) -> dict[str, Any]:
        return {"citation_id": knowledge.ingest(title, source_uri, body), "trust_level": "UNTRUSTED_RETRIEVAL"}

    @mcp.tool(name="knowledge.search")
    def knowledge_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
        return [citation.model_dump(mode="json") for citation in knowledge.search(query, limit)]

    @mcp.tool(name="project.intake")
    def project_intake(payload: dict[str, Any]) -> dict[str, Any]:
        intake = ProductIntake(**payload)
        profile = CategoryRegistry.classify(intake)
        research = CategoryRegistry.research_plan(intake, profile)
        return {
            "intake": intake.model_dump(mode="json"),
            "category_profile": profile.model_dump(mode="json"),
            "research_plan": research.model_dump(mode="json"),
            "go_eligible": profile.go_eligible,
        }

    @mcp.tool(name="category.classify")
    def category_classify(payload: dict[str, Any]) -> dict[str, Any]:
        return CategoryRegistry.classify(ProductIntake(**payload)).model_dump(mode="json")

    @mcp.tool(name="category.confirm")
    def category_confirm(payload: dict[str, Any], actor: str) -> dict[str, Any]:
        if actor != "human-manager":
            return {"confirmed": False, "error": "only human-manager may confirm a category profile"}
        confirmed = dict(payload)
        confirmed["status"] = "CONFIRMED"
        confirmed["confirmed_by"] = actor
        return {"confirmed": True, "category_profile": confirmed}

    @mcp.tool(name="concept.generate")
    def concept_generate(pain_point_refs: list[str]) -> dict[str, Any]:
        return workflow.concepts(pain_point_refs).model_dump(mode="json")

    @mcp.tool(name="sample_spec.lock")
    def sample_spec_lock(payload: dict[str, Any], actor: str) -> dict[str, Any]:
        if actor != "human-manager":
            return {"locked": False, "error": "only human-manager may lock SampleSpec"}
        data = dict(payload)
        data["lock_status"] = "LOCKED"
        data["locked_by"] = actor
        data.pop("spec_hash", None)
        spec = SampleSpec(**data)
        return {"locked": True, "sample_spec": spec.model_dump(mode="json")}

    @mcp.tool(name="image.get_manifest")
    def image_get_manifest(render_id: str) -> dict[str, Any] | None:
        rows = artifacts.list_by_type("RenderManifest", "nap-pillow-cn-20260811-001")
        match = next((row for row in rows if row.payload.get("render_id") == render_id), None)
        return match.payload if match else None

    @mcp.tool(name="image.generate")
    def image_generate(payload: dict[str, Any], provider: str = "offline") -> dict[str, Any]:
        record = RenderPromptRecord(**payload)
        try:
            adapter = QwenImageProvider() if provider == "qwen" else OfflineImageProvider()
            return adapter.generate(record).model_dump(mode="json")
        except ImageGenerationError as exc:
            if provider != "qwen":
                return {"error": str(exc), "event_type": "MODEL_DEGRADED"}
            try:
                fallback = OfflineImageProvider().generate(record).model_dump(mode="json")
            except ImageGenerationError as fallback_exc:
                return {
                    "error": "online and replay image providers failed",
                    "provider_error": str(exc), "fallback_error": str(fallback_exc),
                    "event_type": "MODEL_DEGRADED",
                }
            return {
                "manifest": fallback, "event_type": "MODEL_DEGRADED",
                "provider_error": str(exc), "fallback": "offline-replay",
            }

    @mcp.tool(name="rfq.build")
    def rfq_build(project_id: str) -> dict[str, Any] | None:
        rows = artifacts.list_by_type("RFQPack", project_id)
        return rows[-1].payload if rows else None

    @mcp.tool(name="rfq.import_response")
    def rfq_import_response(
        payload: dict[str, Any], task_id: str, actor: str
    ) -> dict[str, Any]:
        """Import a user-provided supplier response bound to the locked RFQ/spec hash."""
        task = tasks.get(task_id)
        if not task or task.owner != "gap2sku-supply":
            return {"accepted": False, "error": "active Supply task required"}
        if actor not in {"gap2sku-supply", "human-manager"}:
            return {"accepted": False, "error": "actor is not authorized to import supplier evidence"}
        quote_set = SupplierQuoteSet(**payload)
        if quote_set.project_id != task.project_id:
            return {"accepted": False, "error": "project does not match Supply task"}
        rfq = artifacts.get(quote_set.rfq_ref)
        if not rfq or rfq.artifact_type != ArtifactType.RFQ_PACK:
            return {"accepted": False, "error": "referenced RFQ artifact not found"}
        if rfq.payload.get("sample_spec_hash") != quote_set.sample_spec_hash:
            return {"accepted": False, "error": "supplier response is not bound to current spec hash"}
        if not quote_set.source_document_hash.startswith("sha256:"):
            return {"accepted": False, "error": "source document SHA-256 is required"}
        invalid = [
            quote.quote_id
            for quote in quote_set.quotes
            if quote.data_mode != "REAL" or quote.verification_level != "SUPPLIER_RESPONSE"
        ]
        if invalid:
            return {
                "accepted": False,
                "error": "only explicit REAL supplier responses may enter SupplierQuoteSet",
                "invalid_quote_ids": invalid,
            }
        body = quote_set.model_dump(mode="json")
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        envelope = ArtifactEnvelope(
            artifact_id=quote_set.quote_set_id,
            artifact_type=ArtifactType.SUPPLIER_QUOTE_SET,
            artifact_version=1,
            project_id=quote_set.project_id,
            producer_agent="gap2sku-supply",
            producer_task_id=task_id,
            status=ArtifactStatus.VALID,
            input_refs=[quote_set.rfq_ref],
            content_hash="sha256:" + hashlib.sha256(encoded).hexdigest(),
            data_mode="REAL",
            payload=body,
        )
        committed = artifacts.commit(
            envelope,
            artifacts.project_revision(quote_set.project_id),
            f"rfq-import:{quote_set.quote_set_id}:{quote_set.source_document_hash}",
        )
        return {
            "accepted": True,
            "artifact": committed.model_dump(mode="json"),
            "notice": "quote imported; sample and factory capability remain separate evidence gates",
        }

    @mcp.tool(name="compliance.evaluate")
    def compliance_evaluate(project_id: str) -> dict[str, Any] | None:
        rows = artifacts.list_by_type("ComplianceAssessment", project_id)
        return rows[-1].payload if rows else None

    @mcp.tool(name="story.render")
    def story_render(project_id: str, view: str = "internal") -> dict[str, Any] | None:
        rows = artifacts.list_by_type("ProductStoryBundle", project_id)
        if not rows:
            return None
        return ProductStoryService.for_view(ProductStoryBundle(**rows[-1].payload), view)

    return mcp
