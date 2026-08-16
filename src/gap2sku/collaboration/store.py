from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from .models import CollaborationEvent, MatrixMessageRecord


class CollaborationStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS matrix_messages (
              message_id TEXT PRIMARY KEY, room_id TEXT NOT NULL, project_id TEXT NOT NULL,
              sender_id TEXT NOT NULL, sender_role TEXT NOT NULL, body TEXT NOT NULL,
              origin_server_ts INTEGER NOT NULL, event_type TEXT NOT NULL, data_mode TEXT NOT NULL,
              raw_event_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_matrix_project_ts
              ON matrix_messages(project_id, origin_server_ts DESC);
            CREATE TABLE IF NOT EXISTS collaboration_events (
              event_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT NOT NULL,
              revision INTEGER NOT NULL, event_type TEXT NOT NULL, sender TEXT NOT NULL,
              recipients_json TEXT NOT NULL, summary TEXT NOT NULL, artifact_refs_json TEXT NOT NULL,
              status TEXT NOT NULL, data_mode TEXT NOT NULL, matrix_message_id TEXT,
              requested_action TEXT, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_collab_project_created
              ON collaboration_events(project_id, created_at DESC);
            """
        )

    def append_message(self, message: MatrixMessageRecord) -> MatrixMessageRecord:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO matrix_messages VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (message.message_id, message.room_id, message.project_id, message.sender_id,
                 message.sender_role, message.body, message.origin_server_ts, message.event_type,
                 message.data_mode, json.dumps(message.raw_event), message.created_at),
            )
            self._conn.commit()
        return message

    def append_event(self, event: CollaborationEvent) -> CollaborationEvent:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO collaboration_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (event.event_id, event.project_id, event.task_id, event.revision, event.event_type,
                 event.sender, json.dumps(event.recipients), event.summary,
                 json.dumps(event.artifact_refs), event.status, event.data_mode,
                 event.matrix_message_id, event.requested_action, event.created_at),
            )
            self._conn.commit()
        return event

    def list_messages(self, project_id: str, *, before: int | None = None, limit: int = 50) -> list[MatrixMessageRecord]:
        if before is None:
            rows = self._conn.execute(
                "SELECT * FROM matrix_messages WHERE project_id=? ORDER BY origin_server_ts DESC LIMIT ?",
                (project_id, min(limit, 200)),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM matrix_messages WHERE project_id=? AND origin_server_ts<? ORDER BY origin_server_ts DESC LIMIT ?",
                (project_id, before, min(limit, 200)),
            ).fetchall()
        return [MatrixMessageRecord(
            message_id=row["message_id"], room_id=row["room_id"], project_id=row["project_id"],
            sender_id=row["sender_id"], sender_role=row["sender_role"], body=row["body"],
            origin_server_ts=row["origin_server_ts"], event_type=row["event_type"],
            data_mode=row["data_mode"], raw_event=json.loads(row["raw_event_json"]), created_at=row["created_at"],
        ) for row in reversed(rows)]

    def list_events(self, project_id: str, *, limit: int = 100) -> list[CollaborationEvent]:
        rows = self._conn.execute(
            "SELECT * FROM collaboration_events WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, min(limit, 500)),
        ).fetchall()
        return [CollaborationEvent(
            event_id=row["event_id"], project_id=row["project_id"], task_id=row["task_id"],
            revision=row["revision"], event_type=row["event_type"], sender=row["sender"],
            recipients=json.loads(row["recipients_json"]), summary=row["summary"],
            artifact_refs=json.loads(row["artifact_refs_json"]), status=row["status"],
            data_mode=row["data_mode"], matrix_message_id=row["matrix_message_id"],
            requested_action=row["requested_action"], created_at=row["created_at"],
        ) for row in reversed(rows)]

    def close(self) -> None:
        self._conn.close()
