"""ArtifactRepository — abstract interface for pluggable storage backends.

P0 implementation: SQLite (see store.py).
Future: PostgreSQL (spec 9.3 notes Repository interface isolation).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas.envelope import ArtifactEnvelope


class ArtifactRepository(ABC):
    """Abstract repository. Implementations must be concurrency-safe."""

    @abstractmethod
    def init_schema(self) -> None: ...

    @abstractmethod
    def get(self, artifact_id: str, version: int | None = None) -> ArtifactEnvelope | None: ...

    @abstractmethod
    def list_by_type(self, artifact_type: str, project_id: str) -> list[ArtifactEnvelope]: ...

    @abstractmethod
    def commit(self, envelope: ArtifactEnvelope, expected_project_revision: int, idempotency_key: str) -> ArtifactEnvelope: ...

    @abstractmethod
    def mark_status(self, artifact_id: str, version: int, status: str) -> None: ...

    @abstractmethod
    def get_by_idempotency(self, idempotency_key: str) -> ArtifactEnvelope | None: ...

    @abstractmethod
    def project_revision(self, project_id: str) -> int: ...

    @abstractmethod
    def list_all(self, project_id: str) -> list[ArtifactEnvelope]: ...
