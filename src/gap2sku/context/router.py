"""Context Router — deterministic minimal context per role (spec 12).

Deterministic: only role policy + artifact type + dependency + version.
No Chain-of-Thought. No full Matrix transcript.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..schemas.envelope import ArtifactEnvelope, ArtifactType

# Which artifact types each role should receive (spec 12 table).
ROLE_POLICY: dict[str, set[str]] = {
    "market": {
        ArtifactType.CONSTRAINT.value,
        ArtifactType.REVIEW_SNAPSHOT.value,
        ArtifactType.EVIDENCE.value,
    },
    "supply": {
        ArtifactType.CONSTRAINT.value,
        ArtifactType.FEATURE_HYPOTHESIS.value,
        ArtifactType.SUPPLIER_CAPABILITY.value,
    },
    "economics": {
        ArtifactType.CONSTRAINT.value,
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.SUPPLIER_CAPABILITY.value,
    },
    "product-architect": {
        ArtifactType.CONSTRAINT.value,
        ArtifactType.PAIN_POINT_SET.value,
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.ECONOMICS.value,
        ArtifactType.FEATURE_DECISION.value,
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.REVIEW_RESULT.value,
    },
    "reviewer": {
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.FEATURE_DECISION.value,
        ArtifactType.ECONOMICS.value,
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.PAIN_POINT_SET.value,
        ArtifactType.EVIDENCE.value,
        ArtifactType.REVIEW_RESULT.value,
    },
}

# Excluded types per role (never send).
EXCLUDED_TYPES: dict[str, set[str]] = {
    "market": {ArtifactType.SUPPLIER_ASSESSMENT.value, ArtifactType.ECONOMICS.value},
    "supply": {ArtifactType.EVIDENCE.value},
    "economics": {ArtifactType.EVIDENCE.value, ArtifactType.REVIEW_SNAPSHOT.value},
}


class ContextBundle(BaseModel):
    project_id: str
    task_id: str
    role: str
    schema_versions: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    constraint_versions: dict[str, int] = Field(default_factory=dict)
    content_hashes: list[str] = Field(default_factory=list)
    token_budget: int = 12000
    excluded_types: list[str] = Field(default_factory=list)
    generated_at: str = ""


class ContextRouter:
    """Deterministic context builder."""

    @staticmethod
    def build_bundle(
        project_id: str,
        task_id: str,
        role: str,
        all_artifacts: list[ArtifactEnvelope],
        constraint_versions: dict[str, int] | None = None,
        token_budget: int = 12000,
    ) -> tuple[ContextBundle, list[ArtifactEnvelope]]:
        allowed = ROLE_POLICY.get(role, set())
        excluded = EXCLUDED_TYPES.get(role, set())

        selected: list[ArtifactEnvelope] = []
        for a in all_artifacts:
            if a.artifact_type.value in excluded:
                continue
            if a.artifact_type.value in allowed:
                selected.append(a)

        bundle = ContextBundle(
            project_id=project_id,
            task_id=task_id,
            role=role,
            artifact_refs=[a.artifact_id for a in selected],
            schema_versions=sorted({f"{a.artifact_type.value}@{a.schema_version}" for a in selected}),
            constraint_versions=constraint_versions or {},
            content_hashes=[a.content_hash for a in selected],
            token_budget=token_budget,
            excluded_types=sorted(excluded),
        )
        return bundle, selected
