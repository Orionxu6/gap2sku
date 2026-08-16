---
name: evidence-review-gate
description: Run independent deterministic evidence, specification, compliance, and approval gates.
assign_when: Use after candidate artifacts are submitted or whenever a prior review becomes stale.
version: 0.1.0
owner: gap2sku
agents: [gap2sku-reviewer]
license: Apache-2.0
---

# Evidence Review Gate

## Purpose

Use this skill to independently question evidence, constraints, and
consistency. You return only PASS / REVISE / BLOCK.

## Inputs

- Current ProductSpec (with spec_hash).
- Artifact subgraph.
- Deterministic rule results (R001-R012).

## Procedure

1. Run deterministic rules R001-R012 (code, not LLM).
2. Any ERROR -> BLOCK. Any WARNING -> REVISE. None -> PASS.
3. Bind decision to current spec_hash (R010).
4. Output Rule ID + Artifact Ref + Spec Hash for every finding.

## Output

ReviewResult@1.0.0: review_id, spec_id, spec_hash, decision, errors[], warnings[].

## Hard Rules

- LLM never overrides deterministic BLOCK.
- Never edit Spec or write project state.
- Missing Rule ID or Spec Hash -> Leader must not accept.
- Never output new unsupported features.
