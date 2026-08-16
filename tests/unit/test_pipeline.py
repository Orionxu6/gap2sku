"""Integration test for Domain Core pipeline (spec 27.1)."""
from pathlib import Path

import pytest

from gap2sku.fixtures.generate import generate_fixture
from gap2sku.pipeline import DomainCorePipeline


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("fixture")
    generate_fixture(d, seed=42)
    return d


def test_pipeline_produces_spec_and_review(fixture_dir, tmp_path):
    db = tmp_path / "test.db"
    from gap2sku.artifacts.store import ArtifactStore
    store = ArtifactStore(str(db))
    pipeline = DomainCorePipeline(fixture_dir, store)
    result = pipeline.run()

    assert result["project_id"] == "laptop-stand-us-20260803-001"
    assert result["artifact_count"] >= 8
    assert result["spec"]["spec_id"] == "product-spec-v1"
    assert result["review"]["decision"] in ("PASS", "REVISE", "BLOCK")


def test_pipeline_carbon_fiber_rejected(fixture_dir, tmp_path):
    from gap2sku.artifacts.store import ArtifactStore
    store = ArtifactStore(str(tmp_path / "test.db"))
    pipeline = DomainCorePipeline(fixture_dir, store)
    pipeline.run()
    carbon = [a for a in pipeline.artifacts
              if a.artifact_type.value == "FeatureDecision"
              and a.payload.get("feature_id") == "carbon_fiber_structure"]
    assert len(carbon) == 1
    assert carbon[0].payload["status"] == "REJECT"


def test_pipeline_has_full_evidence_chain_for_accept(fixture_dir, tmp_path):
    from gap2sku.artifacts.store import ArtifactStore
    store = ArtifactStore(str(tmp_path / "test.db"))
    pipeline = DomainCorePipeline(fixture_dir, store)
    pipeline.run()
    accepted = [a for a in pipeline.artifacts
                if a.artifact_type.value == "FeatureDecision"
                and a.payload.get("status") == "ACCEPT"]
    assert len(accepted) >= 2  # spec 16.2: at least 2 accepted
    for d in accepted:
        assert d.payload.get("market_refs")
        assert d.payload.get("supply_refs")
        assert d.payload.get("economics_refs")
