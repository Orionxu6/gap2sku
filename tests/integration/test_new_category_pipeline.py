from __future__ import annotations

from gap2sku.artifacts.store import ArtifactStore
from gap2sku.new_category import PUBLIC_PROJECT_ID, SYNTHETIC_PROJECT_ID, NewCategoryPipeline


def test_public_signal_path_is_revise_and_does_not_invent_quote(tmp_path) -> None:
    db = tmp_path / "public.db"
    result = NewCategoryPipeline(
        synthetic=False,
        db_path=db,
        output_dir=tmp_path / "public-evidence",
    ).run()
    assert result["project_id"] == PUBLIC_PROJECT_ID
    assert result["recommendation"] == "REVISE"
    assert result["public_supplier_signal_count"] == 3
    assert result["public_signals_used_as_quote"] is False
    assert result["matched_spec_quote_state"] == "MISSING"
    assert result["verified_profit"] is None
    assert result["concept_count"] == 3
    assert result["task_count"] == 8

    store = ArtifactStore(db)
    signals = store.list_by_type("PublicSupplierSignalSet", PUBLIC_PROJECT_ID)
    assert signals[0].payload["quote_state"] == "MISSING"
    assert all(
        row["evidence_class"] == "PUBLIC_LISTING_SIGNAL"
        for row in signals[0].payload["signals"]
    )
    store.close()


def test_synthetic_path_reaches_go_with_exact_bound_approval(tmp_path) -> None:
    db = tmp_path / "synthetic.db"
    result = NewCategoryPipeline(
        synthetic=True,
        db_path=db,
        output_dir=tmp_path / "synthetic-evidence",
    ).run()
    assert result["project_id"] == SYNTHETIC_PROJECT_ID
    assert result["recommendation"] == "GO"
    assert result["data_mode"] == "SYNTHETIC"
    assert result["approval_ref"] == "desk-synthetic-approval-v1"
    assert result["verified_profit"]["status"] == "CONFIRMED_SYNTHETIC"

    store = ArtifactStore(db)
    approval = store.get("desk-synthetic-approval-v1")
    assert approval is not None
    assert approval.payload["spec_hash"] == result["product_spec_hash"]
    assert approval.data_mode == "SYNTHETIC"
    store.close()
