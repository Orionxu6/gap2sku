from __future__ import annotations

import builtins
import json
import sqlite3
import threading
from pathlib import Path

from .models import TaskContract, TaskEvent, TaskState, utcnow


class TaskError(RuntimeError):
    pass


class TaskNotReady(TaskError):
    pass


class TaskPermissionDenied(TaskError):
    pass


TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.READY, TaskState.CANCELLED},
    TaskState.READY: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {TaskState.SUBMITTED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.SUBMITTED: {TaskState.ACCEPTED, TaskState.REVISE, TaskState.BLOCKED},
    TaskState.REVISE: {TaskState.READY, TaskState.CANCELLED},
    TaskState.BLOCKED: {TaskState.REVISE, TaskState.CANCELLED},
    TaskState.FAILED: {TaskState.REVISE, TaskState.CANCELLED},
    TaskState.ACCEPTED: set(),
    TaskState.CANCELLED: set(),
}


class TaskStore:
    """SQLite source of truth for work state; chat is never authoritative."""

    _lock = threading.RLock()

    def __init__(self, db_path: str | Path = "shared/gap2sku.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self.init_schema()

    def init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner TEXT NOT NULL,
              revision INTEGER NOT NULL, state TEXT NOT NULL, depends_on_json TEXT NOT NULL,
              input_refs_json TEXT NOT NULL, expected_types_json TEXT NOT NULL,
              acceptance_json TEXT NOT NULL, idempotency_key TEXT UNIQUE NOT NULL,
              parent_task_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id, state);
            CREATE TABLE IF NOT EXISTS task_events (
              event_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
              project_id TEXT NOT NULL, revision INTEGER NOT NULL, from_state TEXT,
              to_state TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL,
              artifact_refs_json TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(task_id) REFERENCES tasks(task_id)
            );
            """
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TaskContract:
        return TaskContract(
            task_id=row["task_id"], project_id=row["project_id"], owner=row["owner"],
            revision=row["revision"], state=row["state"],
            depends_on=json.loads(row["depends_on_json"]), input_refs=json.loads(row["input_refs_json"]),
            expected_artifact_types=json.loads(row["expected_types_json"]),
            acceptance_criteria=json.loads(row["acceptance_json"]),
            idempotency_key=row["idempotency_key"], parent_task_id=row["parent_task_id"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def create(self, task: TaskContract) -> TaskContract:
        with self._lock:
            existing = self._conn.execute(
                "SELECT * FROM tasks WHERE idempotency_key=?", (task.idempotency_key,)
            ).fetchone()
            if existing:
                return self._from_row(existing)
            self._conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (task.task_id, task.project_id, task.owner, task.revision, task.state.value,
                 json.dumps(task.depends_on), json.dumps(task.input_refs),
                 json.dumps(task.expected_artifact_types), json.dumps(task.acceptance_criteria),
                 task.idempotency_key, task.parent_task_id, task.created_at, task.updated_at),
            )
            self._record(task, None, task.state, "system", "task_created", [])
            return task

    def get(self, task_id: str) -> TaskContract | None:
        row = self._conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return self._from_row(row) if row else None

    def list(self, project_id: str, state: TaskState | None = None) -> list[TaskContract]:
        if state:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE project_id=? AND state=? ORDER BY task_id",
                (project_id, state.value),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY task_id", (project_id,)
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _dependencies_accepted(self, task: TaskContract) -> bool:
        return all((dep := self.get(task_id)) is not None and dep.state == TaskState.ACCEPTED for task_id in task.depends_on)

    def advance(
        self, task_id: str, to_state: TaskState, actor: str, reason: str,
        artifact_refs: builtins.list[str] | None = None,
    ) -> TaskContract:
        with self._lock:
            task = self.get(task_id)
            if not task:
                raise TaskError(f"task not found: {task_id}")
            if to_state not in TRANSITIONS[task.state]:
                raise TaskError(f"illegal transition {task.state.value} -> {to_state.value}")
            privileged = {"acceptance-gate", "gap2sku-reviewer", "human-manager"}
            if actor != task.owner and actor not in privileged:
                raise TaskPermissionDenied(f"{actor} cannot advance task owned by {task.owner}")
            if to_state == TaskState.READY and not self._dependencies_accepted(task):
                raise TaskNotReady(f"dependencies not accepted: {task.depends_on}")
            if to_state == TaskState.ACCEPTED and actor != "acceptance-gate":
                raise TaskPermissionDenied("only acceptance-gate may ACCEPT")
            old = task.state
            task.state = to_state
            task.updated_at = utcnow()
            self._conn.execute(
                "UPDATE tasks SET state=?, updated_at=? WHERE task_id=?",
                (to_state.value, task.updated_at, task_id),
            )
            self._record(task, old, to_state, actor, reason, artifact_refs or [])
            return task

    def create_revision(self, task_id: str, owner: str, reason: str) -> TaskContract:
        prior = self.get(task_id)
        if not prior:
            raise TaskError(f"task not found: {task_id}")
        new_id = f"{task_id.rsplit('-r', 1)[0]}-r{prior.revision + 1:03d}"
        revised = prior.model_copy(update={
            "task_id": new_id, "revision": prior.revision + 1, "state": TaskState.PENDING,
            "owner": owner, "parent_task_id": prior.task_id,
            "idempotency_key": f"revision:{prior.task_id}:{prior.revision + 1}",
            "created_at": utcnow(), "updated_at": utcnow(),
        })
        return self.create(revised)

    def events(self, task_id: str) -> builtins.list[TaskEvent]:
        rows = self._conn.execute(
            "SELECT * FROM task_events WHERE task_id=? ORDER BY event_id", (task_id,)
        ).fetchall()
        return [TaskEvent(
            event_id=row["event_id"], task_id=row["task_id"], project_id=row["project_id"],
            revision=row["revision"], from_state=row["from_state"], to_state=row["to_state"],
            actor=row["actor"], reason=row["reason"],
            artifact_refs=json.loads(row["artifact_refs_json"]), created_at=row["created_at"],
        ) for row in rows]

    def _record(self, task: TaskContract, old: TaskState | None, new: TaskState,
                actor: str, reason: str, refs: builtins.list[str]) -> None:
        self._conn.execute(
            "INSERT INTO task_events (task_id, project_id, revision, from_state, to_state, actor, reason, artifact_refs_json, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (task.task_id, task.project_id, task.revision, old.value if old else None,
             new.value, actor, reason, json.dumps(refs), utcnow()),
        )

    def close(self) -> None:
        self._conn.close()
