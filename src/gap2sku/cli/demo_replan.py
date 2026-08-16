"""demo-replan CLI — $8.00 -> $6.50 selective re-plan (spec 19, 25)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..pipeline import DomainCorePipeline
from ..replanning.coordinator import ReplanningCoordinator
from ..schemas.change import ChangeEvent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", default="8.00")
    parser.add_argument("--new", default="6.50")
    parser.add_argument("--fixture", default="data/fixtures/laptop_stand")
    parser.add_argument("--out", default="evidence/demo-replan-plan.json")
    args = parser.parse_args()

    # Run V1 first
    pipeline = DomainCorePipeline(Path(args.fixture))
    pipeline.run()

    # Apply change
    event = ChangeEvent(
        change_id="chg-002", project_id=pipeline.project_id, changed_by="human",
        path="business.factory_cost_max", old_value=args.old, new_value=args.new,
        old_version=1, new_version=2, reason="live demo constraint change",
        created_at="2026-08-03T00:00:00Z",
    )
    coordinator = ReplanningCoordinator(pipeline.store, pipeline.graph)
    result = coordinator.apply_change(event, pipeline.artifacts)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "change_event": result.change_event.model_dump(mode="json"),
        "impact_plan": result.impact_plan.model_dump(mode="json"),
        "spec_v2_hash": result.spec_v2_hash,
        "market_agent_calls": result.market_agent_calls,
        "preserved_count": len(result.impact_plan.preserved_artifacts),
        "stale_count": len(result.impact_plan.stale_artifacts) + len(result.impact_plan.recompute_artifacts),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"[demo-replan] change: {args.old} -> {args.new}")
    print(f"[demo-replan] preserved: {payload['preserved_count']}")
    print(f"[demo-replan] stale/recompute: {payload['stale_count']}")
    print(f"[demo-replan] market calls: {payload['market_agent_calls']} (must be 0)")
    print(f"[demo-replan] new tasks: {len(result.impact_plan.new_tasks)}")
    print(f"[demo-replan] output: {args.out}")


if __name__ == "__main__":
    main()
