from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .artifacts.store import ArtifactStore
from .collaboration.matrix import MatrixObserver
from .collaboration.models import CollaborationEvent, MatrixMessageRecord
from .collaboration.store import CollaborationStore
from .evidence.reviews import ReviewWorkbookImporter
from .governance.decision import DecisionEngine
from .governance.models import ApprovalRecord
from .observability.metrics import Metrics
from .product.workflow import CategoryRegistry
from .schemas.product import ProductIntake
from .story.service import ProductStoryService
from .tasking.store import TaskStore

try:
    import uvicorn as uvicorn_module
    from sse_starlette.sse import EventSourceResponse
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import FileResponse, JSONResponse
    from starlette.routing import Route
    from starlette.staticfiles import StaticFiles
    uvicorn: Any = uvicorn_module
except ImportError:  # pragma: no cover
    uvicorn = None


PROJECT_ID = "nap-pillow-cn-20260811-001"


def create_app(
    db_path: str = "shared/nap_pillow.db", source_dir: str = "private/raw_reviews",
    evidence_dir: str = "evidence/nap-pillow", static_dir: str = "web",
    project_overrides: Mapping[str, tuple[str, str]] | None = None,
) -> Any:
    if uvicorn is None:
        raise RuntimeError("starlette and uvicorn are required; run make bootstrap")
    review_mode = os.getenv("GAP2SKU_REVIEW_MODE", "").strip().lower() in {
        "1", "true", "yes", "on"
    }
    tasks, artifacts = TaskStore(db_path), ArtifactStore(db_path)
    collaboration = CollaborationStore(db_path)
    static = Path(static_dir)
    secondary_sources = {
        "desk-public": (
            "shared/desk_headphone_hanger_public.db",
            "evidence/new-category-public",
        ),
        "desk-synthetic": (
            "shared/desk_headphone_hanger_synthetic.db",
            "evidence/new-category-synthetic",
        ),
    }
    secondary_sources.update(project_overrides or {})
    project_catalog: dict[str, dict[str, Any]] = {
        "nap-pillow": {
            "project_id": PROJECT_ID,
            "project_name": "学生午睡枕改款 · 美国站",
            "short_name": "午睡枕真实证据",
            "entry_mode": "Existing SKU Upgrade",
            "data_mode": "REAL",
            "db_path": Path(db_path),
            "evidence_dir": Path(evidence_dir),
            "story_url": "/story?project=nap-pillow",
            "live_capable": True,
        },
        "desk-public": {
            "project_id": "desk-headphone-hanger-us-public-001",
            "project_name": "桌边耳机与线材挂架 · 公开信号",
            "short_name": "耳机挂架公开信号",
            "entry_mode": "New Concept",
            "data_mode": "PUBLIC_SIGNAL",
            "db_path": Path(secondary_sources["desk-public"][0]),
            "evidence_dir": Path(secondary_sources["desk-public"][1]),
            "story_url": "/story?project=desk-public",
            "live_capable": False,
        },
        "desk-synthetic": {
            "project_id": "desk-headphone-hanger-us-synthetic-001",
            "project_name": "桌边耳机与线材挂架 · 合成回归",
            "short_name": "耳机挂架合成 GO",
            "entry_mode": "New Concept",
            "data_mode": "SYNTHETIC",
            "db_path": Path(secondary_sources["desk-synthetic"][0]),
            "evidence_dir": Path(secondary_sources["desk-synthetic"][1]),
            "story_url": "/story?project=desk-synthetic",
            "live_capable": False,
        },
    }
    matrix: MatrixObserver | None = None
    matrix_task: asyncio.Task[None] | None = None
    matrix_sync_state: dict[str, Any] = {
        "connected": False,
        "last_success_epoch": None,
        "last_error_type": None,
        "messages_synced": 0,
    }
    matrix_homeserver = os.getenv("MATRIX_HOMESERVER", "").strip()
    matrix_room = os.getenv("MATRIX_ROOM_ID", "").strip()
    matrix_token = os.getenv("MATRIX_OBSERVER_ACCESS_TOKEN", "").strip()
    matrix_observer_user = os.getenv("MATRIX_OBSERVER_USER_ID", "@gap2sku-observer:local").strip()
    try:
        matrix_role_map = json.loads(os.getenv("MATRIX_ROLE_MAP_JSON", "{}"))
    except json.JSONDecodeError:
        matrix_role_map = {}
    if not review_mode and matrix_homeserver and matrix_room and matrix_token:
        matrix = MatrixObserver(
            matrix_homeserver, matrix_token, matrix_room, PROJECT_ID,
            role_by_matrix_id=matrix_role_map if isinstance(matrix_role_map, dict) else {},
            observer_user_id=matrix_observer_user,
        )

    def load_run() -> dict[str, Any]:
        path = Path(evidence_dir) / "run.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def artifact_payload(artifact_type: str) -> dict[str, Any] | None:
        rows = artifacts.list_by_type(artifact_type, PROJECT_ID)
        return rows[-1].payload if rows else None

    def selected_project(request: Request) -> tuple[str, dict[str, Any]] | None:
        key = request.query_params.get("project", "nap-pillow")
        config = project_catalog.get(key)
        return (key, config) if config else None

    def open_project_stores(
        key: str,
    ) -> tuple[TaskStore, ArtifactStore, CollaborationStore, bool]:
        if key == "nap-pillow":
            return tasks, artifacts, collaboration, False
        config = project_catalog[key]
        source_db = str(config["db_path"])
        return TaskStore(source_db), ArtifactStore(source_db), CollaborationStore(source_db), True

    def close_project_stores(
        source_tasks: TaskStore,
        source_artifacts: ArtifactStore,
        source_collaboration: CollaborationStore,
        owned: bool,
    ) -> None:
        if owned:
            source_collaboration.close()
            source_tasks.close()
            source_artifacts.close()

    def load_project_run(config: dict[str, Any]) -> dict[str, Any]:
        path = Path(config["evidence_dir"]) / "run.json"
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}

    def latest_project_payload(
        source_artifacts: ArtifactStore,
        project_id: str,
        artifact_type: str,
    ) -> dict[str, Any]:
        rows = source_artifacts.list_by_type(artifact_type, project_id)
        return rows[-1].payload if rows else {}

    def display_constraints(
        source_artifacts: ArtifactStore,
        project_id: str,
        run: dict[str, Any],
    ) -> dict[str, str]:
        intake = latest_project_payload(source_artifacts, project_id, "ProductIntake")
        economics = latest_project_payload(source_artifacts, project_id, "Economics")
        constraints = intake.get("hard_constraints", {})
        target = constraints.get("target_retail_cny") or economics.get("target_retail_cny")
        if project_id == PROJECT_ID:
            target = [99, 119]
        if isinstance(target, list) and len(target) >= 2:
            target_label = f"¥{target[0]}–{target[1]}"
        elif isinstance(target, (int, float)):
            target_label = f"¥{target:g}"
        else:
            target_label = "待确认"
        factory_cost = economics.get("factory_cost_cny")
        cost_label = f"¥{factory_cost:g}" if isinstance(factory_cost, (int, float)) else "待 RFQ"
        margin = constraints.get("target_contribution_margin", 0.4)
        margin_label = f"≥{round(float(margin) * 100)}%" if isinstance(margin, (int, float)) else "待确认"
        return {
            "target_price": target_label,
            "cost": cost_label,
            "target_margin": margin_label,
            "recommendation": str(run.get("recommendation", "—")),
        }

    async def index(request: Request) -> FileResponse:
        return FileResponse(static / "index.html")

    async def story_page(request: Request) -> FileResponse:
        return FileResponse(static / "story.html")

    async def guide_page(request: Request) -> FileResponse:
        return FileResponse(static / "guide.html")

    async def projects(request: Request) -> JSONResponse:
        rows = []
        for key, config in project_catalog.items():
            run = load_project_run(config)
            rows.append({
                "key": key,
                "project_id": config["project_id"],
                "project_name": config["project_name"],
                "short_name": config["short_name"],
                "entry_mode": config["entry_mode"],
                "data_mode": config["data_mode"],
                "recommendation": run.get("recommendation"),
                "story_url": config["story_url"],
                "available": Path(config["db_path"]).exists() and bool(run),
            })
        return JSONResponse({"projects": rows, "default_project": "nap-pillow"})

    async def project_view(request: Request) -> JSONResponse:
        selected = selected_project(request)
        if selected is None:
            return JSONResponse({"error": "unknown project"}, status_code=404)
        key, config = selected
        if not Path(config["db_path"]).exists():
            return JSONResponse(
                {"error": "project demo data is not generated; run the matching make target"},
                status_code=409,
            )
        source_tasks, source_artifacts, source_collaboration, owned = open_project_stores(key)
        try:
            project_id = str(config["project_id"])
            run = load_project_run(config)
            if key == "nap-pillow":
                status_response = await status(request)
                status_payload = json.loads(bytes(status_response.body))
            else:
                event_rows = source_collaboration.list_events(project_id, limit=200)
                completed_agents = {
                    event.sender for event in event_rows if event.sender.startswith("gap2sku-")
                }
                status_payload = {
                    "project_id": project_id,
                    "project_name": config["project_name"],
                    "run": run,
                    "category_profile": latest_project_payload(
                        source_artifacts, project_id, "CategoryProfile"
                    ),
                    "collaboration_mode": "LOCAL_REPLAY",
                    "matrix_connected": False,
                    "runtime_verified": False,
                    "end_to_end_verified": True,
                    "active_run_id": run.get("run_id") or project_id,
                    "active_run_started_at": None,
                    "active_run_progress": {
                        "completed": min(len(completed_agents), 7),
                        "total": 7,
                    },
                    "policy_version": (
                        latest_project_payload(source_artifacts, project_id, "DecisionPolicy").get(
                            "version"
                        )
                        or next(
                            (
                                artifact.policy_version
                                for artifact in source_artifacts.list_all(project_id)
                                if artifact.policy_version
                            ),
                            "policy-v3.0.0",
                        )
                    ),
                    "tasks": [
                        task.model_dump(mode="json") for task in source_tasks.list(project_id)
                    ],
                    "artifacts": [
                        artifact.model_dump(mode="json")
                        for artifact in source_artifacts.list_all(project_id)
                    ],
                    "story": latest_project_payload(
                        source_artifacts, project_id, "ProductStoryBundle"
                    ),
                    "agents": [
                        {"id": agent_id, "label": label, "status": "replay"}
                        for agent_id, label in [
                            ("gap2sku-product-architect", "Leader"),
                            ("gap2sku-market", "Market"),
                            ("gap2sku-prototype-designer", "Prototype Designer"),
                            ("gap2sku-supply", "Supply"),
                            ("gap2sku-economics", "Economics"),
                            ("gap2sku-compliance", "Compliance"),
                            ("gap2sku-reviewer", "Reviewer"),
                        ]
                    ],
                }
            status_payload.update({
                "project_key": key,
                "project_name": config["project_name"],
                "entry_mode": config["entry_mode"],
                "data_mode": config["data_mode"],
                "story_url": config["story_url"],
                "review_mode": review_mode,
                "read_only_replay": review_mode or key != "nap-pillow",
                "display_constraints": display_constraints(
                    source_artifacts, project_id, run
                ),
            })
            decision_types = [
                "DecisionBrief", "ReviewResult", "ProductSpec", "DecisionToSamplePack",
                "ProductConceptSet", "SampleSpec", "RFQPack", "ComplianceAssessment",
                "TestMatrix",
            ]
            decision_payload: dict[str, Any] = {}
            for artifact_type in decision_types:
                output_key = artifact_type[0].lower() + artifact_type[1:]
                decision_payload[output_key] = [
                    item.model_dump(mode="json")
                    for item in source_artifacts.list_by_type(artifact_type, project_id)
                ]
            trace_path = Path(config["evidence_dir"]) / "trace.jsonl"
            trace_rows = (
                [
                    json.loads(line)
                    for line in trace_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                if trace_path.exists()
                else []
            )
            return JSONResponse({
                "status": status_payload,
                "messages": [
                    row.model_dump(mode="json")
                    for row in source_collaboration.list_messages(project_id, limit=100)
                ],
                "events": [
                    row.model_dump(mode="json")
                    for row in source_collaboration.list_events(project_id, limit=200)
                ],
                "conflicts": [
                    row.model_dump(mode="json")
                    for row in source_artifacts.list_by_type("ConflictCard", project_id)
                ],
                "decision": decision_payload,
                "trace": {
                    "metrics": Metrics.from_trace(trace_path) if trace_path.exists() else {},
                    "events": trace_rows[-200:],
                },
            })
        finally:
            close_project_stores(
                source_tasks, source_artifacts, source_collaboration, owned
            )

    async def status(request: Request) -> JSONResponse:
        run = load_run()
        profile = artifact_payload("CategoryProfile") or {}
        story = artifact_payload("ProductStoryBundle") or {}
        runtime_path = Path("evidence/agentteams-runtime-verification.json")
        runtime_report: dict[str, Any] = {}
        if runtime_path.exists():
            try:
                loaded = json.loads(runtime_path.read_text(encoding="utf-8"))
                runtime_report = loaded if isinstance(loaded, dict) else {}
            except json.JSONDecodeError:
                runtime_report = {}
        runtime_verified = bool(
            runtime_report.get("runtime_verified", runtime_report.get("verified", False))
        )
        structured_handoffs = runtime_report.get("checks", {}).get("structured_handoffs", {})
        active_run_id = str(structured_handoffs.get("run_id", "")) or None
        active_run_completed = int(structured_handoffs.get("event_count", 0) or 0)
        live = bool(matrix and matrix_sync_state["connected"] and runtime_verified)
        worker_checks = runtime_report.get("checks", {}).get("workers", {}) if live else {}
        agent_specs = [
            ("gap2sku-product-architect", "Leader"), ("gap2sku-market", "Market"),
            ("gap2sku-prototype-designer", "Prototype Designer"), ("gap2sku-supply", "Supply"),
            ("gap2sku-economics", "Economics"), ("gap2sku-compliance", "Compliance"),
            ("gap2sku-reviewer", "Reviewer"),
        ]
        return JSONResponse({
            "project_id": PROJECT_ID, "project_name": "学生午睡枕改款 · 美国站",
            "run": run, "category_profile": profile,
            "collaboration_mode": "AGENTTEAMS_LIVE" if live else "LOCAL_REPLAY",
            "matrix_connected": bool(matrix_sync_state["connected"]),
            "matrix_sync": {
                "last_success_epoch": matrix_sync_state["last_success_epoch"],
                "last_error_type": matrix_sync_state["last_error_type"],
                "messages_synced": matrix_sync_state["messages_synced"],
            },
            "runtime_verified": runtime_verified,
            "end_to_end_verified": bool(runtime_report.get("end_to_end_verified", False)),
            "review_mode": review_mode,
            "active_run_id": active_run_id,
            "active_run_started_at": structured_handoffs.get("after"),
            "active_run_progress": {"completed": active_run_completed, "total": len(agent_specs)},
            "policy_version": (artifact_payload("DecisionPolicy") or {}).get("version", "policy-v3.0.0"),
            "tasks": [task.model_dump(mode="json") for task in tasks.list(PROJECT_ID)],
            "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts.list_all(PROJECT_ID)],
            "story": story,
            "agents": [{
                "id": agent_id, "label": label,
                "status": str(worker_checks.get(agent_id, {}).get("phase", "ready")).lower()
                if live else "replay",
            } for agent_id, label in agent_specs],
        })

    async def evidence(request: Request) -> JSONResponse:
        imported = ReviewWorkbookImporter(source_dir).import_all()
        query = request.query_params.get("q", "")
        brand = request.query_params.get("brand", "")
        rows = [record for record in imported.records if (
            not query or query in record.content_excerpt
        ) and (not brand or record.metadata.get("brand") == brand)]
        return JSONResponse({
            "report": imported.report,
            "records": [record.model_dump(mode="json") for record in rows[:100]],
        })

    async def conflicts(request: Request) -> JSONResponse:
        rows = artifacts.list_by_type("ConflictCard", PROJECT_ID)
        options = artifacts.list_by_type("OptionCard", PROJECT_ID)
        return JSONResponse({
            "conflicts": [row.model_dump(mode="json") for row in rows],
            "options": [row.model_dump(mode="json") for row in options],
        })

    async def decision(request: Request) -> JSONResponse:
        types = ["DecisionBrief", "ReviewResult", "ProductSpec", "DecisionToSamplePack",
                 "ProductConceptSet", "SampleSpec", "RFQPack", "ComplianceAssessment", "TestMatrix"]
        payload: dict[str, Any] = {}
        for artifact_type in types:
            key = artifact_type[0].lower() + artifact_type[1:]
            payload[key] = [item.model_dump(mode="json") for item in artifacts.list_by_type(artifact_type, PROJECT_ID)]
        return JSONResponse(payload)

    async def trace(request: Request) -> JSONResponse:
        path = Path(evidence_dir) / "trace.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
        return JSONResponse({"metrics": Metrics.from_trace(path), "events": rows[-200:]})

    async def collaboration_messages(request: Request) -> JSONResponse:
        before_value = request.query_params.get("before")
        before = int(before_value) if before_value else None
        limit = int(request.query_params.get("limit", "50"))
        rows = collaboration.list_messages(PROJECT_ID, before=before, limit=limit)
        return JSONResponse({"messages": [row.model_dump(mode="json") for row in rows]})

    async def send_message(request: Request) -> JSONResponse:
        if review_mode:
            return JSONResponse({"error": "审核快照为只读模式"}, status_code=403)
        body = await request.json()
        text = str(body.get("body", "")).strip()
        if not text:
            return JSONResponse({"error": "body is required"}, status_code=422)
        stamp = int(time.time() * 1000)
        forwarded = False
        if matrix:
            try:
                message = await asyncio.to_thread(matrix.send_text, text, f"gap2sku-{uuid.uuid4().hex}")
                message.origin_server_ts = stamp
                forwarded = True
            except Exception as exc:
                message = MatrixMessageRecord(
                    message_id=f"$web-{uuid.uuid4().hex}", room_id=matrix.room_id,
                    project_id=PROJECT_ID, sender_id="@human-manager:local", sender_role="human-manager",
                    body=text, origin_server_ts=stamp, data_mode="REAL",
                    raw_event={"source": "workbench", "forward_status": "MATRIX_FAILED", "error_type": type(exc).__name__},
                )
        else:
            message = MatrixMessageRecord(
                message_id=f"$web-{uuid.uuid4().hex}", room_id="!gap2sku-definition:local",
                project_id=PROJECT_ID, sender_id="@human-manager:local", sender_role="human-manager",
                body=text, origin_server_ts=stamp, data_mode="REAL",
                raw_event={"source": "workbench", "forward_status": "LOCAL_REPLAY_ONLY"},
            )
        message = collaboration.append_message(message)
        mentions = [token.removeprefix("@").lower() for token in text.split() if token.startswith("@")] or ["leader"]
        event = collaboration.append_event(CollaborationEvent(
            event_id=f"evt-web-{uuid.uuid4().hex}", project_id=PROJECT_ID,
            task_id=f"{PROJECT_ID}-user-request-r001", revision=1, event_type="USER_REQUEST",
            sender="human-manager", recipients=mentions, summary=text, status="suggested",
            data_mode="REAL", matrix_message_id=message.message_id,
            requested_action="create_suggested_task",
        ))
        return JSONResponse({
            "message": message.model_dump(mode="json"), "event": event.model_dump(mode="json"),
            "business_state_changed": False,
            "forwarded_to_matrix": forwarded,
            "notice": "消息已转发 Matrix" if forwarded else "消息保存在本地建议队列；配置 Matrix 后可真实转发",
        }, status_code=201)

    async def collaboration_events(request: Request) -> JSONResponse:
        limit = int(request.query_params.get("limit", "100"))
        rows = collaboration.list_events(PROJECT_ID, limit=limit)
        return JSONResponse({"events": [row.model_dump(mode="json") for row in rows]})

    async def collaboration_stream(request: Request) -> EventSourceResponse:
        async def generate() -> Any:
            # The normal JSON endpoint provides the initial snapshot. SSE only carries
            # events created after this connection, avoiding one refetch per old event.
            sent = {
                event.event_id for event in collaboration.list_events(PROJECT_ID, limit=500)
            }
            while True:
                if await request.is_disconnected():
                    break
                for event in collaboration.list_events(PROJECT_ID, limit=100):
                    if event.event_id in sent:
                        continue
                    sent.add(event.event_id)
                    yield {"event": "collaboration", "id": event.event_id,
                           "data": event.model_dump_json()}
                yield {"event": "heartbeat", "data": json.dumps({"ts": int(time.time())})}
                await asyncio.sleep(2)
        return EventSourceResponse(generate())

    async def create_revision(request: Request) -> JSONResponse:
        if review_mode:
            return JSONResponse({"error": "审核快照为只读模式"}, status_code=403)
        body = await request.json()
        task_id = str(body.get("task_id", ""))
        actor = str(body.get("actor", "human-manager"))
        reason = str(body.get("reason", "从历史产物创建新版本"))
        if not task_id or not tasks.get(task_id):
            return JSONResponse({"error": "task not found"}, status_code=404)
        revised = tasks.create_revision(task_id, actor, reason)
        return JSONResponse({
            "task": revised.model_dump(mode="json"),
            "history_mutated": False,
            "notice": "旧任务和 Artifact 保留；新 revision 已创建",
        }, status_code=201)

    async def story_data(request: Request) -> JSONResponse:
        view = request.query_params.get("view", "internal")
        project_key = request.query_params.get("project", "nap-pillow")
        story_sources = {
            "nap-pillow": (Path(db_path), PROJECT_ID),
            "desk-public": (
                Path("shared/desk_headphone_hanger_public.db"),
                "desk-headphone-hanger-us-public-001",
            ),
            "desk-synthetic": (
                Path("shared/desk_headphone_hanger_synthetic.db"),
                "desk-headphone-hanger-us-synthetic-001",
            ),
        }
        source = story_sources.get(project_key)
        if source is None:
            return JSONResponse({"error": "unknown Product Story project"}, status_code=404)
        source_db, source_project = source
        if source_project == PROJECT_ID:
            payload = artifact_payload("ProductStoryBundle")
        elif source_db.exists():
            story_store = ArtifactStore(source_db)
            try:
                rows = story_store.list_by_type("ProductStoryBundle", source_project)
                payload = rows[-1].payload if rows else None
            finally:
                story_store.close()
        else:
            payload = None
        if not payload:
            return JSONResponse(
                {"error": "Product Story not generated; run the matching demo target"},
                status_code=404,
            )
        try:
            from .schemas.product import ProductStoryBundle
            return JSONResponse(ProductStoryService.for_view(ProductStoryBundle(**payload), view))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    async def artifact_detail(request: Request) -> JSONResponse:
        artifact = artifacts.get(request.path_params["artifact_id"])
        if not artifact:
            return JSONResponse({"error": "artifact not found"}, status_code=404)
        return JSONResponse(artifact.model_dump(mode="json"))

    async def project_artifact_detail(request: Request) -> JSONResponse:
        selected = selected_project(request)
        if selected is None:
            return JSONResponse({"error": "unknown project"}, status_code=404)
        key, config = selected
        if not Path(config["db_path"]).exists():
            return JSONResponse({"error": "project data unavailable"}, status_code=409)
        source_tasks, source_artifacts, source_collaboration, owned = open_project_stores(key)
        try:
            artifact = source_artifacts.get(request.path_params["artifact_id"])
            if not artifact or artifact.project_id != config["project_id"]:
                return JSONResponse({"error": "artifact not found"}, status_code=404)
            return JSONResponse(artifact.model_dump(mode="json"))
        finally:
            close_project_stores(
                source_tasks, source_artifacts, source_collaboration, owned
            )

    async def send_project_message(request: Request) -> JSONResponse:
        if review_mode:
            return JSONResponse({"error": "审核快照为只读模式"}, status_code=403)
        selected = selected_project(request)
        if selected is None:
            return JSONResponse({"error": "unknown project"}, status_code=404)
        key, config = selected
        if not Path(config["db_path"]).exists():
            return JSONResponse({"error": "project data unavailable"}, status_code=409)
        body = await request.json()
        text = str(body.get("body", "")).strip()
        if not text:
            return JSONResponse({"error": "body is required"}, status_code=422)
        source_tasks, source_artifacts, source_collaboration, owned = open_project_stores(key)
        try:
            stamp = int(time.time() * 1000)
            forwarded = False
            project_id = str(config["project_id"])
            active_matrix = matrix if key == "nap-pillow" else None
            if active_matrix:
                try:
                    message = await asyncio.to_thread(
                        active_matrix.send_text, text, f"gap2sku-{uuid.uuid4().hex}"
                    )
                    message.origin_server_ts = stamp
                    forwarded = True
                except Exception as exc:
                    message = MatrixMessageRecord(
                        message_id=f"$web-{uuid.uuid4().hex}",
                        room_id=active_matrix.room_id,
                        project_id=project_id,
                        sender_id="@human-manager:local",
                        sender_role="human-manager",
                        body=text,
                        origin_server_ts=stamp,
                        data_mode=str(config["data_mode"]),
                        raw_event={
                            "source": "workbench",
                            "forward_status": "MATRIX_FAILED",
                            "error_type": type(exc).__name__,
                        },
                    )
            else:
                message = MatrixMessageRecord(
                    message_id=f"$web-{uuid.uuid4().hex}",
                    room_id="!gap2sku-project-replay:local",
                    project_id=project_id,
                    sender_id="@human-manager:local",
                    sender_role="human-manager",
                    body=text,
                    origin_server_ts=stamp,
                    data_mode=str(config["data_mode"]),
                    raw_event={
                        "source": "workbench",
                        "forward_status": "LOCAL_SUGGESTION_ONLY",
                    },
                )
            message = source_collaboration.append_message(message)
            mentions = [
                token.removeprefix("@").lower()
                for token in text.split()
                if token.startswith("@")
            ] or ["leader"]
            event = source_collaboration.append_event(CollaborationEvent(
                event_id=f"evt-web-{uuid.uuid4().hex}",
                project_id=project_id,
                task_id=f"{project_id}-user-request-r001",
                revision=1,
                event_type="USER_REQUEST",
                sender="human-manager",
                recipients=mentions,
                summary=text,
                status="suggested",
                data_mode=str(config["data_mode"]),
                matrix_message_id=message.message_id,
                requested_action="create_suggested_task",
            ))
            return JSONResponse({
                "message": message.model_dump(mode="json"),
                "event": event.model_dump(mode="json"),
                "business_state_changed": False,
                "forwarded_to_matrix": forwarded,
                "notice": (
                    "消息已转发 Matrix"
                    if forwarded
                    else "消息已保存为当前项目的建议任务；回放项目不会伪装成实时 AgentTeams"
                ),
            }, status_code=201)
        finally:
            close_project_stores(
                source_tasks, source_artifacts, source_collaboration, owned
            )

    async def intake_preview(request: Request) -> JSONResponse:
        if review_mode:
            return JSONResponse({"error": "审核快照不提供新品输入预览"}, status_code=403)
        try:
            intake = ProductIntake(**await request.json())
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        profile = CategoryRegistry.classify(intake)
        plan = CategoryRegistry.research_plan(intake, profile)
        return JSONResponse({
            "intake": intake.model_dump(mode="json"), "category_profile": profile.model_dump(mode="json"),
            "research_plan": plan.model_dump(mode="json"), "go_eligible": profile.go_eligible,
            "notice": "未知品类可继续研究，但 CategoryProfile 人工确认前禁止 GO",
        })

    async def approve(request: Request) -> JSONResponse:
        if review_mode:
            return JSONResponse({"error": "审核快照不提供人工审批写入"}, status_code=403)
        body = await request.json()
        reviews = artifacts.list_by_type("ReviewResult", PROJECT_ID)
        specs = artifacts.list_by_type("ProductSpec", PROJECT_ID)
        if not reviews or not specs:
            return JSONResponse({"error": "review/spec missing"}, status_code=409)
        review = reviews[-1].payload
        if review.get("review_result") != "PASS":
            return JSONResponse({"error": "Reviewer has not passed; approval cannot override deterministic gate"}, status_code=409)
        approval = ApprovalRecord(
            approval_id=f"approval-{uuid.uuid4().hex}", spec_hash=str(body.get("spec_hash", "")),
            policy_version=str(body.get("policy_version", "")), approver=str(body.get("approver", "")),
            reason=str(body.get("reason", "")), decision=str(body.get("decision", "APPROVE")),
        )
        expected_hash = str(specs[-1].payload.get("spec_hash", ""))
        if not DecisionEngine.approval_valid(approval, expected_hash, str(review.get("policy_version", ""))):
            return JSONResponse({"error": "approval does not match current spec/policy"}, status_code=409)
        return JSONResponse({"approval": approval.model_dump(mode="json"), "accepted": True})

    async def sync_matrix_once() -> None:
        if not matrix:
            return
        rows, _ = await asyncio.to_thread(matrix.messages, limit=100)
        for row in rows:
            collaboration.append_message(row)
        matrix_sync_state["connected"] = True
        matrix_sync_state["last_success_epoch"] = int(time.time())
        matrix_sync_state["last_error_type"] = None
        matrix_sync_state["messages_synced"] = len(rows)

    async def poll_matrix() -> None:
        while True:
            try:
                await sync_matrix_once()
            except Exception as exc:
                # The page exposes a disconnected state through its own SSE retry.
                # Tokens and remote error bodies are deliberately not logged.
                matrix_sync_state["connected"] = False
                matrix_sync_state["last_error_type"] = type(exc).__name__
            await asyncio.sleep(2)

    async def startup() -> None:
        nonlocal matrix_task
        try:
            await sync_matrix_once()
        except Exception as exc:
            matrix_sync_state["connected"] = False
            matrix_sync_state["last_error_type"] = type(exc).__name__
        if matrix:
            matrix_task = asyncio.create_task(poll_matrix())

    async def shutdown() -> None:
        if matrix_task:
            matrix_task.cancel()
            try:
                await matrix_task
            except asyncio.CancelledError:
                pass
        collaboration.close()
        tasks.close()
        artifacts.close()

    routes = [
        Route("/", index), Route("/story", story_page), Route("/guide", guide_page),
        Route("/api/projects", projects), Route("/api/project-view", project_view),
        Route("/api/status", status), Route("/api/evidence", evidence),
        Route("/api/conflicts", conflicts), Route("/api/decision", decision),
        Route("/api/trace", trace), Route("/api/collaboration/messages", collaboration_messages),
        Route("/api/collaboration/messages", send_message, methods=["POST"]),
        Route("/api/collaboration/events", collaboration_events),
        Route("/api/collaboration/stream", collaboration_stream),
        Route("/api/collaboration/revision", create_revision, methods=["POST"]),
        Route("/api/story", story_data), Route("/api/artifacts/{artifact_id}", artifact_detail),
        Route(
            "/api/project-artifacts/{artifact_id}",
            project_artifact_detail,
        ),
        Route("/api/project-messages", send_project_message, methods=["POST"]),
        Route("/api/intake/preview", intake_preview, methods=["POST"]),
        Route("/api/decision/approve", approve, methods=["POST"]),
    ]
    app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])
    app.mount("/static", StaticFiles(directory=static), name="static")
    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db", default="shared/nap_pillow.db")
    args = parser.parse_args()
    if uvicorn is None:
        raise SystemExit("starlette/uvicorn not installed; run make bootstrap")
    uvicorn.run(create_app(args.db), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
