"""Impact Analysis — deterministic BFS selective re-plan (spec 19).

Algorithm (spec 19.1):
  1. Commit new Constraint version.
  2. Find artifacts whose constraint_dependencies include changed path.
  3. Mark them STALE.
  4. BFS downstream in Artifact Graph.
  5. Map artifact types to responsible roles.
  6. Generate ImpactPlan: preserved / stale / recompute / skipped.
  7. Leader creates revision tasks (new IDs, no overwrite).
  8. Unaffected artifacts keep id/version/hash.
"""
from __future__ import annotations

from ..schemas.envelope import ArtifactEnvelope, ArtifactType
from ..schemas.impact import ImpactPlan
from .graph import ArtifactGraph

# Map artifact type -> responsible agent role (spec 19.1 step 5).
ROLE_BY_TYPE: dict[str, str] = {
    ArtifactType.EVIDENCE.value: "gap2sku-market",
    ArtifactType.REVIEW_SNAPSHOT.value: "gap2sku-market",
    ArtifactType.PAIN_POINT_SET.value: "gap2sku-market",
    ArtifactType.FEATURE_HYPOTHESIS.value: "gap2sku-market",
    ArtifactType.SUPPLIER_CAPABILITY.value: "gap2sku-supply",
    ArtifactType.SUPPLIER_ASSESSMENT.value: "gap2sku-supply",
    ArtifactType.ECONOMICS.value: "gap2sku-economics",
    ArtifactType.FEATURE_DECISION.value: "gap2sku-product-architect",
    ArtifactType.PRODUCT_SPEC.value: "gap2sku-product-architect",
    ArtifactType.REVIEW_RESULT.value: "gap2sku-reviewer",
}

# Which constraint paths each agent re-runs for (spec 19.4).
CONSTRAINT_PATH_IMPACT: dict[str, set[str]] = {
    "business.factory_cost_max": {
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.ECONOMICS.value,
        ArtifactType.FEATURE_DECISION.value,
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.REVIEW_RESULT.value,
    },
    "business.moq_max": {
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.ECONOMICS.value,
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.REVIEW_RESULT.value,
    },
    "business.target_margin_min": {
        ArtifactType.ECONOMICS.value,
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.REVIEW_RESULT.value,
    },
    "data.review_snapshot": {
        ArtifactType.EVIDENCE.value,
        ArtifactType.PAIN_POINT_SET.value,
        ArtifactType.FEATURE_HYPOTHESIS.value,
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.ECONOMICS.value,
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.REVIEW_RESULT.value,
    },
    "business.target_market": {
        ArtifactType.EVIDENCE.value,
        ArtifactType.PAIN_POINT_SET.value,
        ArtifactType.FEATURE_HYPOTHESIS.value,
        ArtifactType.SUPPLIER_ASSESSMENT.value,
        ArtifactType.ECONOMICS.value,
        ArtifactType.PRODUCT_SPEC.value,
        ArtifactType.REVIEW_RESULT.value,
    },
}


class ImpactAnalyzer:
    """Deterministic impact analysis. No LLM (spec rule 14)."""

    def __init__(self, graph: ArtifactGraph, all_artifacts: list[ArtifactEnvelope]) -> None:
        self.graph = graph
        self.all_artifacts = all_artifacts
        self.by_id: dict[str, ArtifactEnvelope] = {a.artifact_id: a for a in all_artifacts}

    def analyze(self, changed_path: str, change_id: str, project_id: str) -> ImpactPlan:
        # 1. directly affected: constraint_dependencies contains path
        directly_affected: set[str] = set()
        for art in self.all_artifacts:
            if changed_path in art.constraint_dependencies:
                directly_affected.add(art.artifact_id)

        # 1b. also use CONSTRAINT_PATH_IMPACT for type-level mapping
        type_impact = CONSTRAINT_PATH_IMPACT.get(changed_path, set())
        for art in self.all_artifacts:
            if art.artifact_type.value in type_impact:
                directly_affected.add(art.artifact_id)

        # 2. BFS downstream
        stale: set[str] = set()
        for aid in directly_affected:
            stale.add(aid)
            stale.update(self.graph.downstream(aid))

        # 3. preserved = all - stale
        all_ids = {a.artifact_id for a in self.all_artifacts}
        preserved = all_ids - stale

        # 4. skipped agents: a role is skipped if NONE of its artifact types
        #    appear in the affected (stale) set.
        affected_types: set[str] = set()
        for aid in stale:
            stale_art = self.by_id.get(aid)
            if stale_art:
                affected_types.add(stale_art.artifact_type.value)

        # Market re-runs iff any market-owned type is affected.
        market_types = {
            ArtifactType.EVIDENCE.value,
            ArtifactType.REVIEW_SNAPSHOT.value,
            ArtifactType.PAIN_POINT_SET.value,
            ArtifactType.FEATURE_HYPOTHESIS.value,
        }
        skipped_agents: set[str] = set()
        for atype, role in ROLE_BY_TYPE.items():
            if atype not in affected_types:
                skipped_agents.add(role)
        # De-duplicate: if market types affected, ensure market not skipped.
        if affected_types & market_types:
            skipped_agents.discard("gap2sku-market")

        # 5. new task IDs (revision r002)
        new_tasks: list[str] = []
        for aid in sorted(stale):
            task_art = self.by_id.get(aid)
            if not task_art:
                continue
            new_tasks.append(f"{project_id}-{task_art.artifact_type.value.lower()}-r002")

        return ImpactPlan(
            change_id=change_id,
            preserved_artifacts=sorted(preserved),
            stale_artifacts=sorted(stale - directly_affected),
            recompute_artifacts=sorted(directly_affected),
            new_tasks=new_tasks,
            skipped_agents=sorted(skipped_agents),
            reason=f"{changed_path} changed",
        )
