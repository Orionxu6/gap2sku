---
name: supplier-capability-assessment
description: Assess supplier and manufacturing evidence against locked specification and sourcing constraints.
assign_when: Use for supplier shortlisting, RFQ response review, manufacturability, or sample planning.
version: 0.1.0
owner: gap2sku
agents: [gap2sku-supply]
license: Apache-2.0
---

# Supplier Capability Assessment

## Purpose

Use this skill to prove features are procurable under MOQ / mold / cost /
lead-time constraints.

## Inputs

- Feature Hypotheses (feature_id, cost_delta).
- Supplier Snapshot (offers: supplier_id, support_state, moq, base_unit_cost, existing_mold).
- Constraints (moq_max, factory_cost_max).

## Procedure

1. Validate input Schema.
2. For each feature, find supplier offers with support_state in (listed, confirmed).
3. Filter by moq <= moq_max and (base_unit_cost + cost_delta) <= factory_cost_max and existing_mold.
4. Accepted options go to accepted_options; others to rejected_options.
5. Conflicting support_state -> conflicts list, mark CONFLICT (never pick one as fact).
6. verification_level must reflect actual evidence (platform_visible != human_confirmed).

## Output

SupplierAssessment@1.0.0: assessment_id, accepted_options, rejected_options, conflicts.

## Failure Path

- No supplier snapshot -> BLOCKED.
- All offers unsupported -> return empty accepted_options (not an error).
