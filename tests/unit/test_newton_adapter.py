from __future__ import annotations

import json

import pytest

from gap2sku.integrations.newton import NewtonExportAdapter, NewtonExportError


def test_newton_export_remains_non_quote_signal(tmp_path) -> None:
    export = tmp_path / "newton.json"
    export.write_text(
        json.dumps(
            {
                "exported_at": "2026-08-15T00:00:00Z",
                "items": [
                    {
                        "supplier_name": "Example",
                        "source_url": "https://detail.1688.com/example",
                        "observed_facts": {"displayed_moq": 500},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = NewtonExportAdapter.ingest(export, "project-1")
    assert result.quote_state == "MISSING"
    assert result.signals[0].evidence_class == "PUBLIC_LISTING_SIGNAL"
    assert result.signals[0].verification_level == "AUTHORIZED_PLATFORM_EXPORT"


def test_newton_export_rejects_session_material(tmp_path) -> None:
    export = tmp_path / "bad.json"
    export.write_text(
        json.dumps(
            {
                "exported_at": "2026-08-15T00:00:00Z",
                "cookie": "secret",
                "items": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(NewtonExportError, match="credentials"):
        NewtonExportAdapter.ingest(export, "project-1")
