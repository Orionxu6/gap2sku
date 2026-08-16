"""SQLite ArtifactStore — P0 single-writer store with optimistic revision.

Spec 9.2:
  - Product Architect is the only project-level committer.
  - expected_revision required for writes.
  - Artifact versions immutable (no overwrite).
  - Idempotency keys return existing result.
  - SQLite WAL + transaction.

Tables (spec 9.3): runs, constraints, artifacts, artifact_edges,
  evidence_refs, feature_decisions, reviews, change_events, approvals,
  domain_events. This module creates artifacts + idempotency + edges;
  other tables are created by their respective domain modules.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from ..schemas.envelope import ArtifactEnvelope, ArtifactStatus
from .repository import ArtifactRepository


class ArtifactNotFound(Exception):
    pass


class ConcurrencyError(Exception):
    pass


class ArtifactStore(ArtifactRepository):
    """Thread-safe SQLite store. Single process; WAL mode."""

    _lock = threading.RLock()

    def __init__(self, db_path: str | Path = "shared/gap2sku.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.init_schema()

    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id    TEXT NOT NULL,
                    artifact_version INTEGER NOT NULL,
                    artifact_type  TEXT NOT NULL,
                    project_id     TEXT NOT NULL,
                    producer_agent TEXT NOT NULL,
                    producer_task_id TEXT NOT NULL,
                    status         TEXT NOT NULL,
                    content_hash   TEXT NOT NULL,
                    payload_json   TEXT NOT NULL,
                    created_at     TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL DEFAULT 'policy-v1',
                    input_refs_json TEXT NOT NULL DEFAULT '[]',
                    constraint_dependencies_json TEXT NOT NULL DEFAULT '[]',
                    source_snapshot_ids_json TEXT NOT NULL DEFAULT '[]',
                    data_mode TEXT NOT NULL DEFAULT 'REAL',
                    PRIMARY KEY (artifact_id, artifact_version)
                );
                CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type, project_id);

                CREATE TABLE IF NOT EXISTS artifact_meta (
                    artifact_id TEXT PRIMARY KEY,
                    latest_version INTEGER NOT NULL,
                    project_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    artifact_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_revisions (
                    project_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS artifact_edges (
                    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    src_id TEXT NOT NULL,
                    src_version INTEGER NOT NULL,
                    dst_id TEXT NOT NULL,
                    dst_version INTEGER NOT NULL,
                    relation TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_edges_src ON artifact_edges(src_id);
                CREATE INDEX IF NOT EXISTS idx_edges_dst ON artifact_edges(dst_id);
                """
            )
            # Compatible migration from the v0.1 store. SQLite cannot add all
            # columns in one portable statement, so add only those absent.
            existing = {row["name"] for row in self._conn.execute("PRAGMA table_info(artifacts)")}
            migrations = {
                "policy_version": "TEXT NOT NULL DEFAULT 'policy-v1'",
                "input_refs_json": "TEXT NOT NULL DEFAULT '[]'",
                "constraint_dependencies_json": "TEXT NOT NULL DEFAULT '[]'",
                "source_snapshot_ids_json": "TEXT NOT NULL DEFAULT '[]'",
                "data_mode": "TEXT NOT NULL DEFAULT 'REAL'",
            }
            for name, declaration in migrations.items():
                if name not in existing:
                    self._conn.execute(f"ALTER TABLE artifacts ADD COLUMN {name} {declaration}")
            self._migrate_enveloped_payloads()

    def _migrate_enveloped_payloads(self) -> None:
        """Repair the v0.1 bug that stored the whole envelope as payload_json."""
        rows = self._conn.execute(
            "SELECT artifact_id, artifact_version, payload_json FROM artifacts"
        ).fetchall()
        for row in rows:
            try:
                value = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict) or "payload" not in value or "artifact_id" not in value:
                continue
            self._conn.execute(
                "UPDATE artifacts SET payload_json=?, policy_version=?, input_refs_json=?, "
                "constraint_dependencies_json=?, source_snapshot_ids_json=?, data_mode=? "
                "WHERE artifact_id=? AND artifact_version=?",
                (json.dumps(value.get("payload", {}), ensure_ascii=False, sort_keys=True),
                 value.get("policy_version", "policy-v1"),
                 json.dumps(value.get("input_refs", [])),
                 json.dumps(value.get("constraint_dependencies", [])),
                 json.dumps(value.get("source_snapshot_ids", [])),
                 value.get("data_mode", "REAL"), row["artifact_id"], row["artifact_version"]),
            )

    def _row_to_envelope(self, row: sqlite3.Row) -> ArtifactEnvelope:
        payload = json.loads(row["payload_json"])
        return ArtifactEnvelope(
            artifact_id=row["artifact_id"],
            artifact_version=row["artifact_version"],
            artifact_type=row["artifact_type"],
            schema_version=row["schema_version"],
            policy_version=row["policy_version"],
            project_id=row["project_id"],
            producer_agent=row["producer_agent"],
            producer_task_id=row["producer_task_id"],
            status=ArtifactStatus(row["status"]),
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            input_refs=json.loads(row["input_refs_json"]),
            constraint_dependencies=json.loads(row["constraint_dependencies_json"]),
            source_snapshot_ids=json.loads(row["source_snapshot_ids_json"]),
            data_mode=row["data_mode"],
            payload=payload,
        )

    def get(self, artifact_id: str, version: int | None = None) -> ArtifactEnvelope | None:
        with self._lock:
            if version is None:
                row = self._conn.execute(
                    "SELECT a.* FROM artifacts a JOIN artifact_meta m ON a.artifact_id=m.artifact_id "
                    "AND a.artifact_version=m.latest_version WHERE a.artifact_id=?",
                    (artifact_id,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT * FROM artifacts WHERE artifact_id=? AND artifact_version=?",
                    (artifact_id, version),
                ).fetchone()
            return self._row_to_envelope(row) if row else None

    def list_by_type(self, artifact_type: str, project_id: str) -> list[ArtifactEnvelope]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT a.* FROM artifacts a JOIN artifact_meta m ON a.artifact_id=m.artifact_id "
                "AND a.artifact_version=m.latest_version "
                "WHERE a.artifact_type=? AND a.project_id=?",
                (artifact_type, project_id),
            ).fetchall()
            return [self._row_to_envelope(r) for r in rows]

    def list_all(self, project_id: str) -> list[ArtifactEnvelope]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT a.* FROM artifacts a JOIN artifact_meta m ON a.artifact_id=m.artifact_id "
                "AND a.artifact_version=m.latest_version WHERE a.project_id=?",
                (project_id,),
            ).fetchall()
            return [self._row_to_envelope(r) for r in rows]

    def project_revision(self, project_id: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT revision FROM project_revisions WHERE project_id=?", (project_id,)
            ).fetchone()
            return row["revision"] if row else 0

    def get_by_idempotency(self, idempotency_key: str) -> ArtifactEnvelope | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT artifact_id, artifact_version FROM idempotency WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if not row:
                return None
            return self.get(row["artifact_id"], row["artifact_version"])

    def commit(
        self,
        envelope: ArtifactEnvelope,
        expected_project_revision: int,
        idempotency_key: str,
    ) -> ArtifactEnvelope:
        """Commit a new artifact version. Spec 9.2, 13.3."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                # idempotency check
                existing = self.get_by_idempotency(idempotency_key)
                if existing is not None:
                    self._conn.execute("ROLLBACK")
                    return existing

                # optimistic revision check
                actual = self.project_revision(envelope.project_id)
                if actual != expected_project_revision:
                    self._conn.execute("ROLLBACK")
                    raise ConcurrencyError(
                        f"project {envelope.project_id} revision mismatch: expected {expected_project_revision}, got {actual}"
                    )

                # reject overwrite of existing version
                dup = self._conn.execute(
                    "SELECT 1 FROM artifacts WHERE artifact_id=? AND artifact_version=?",
                    (envelope.artifact_id, envelope.artifact_version),
                ).fetchone()
                if dup:
                    self._conn.execute("ROLLBACK")
                    raise ConcurrencyError(
                        f"artifact {envelope.artifact_id} v{envelope.artifact_version} already exists"
                    )

                # References are a hard integrity boundary. A caller may only
                # commit a derived artifact after every input version exists.
                missing_refs = [ref for ref in envelope.input_refs if self.get(ref) is None]
                if missing_refs:
                    self._conn.execute("ROLLBACK")
                    raise ArtifactNotFound(f"missing input_refs: {missing_refs}")

                self._conn.execute(
                    "INSERT INTO artifacts (artifact_id, artifact_version, artifact_type, project_id, "
                    "producer_agent, producer_task_id, status, content_hash, payload_json, created_at, schema_version, "
                    "policy_version, input_refs_json, constraint_dependencies_json, source_snapshot_ids_json, data_mode) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        envelope.artifact_id,
                        envelope.artifact_version,
                        envelope.artifact_type.value,
                        envelope.project_id,
                        envelope.producer_agent,
                        envelope.producer_task_id,
                        envelope.status.value,
                        envelope.content_hash,
                        json.dumps(envelope.payload, ensure_ascii=False, sort_keys=True),
                        envelope.created_at,
                        envelope.schema_version,
                        envelope.policy_version,
                        json.dumps(envelope.input_refs),
                        json.dumps(envelope.constraint_dependencies),
                        json.dumps(envelope.source_snapshot_ids),
                        envelope.data_mode,
                    ),
                )
                self._conn.execute(
                    "INSERT INTO artifact_meta (artifact_id, latest_version, project_id) "
                    "VALUES (?,?,?) ON CONFLICT(artifact_id) DO UPDATE SET latest_version=excluded.latest_version",
                    (envelope.artifact_id, envelope.artifact_version, envelope.project_id),
                )
                self._conn.execute(
                    "INSERT INTO idempotency (idempotency_key, artifact_id, artifact_version) VALUES (?,?,?)",
                    (idempotency_key, envelope.artifact_id, envelope.artifact_version),
                )
                self._conn.execute(
                    "INSERT INTO project_revisions (project_id, revision) VALUES (?,1) "
                    "ON CONFLICT(project_id) DO UPDATE SET revision=revision+1",
                    (envelope.project_id,),
                )
                self._conn.execute("COMMIT")
                return envelope
            except Exception:
                try:
                    self._conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    def mark_status(self, artifact_id: str, version: int, status: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE artifacts SET status=? WHERE artifact_id=? AND artifact_version=?",
                (status, artifact_id, version),
            )

    def add_edge(self, src_id: str, src_version: int, dst_id: str, dst_version: int, relation: str) -> None:
        with self._lock:
            for artifact_id, version in ((src_id, src_version), (dst_id, dst_version)):
                if self.get(artifact_id, version) is None:
                    raise ArtifactNotFound(f"edge references missing artifact {artifact_id} v{version}")
            self._conn.execute(
                "INSERT INTO artifact_edges (src_id, src_version, dst_id, dst_version, relation) VALUES (?,?,?,?,?)",
                (src_id, src_version, dst_id, dst_version, relation),
            )

    def edges_from(self, artifact_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM artifact_edges WHERE src_id=?", (artifact_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def edges_to(self, artifact_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM artifact_edges WHERE dst_id=?", (artifact_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
