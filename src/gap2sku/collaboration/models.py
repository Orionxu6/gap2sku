from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class MatrixMessageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    room_id: str
    project_id: str
    sender_id: str
    sender_role: str
    body: str
    origin_server_ts: int
    event_type: str = "m.room.message"
    data_mode: str = "REAL"
    raw_event: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow)


class CollaborationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    project_id: str
    task_id: str
    revision: int = Field(ge=1)
    event_type: str
    sender: str
    recipients: list[str]
    summary: str
    artifact_refs: list[str] = Field(default_factory=list)
    status: str
    data_mode: str
    matrix_message_id: str | None = None
    requested_action: str | None = None
    created_at: str = Field(default_factory=utcnow)
