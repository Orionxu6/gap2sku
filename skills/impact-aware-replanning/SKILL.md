---
name: impact-aware-replanning
description: Propagate artifact invalidation and create the smallest safe revision plan after a change.
assign_when: Use when a constraint, quote, policy, test, or locked specification changes.
version: 0.1.0
owner: gap2sku
agents: [gap2sku-product-architect]
license: Apache-2.0
---

# Impact-Aware Replanning

## Purpose

Use this skill when a constraint changes and you must selectively re-run
only affected tasks, preserving valid upstream evidence.

## Inputs

- ChangeEvent (path, old_value, new_value).
- Current Artifact Graph.
- Current Project State.

## Procedure (deterministic, no LLM)

1. Commit new Constraint version; old version immutable.
2. Find artifacts whose constraint_dependencies contains changed path.
3. Mark them STALE.
4. BFS downstream in Artifact Graph.
5. Map affected artifact types to responsible roles.
6. Generate ImpactPlan: preserved / stale / recompute / skipped.
7. Create new revision Task IDs (r002); never overwrite old tasks.
8. Unaffected artifacts keep id/version/hash.
9. New Spec re-enters Reviewer Gate + publish approval.

## Output

ImpactPlan@1.0.0 + new revision task IDs.

## Expected for factory_cost_max $8.00 -> $6.50

- PRESERVED: Review Snapshots, Market Evidence, PainPointSet, Feature Hypotheses, raw SupplierCapability.
- STALE/RECOMPUTE: SupplierAssessment, Economics, FeatureDecisions, ProductSpec, ReviewResult.
- SKIPPED: Market Agent (calls = 0), external page fetch, raw supplier data collection.
