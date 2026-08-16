---
name: unit-economics-evaluation
description: Recalculate product unit economics and sensitivities from explicit quote, BOM, fee, and logistics inputs.
assign_when: Use only when a supply artifact is available, including explicit missing or estimated states.
version: 0.1.0
owner: gap2sku
agents: [gap2sku-economics]
license: Apache-2.0
---

# Unit Economics Evaluation

## Purpose

Use this skill to verify unit economics with deterministic Decimal code.
You (the LLM) never compute cost/margin/constraint results.

## Inputs

- Supplier Assessment (accepted candidate).
- Fee Table (platform_fee_rate, fulfillment_fee, marketing_rate, loss_allowance_rate, packaging, shipping).
- Constraints (factory_cost_max, target_margin_min).

## Procedure

1. Validate input Schema.
2. Call economics.calculate with all inputs as decimal strings.
3. The tool computes: factory_total, landed_cost, platform_fee, marketing,
   loss_allowance, contribution_margin, contribution_margin_rate.
4. Hard constraints evaluated by deterministic code (PASS/FAIL).
5. Sensitivity: shipping +20%, marketing +20%, factory_cost +10%.
6. Call economics.verify to re-derive and confirm hash consistency.

## Output

EconomicsArtifact@1.0.0 with calculation_trace (non-empty), constraint_checks,
sensitivity_cases, assumption_version.

## Hard Rules

- All money via Decimal; JSON as decimal string.
- Missing input -> BLOCKED.
- calculation_trace must be non-empty (R007).
- LLM only interprets; never changes results.
