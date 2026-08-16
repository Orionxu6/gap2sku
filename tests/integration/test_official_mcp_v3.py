from __future__ import annotations

import hashlib
import json

from gap2sku.artifacts.store import ArtifactStore
from gap2sku.mcp_official import create_mcp_server
from gap2sku.schemas.envelope import ArtifactEnvelope, ArtifactType


def test_official_mcp_tool_surface(tmp_path) -> None:
    server = create_mcp_server(str(tmp_path / "mcp.db"), "private/raw_reviews", str(tmp_path))
    tools = set(server._tool_manager._tools)
    assert {
        "task.create", "artifact.get", "evidence.import_reviews", "decision.evaluate", "knowledge.search",
        "project.intake", "category.classify", "concept.generate", "sample_spec.lock", "image.generate",
        "supplier.discover", "rfq.build", "rfq.import_response", "compliance.evaluate",
        "story.render",
    } <= tools
    app = server.streamable_http_app()
    assert app is not None


def test_official_supplier_signal_and_quote_import_boundaries(tmp_path) -> None:
    db = tmp_path / "supplier.db"
    server = create_mcp_server(str(db), "private/raw_reviews", str(tmp_path))
    tools = server._tool_manager._tools

    discover = tools["supplier.discover"].fn
    result = discover("foldable headphone hanger")
    assert result["signal_set"]["quote_state"] == "MISSING"
    assert all(
        item["evidence_class"] == "PUBLIC_LISTING_SIGNAL"
        for item in result["signal_set"]["signals"]
    )
    assert discover("unmapped appliance")["signal_set"] is None

    tools["task.create"].fn(
        {
            "task_id": "supply-r001",
            "project_id": "p",
            "owner": "gap2sku-supply",
            "idempotency_key": "p:supply:1",
        }
    )
    sample_hash = "sha256:locked-sample"
    rfq_payload = {"sample_spec_hash": sample_hash}
    store = ArtifactStore(db)
    store.commit(
        ArtifactEnvelope(
            artifact_id="rfq-v1",
            artifact_type=ArtifactType.RFQ_PACK,
            artifact_version=1,
            project_id="p",
            producer_agent="gap2sku-supply",
            producer_task_id="supply-r001",
            content_hash="sha256:" + hashlib.sha256(json.dumps(rfq_payload).encode()).hexdigest(),
            payload=rfq_payload,
        ),
        store.project_revision("p"),
        "rfq-v1",
    )
    store.close()
    payload = {
        "quote_set_id": "quotes-v1",
        "project_id": "p",
        "rfq_ref": "rfq-v1",
        "sample_spec_hash": sample_hash,
        "received_at": "2026-08-15T00:00:00Z",
        "source_document_hash": "sha256:document",
        "quotes": [
            {
                "quote_id": "quote-1",
                "supplier_name": "Example Factory",
                "source_ref": "sha256:document",
                "verification_level": "SUPPLIER_RESPONSE",
                "amount": "3.20",
                "currency": "USD",
                "moq": 500,
                "lead_days": 30,
                "data_mode": "REAL",
            }
        ],
        "comparison_status": "SINGLE_QUOTE_ONLY",
    }
    importer = tools["rfq.import_response"].fn
    accepted = importer(payload, "supply-r001", "human-manager")
    assert accepted["accepted"] is True
    assert importer(payload, "missing-task", "human-manager")["accepted"] is False
