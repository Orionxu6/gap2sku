from __future__ import annotations

from gap2sku.nap_pillow import NapPillowPipeline


def test_real_pipeline_revises(tmp_path) -> None:
    result = NapPillowPipeline(
        "private/raw_reviews", tmp_path / "real.db", tmp_path / "real-evidence"
    ).run()
    assert result["recommendation"] == "REVISE"
    assert result["review_result"] == "REVISE"
    assert result["evidence_count"] == 389
    assert result["conflicts"] == 4
    assert len(result["revision_tasks"]) == 4


def test_synthetic_pipeline_is_labelled(tmp_path) -> None:
    result = NapPillowPipeline(
        "private/raw_reviews", tmp_path / "synth.db", tmp_path / "synth-evidence",
        synthetic_supply=True,
    ).run()
    assert result["recommendation"] == "GO"
    assert result["data_mode"] == "SYNTHETIC"
    assert result["review_result"] == "PASS"
