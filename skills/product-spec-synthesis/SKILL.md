---
name: product-spec-synthesis
description: Assemble validated cross-role artifacts into a versioned product specification draft.
assign_when: Use after market, prototype, supply, economics, and compliance artifacts are available.
version: 0.1.0
owner: gap2sku
agents: [gap2sku-product-architect]
license: Apache-2.0
---

# Product Spec Synthesis

## Purpose

Use this skill to turn validated Artifacts + constraints into a versioned
ProductSpec draft.

## Inputs

- Valid Artifacts (PainPointSet, SupplierAssessment, EconomicsArtifact).
- ConstraintSet.
- Feature Hypotheses.

## Procedure

1. For each feature, build FeatureDecision:
   - ACCEPT requires Market + Supply + Economics refs (R004).
   - REJECT/DEFER requires rationale + reconsider_if (R009).
2. Compute spec_hash from spec content.
3. Set review_status=PENDING, approval_status=DRAFT.
4. Record artifact_refs for traceability.
5. Only Product Architect commits project-level Artifacts (R012).

## Output

ProductSpec@1.0.0 + FeatureDecision[]@1.0.0.

## Failure Path

- Hard constraint violated -> Spec marked BLOCKED, not published.
- ACCEPT feature missing evidence -> Reviewer BLOCK (R004).
