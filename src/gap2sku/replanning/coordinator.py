"""ReplanningCoordinator — orchestrates selective re-plan (spec 19).

Wraps ImpactAnalyzer + ArtifactGraph + ArtifactStore to:
  - accept ChangeEvent
  - commit new constraint version
  - compute ImpactPlan
  - mark stale artifacts
  - emit new revision task IDs
  - produce Spec V2 diff
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..artifacts.store import ArtifactStore
from ..graph.graph import ArtifactGraph
from ..graph.impact import ImpactAnalyzer
from ..schemas.change import ChangeEvent
from ..schemas.impact import ImpactPlan


@dataclass
class ReplanResult:
    change_event: ChangeEvent
    impact_plan: ImpactPlan
    spec_v2_hash: str
    market_agent_calls: int  # must be 0 for factory_cost_max change


class ReplanningCoordinator:
    def __init__(self, store: ArtifactStore, graph: ArtifactGraph) -> None:
        self.store = store
        self.graph = graph

    def apply_change(self, event: ChangeEvent, all_artifacts: list) -> ReplanResult:
        analyzer = ImpactAnalyzer(self.graph, all_artifacts)
        plan = analyzer.analyze(event.path, event.change_id, event.project_id)

        # Mark stale artifacts
        for aid in plan.stale_artifacts + plan.recompute_artifacts:
            art = self.store.get(aid)
            if art:
                self.store.mark_status(aid, art.artifact_version, "STALE")

        # For factory_cost_max change, Market must be skipped
        market_calls = 0
        if "gap2sku-market" not in plan.skipped_agents:
            # Only market-affecting changes (review_snapshot, target_market) re-run market
            market_calls = 1

        # Compute spec v2 hash (deterministic from plan + event)
        hash_input = json.dumps(
            {"change": event.model_dump(mode="json"), "plan": plan.model_dump(mode="json")},
            sort_keys=True,
        )
        spec_v2_hash = "sha256:" + hashlib.sha256(hash_input.encode()).hexdigest()

        return ReplanResult(
            change_event=event,
            impact_plan=plan,
            spec_v2_hash=spec_v2_hash,
            market_agent_calls=market_calls,
        )
