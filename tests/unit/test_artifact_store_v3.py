from __future__ import annotations

import json
import sqlite3

import pytest

from gap2sku.artifacts.store import ArtifactNotFound, ArtifactStore, ConcurrencyError
from gap2sku.pipeline import _envelope
from gap2sku.schemas.envelope import ArtifactType


def env(artifact_id: str, refs: list[str] | None = None, version: int = 1):
    return _envelope(
        artifact_id, ArtifactType.EVIDENCE, "p1", "agent", "task-r001",
        {"only": "payload"}, input_refs=refs or [], version=version,
    )


def test_payload_and_metadata_round_trip(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts.db")
    value = env("a1")
    value.policy_version = "policy-x"
    value.data_mode = "SYNTHETIC"
    stored = store.commit(value, 0, "a1-v1")
    assert stored.payload == {"only": "payload"}
    loaded = store.get("a1")
    assert loaded and loaded.payload == {"only": "payload"}
    assert loaded.policy_version == "policy-x"
    raw = sqlite3.connect(tmp_path / "artifacts.db").execute("SELECT payload_json FROM artifacts").fetchone()[0]
    assert json.loads(raw) == {"only": "payload"}


def test_missing_refs_and_immutable_version(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts.db")
    with pytest.raises(ArtifactNotFound):
        store.commit(env("derived", ["missing"]), 0, "derived-v1")
    store.commit(env("a1"), 0, "a1-v1")
    with pytest.raises(ConcurrencyError):
        store.commit(env("a1"), 1, "duplicate-version")


def test_legacy_envelope_payload_migration(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "legacy.db")
    legacy = env("legacy")
    store.commit(legacy, 0, "legacy-v1")
    conn = sqlite3.connect(tmp_path / "legacy.db")
    conn.execute("UPDATE artifacts SET payload_json=?", (legacy.model_dump_json(),))
    conn.commit()
    conn.close()
    store.close()
    migrated = ArtifactStore(tmp_path / "legacy.db").get("legacy")
    assert migrated and migrated.payload == {"only": "payload"}


def test_edge_integrity(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "artifacts.db")
    store.commit(env("a1"), 0, "a1")
    with pytest.raises(ArtifactNotFound):
        store.add_edge("a1", 1, "a2", 1, "derived_from")
