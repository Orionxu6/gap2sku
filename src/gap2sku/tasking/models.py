from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TaskState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REVISE = "REVISE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    project_id: str
    owner: str
    revision: int = Field(default=1, ge=1)
    state: TaskState = TaskState.PENDING
    depends_on: list[str] = Field(default_factory=list)
    input_refs: list[str] = Field(default_factory=list)
    expected_artifact_types: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    idempotency_key: str
    parent_task_id: str | None = None
    created_at: str = Field(default_factory=utcnow)
    updated_at: str = Field(default_factory=utcnow)


class TaskEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: int | None = None
    task_id: str
    project_id: str
    revision: int
    from_state: TaskState | None
    to_state: TaskState
    actor: str
    reason: str
    artifact_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utcnow)


class AgentEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    task_id: str
    revision: int = Field(ge=1)
    from_role: str
    to_roles: list[str]
    artifact_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    data_mode: str
    requested_action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow)
