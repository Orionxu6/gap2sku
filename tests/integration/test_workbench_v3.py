from __future__ import annotations

from starlette.testclient import TestClient

from gap2sku.nap_pillow import NapPillowPipeline
from gap2sku.new_category import NewCategoryPipeline
from gap2sku.workbench import create_app


def test_workbench_pages_and_apis(tmp_path) -> None:
    db = tmp_path / "nap.db"
    evidence = tmp_path / "evidence"
    public_db = tmp_path / "desk-public.db"
    public_evidence = tmp_path / "desk-public-evidence"
    synthetic_db = tmp_path / "desk-synthetic.db"
    synthetic_evidence = tmp_path / "desk-synthetic-evidence"
    NapPillowPipeline("private/raw_reviews", db, evidence).run()
    NewCategoryPipeline(
        synthetic=False, db_path=public_db, output_dir=public_evidence
    ).run()
    NewCategoryPipeline(
        synthetic=True, db_path=synthetic_db, output_dir=synthetic_evidence
    ).run()
    project_overrides = {
        "desk-public": (str(public_db), str(public_evidence)),
        "desk-synthetic": (str(synthetic_db), str(synthetic_evidence)),
    }
    with TestClient(create_app(
        str(db), "private/raw_reviews", str(evidence), "web", project_overrides
    )) as client:
        assert client.get("/").status_code == 200
        assert client.get("/story").status_code == 200
        assert client.get("/guide").status_code == 200
        for endpoint in (
            "/api/status", "/api/evidence", "/api/conflicts", "/api/decision", "/api/trace",
            "/api/collaboration/messages", "/api/collaboration/events", "/api/story?view=internal",
            "/api/story?view=supplier", "/api/story?view=judge",
        ):
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.json()
        status = client.get("/api/status").json()
        assert status["collaboration_mode"] == "LOCAL_REPLAY"
        assert status["matrix_connected"] is False
        assert status["active_run_progress"]["total"] == 7
        assert {agent["status"] for agent in status["agents"]} == {"replay"}
        catalog = client.get("/api/projects").json()
        assert {project["key"] for project in catalog["projects"]} == {
            "nap-pillow", "desk-public", "desk-synthetic",
        }
        assert all(project["available"] for project in catalog["projects"])
        public_view = client.get("/api/project-view?project=desk-public")
        assert public_view.status_code == 200
        assert public_view.json()["status"]["run"]["recommendation"] == "REVISE"
        assert public_view.json()["status"]["read_only_replay"] is True
        synthetic_view = client.get("/api/project-view?project=desk-synthetic")
        assert synthetic_view.status_code == 200
        assert synthetic_view.json()["status"]["run"]["recommendation"] == "GO"
        assert synthetic_view.json()["status"]["data_mode"] == "SYNTHETIC"
        desk_artifact = synthetic_view.json()["status"]["artifacts"][0]["artifact_id"]
        assert client.get(
            f"/api/project-artifacts/{desk_artifact}?project=desk-synthetic"
        ).status_code == 200
        desk_message = client.post(
            "/api/project-messages?project=desk-public",
            json={"body": "@Supply 请补充真实 RFQ"},
        )
        assert desk_message.status_code == 201
        assert desk_message.json()["business_state_changed"] is False
        assert desk_message.json()["forwarded_to_matrix"] is False
        sent = client.post("/api/collaboration/messages", json={"body": "@Leader 请建立建议任务"})
        assert sent.status_code == 201
        assert sent.json()["business_state_changed"] is False
        assert sent.json()["forwarded_to_matrix"] is False
        assert client.post("/api/decision/approve", json={}).status_code == 409
        unknown = client.post("/api/intake/preview", json={
            "project_id": "generic-001", "mode": "NEW_CONCEPT", "title": "新概念",
            "target_market": "US", "target_users": ["adult"], "category_hint": "unknown device",
            "idea_or_problem": "validate", "hard_constraints": {},
        })
        assert unknown.status_code == 200
        assert unknown.json()["go_eligible"] is False
        assert unknown.json()["category_profile"]["status"] == "DRAFT"
