"""Trace recorder — local JSONL trace (spec 22).

P0: local JSONL + structured logs.
P1: OpenTelemetry/AgentLoop (optional, fallback to local).
Trace never blocks business artifact commit.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    run_id: str
    project_id: str
    task_id: str = ""
    agent_name: str = ""
    agent_role: str = ""
    tool_name: str = ""
    tool_call_id: str = ""
    artifact_id: str = ""
    artifact_version: int = 0
    parent_artifact_ids: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    token_usage: int = 0
    result_status: str = ""
    review_decision: str = ""
    replan_reason: str = ""
    timestamp: str = ""


class TraceRecorder:
    """Append-only JSONL trace. Thread-safe."""

    def __init__(self, path: str | Path = "evidence/domain-trace.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def record(self, event: TraceEvent) -> None:
        if not event.timestamp:
            event.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = event.model_dump_json()
        with self._lock, self.path.open("a") as f:
            f.write(line + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self._lock:
            return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
