# Agent Contracts (spec 8, 5)

## Task Contract (spec 8)

Each Worker Task has `task_contract.json`:

```json
{
  "task_id": "...-market-r001",
  "project_id": "...",
  "revision": 1,
  "role": "market",
  "goal": "...",
  "input_artifacts": [{"artifact_id": "...", "artifact_version": 1, "sha256": "..."}],
  "relevant_constraints": ["target_market"],
  "allowed_tools": ["evidence.search_reviews"],
  "expected_output_type": "PainPointSet",
  "output_schema_version": "1.0.0",
  "deliverable_path": "shared/tasks/.../deliverables/pain-point-set.json",
  "acceptance_criteria": ["each pain point has evidence_ids", ...],
  "on_missing_data": "BLOCKED",
  "prohibited_actions": ["write project-level state", "call external write ops"]
}
```

## Task Result Status (spec 8)

- `SUCCESS`
- `SUCCESS_WITH_NOTES`
- `REVISION_NEEDED`
- `BLOCKED`

## Reviewer Gate Status (separate, spec 18)

- `PASS`
- `REVISE`
- `BLOCK`

Two status sets never mixed.

## Roles (spec 5.1)

| Role | Mapping | Independent Goal | Main Output | Not Responsible |
|---|---|---|---|---|
| Product Architect | Team Leader | Decompose, accept, version Spec | FeatureDecision, ProductSpec, RevisionPlan | Raw crawl, bypass constraints |
| Market Agent | Worker | Prove pain real/frequent/worth | EvidenceSet, PainPointSet, FeatureHypothesis | Supply promise, cost |
| Supply Agent | Worker | Prove Feature procurable | SupplierCapabilitySet, SupplierAssessment | Market demand |
| Economics Agent | Worker | Deterministic unit economics | EconomicsArtifact, Sensitivity | Fabricate rates, LLM mental math |
| Reviewer Agent | Worker (read-only) | Independent质疑 | ReviewResult: PASS/REVISE/BLOCK | Rewrite Spec, diverge new features |

## Hard Rules

- Worker SUCCESS != Leader ACCEPT.
- Only Product Architect commits project-level Artifacts.
- Reviewer read-only; never edits Spec.
- Impact analysis by deterministic graph algorithm, not LLM.
- All money by Decimal code; LLM never computes.
