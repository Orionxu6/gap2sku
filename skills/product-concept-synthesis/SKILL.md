---
name: product-concept-synthesis
description: Produce three materially different product concepts and a traceable SampleSpec draft from evidence and manufacturing boundaries.
assign_when: Use after the opportunity evidence and initial manufacturing boundary are accepted.
version: 0.2.0
owner: gap2sku
agents: [gap2sku-prototype-designer]
license: Apache-2.0
---

# Product Concept Synthesis

## Inputs

- OpportunityBrief and prioritized pain points.
- CategoryProfile and target-market constraints.
- Supply manufacturability boundary and compliance flags.

## Procedure

1. Generate exactly three concepts: a low-risk baseline, a balanced recommendation, and a high-differentiation exploration. They must differ in mechanism or value proposition, not color-only variants.
2. Link every differentiator to a pain-point reference and record its manufacturing and safety trade-off.
3. For each concept, record the current-product weakness it changes, the source of the idea, category advantage retained, likely failure mode, cost direction, compliance impact, and validation task.
4. Produce a draft SampleSpec using only fields from the active CategoryProfile. Separate locked values, target ranges, assumptions, and unknowns.
5. Call `image.generate` only after the concept text and provisional dimensions are versioned. The prompt must include category, user/use scene, key geometry and dimensions, materials/finish, structure, manufacturing form, camera view, neutral background, and negative constraints: no text, logo, certification mark, hands, supplier identity, or feature absent from SampleSpec.
6. Persist `RenderPromptRecord` and `RenderManifest` with input refs, model, seed, prompt hash, spec hash, output hash, provider, and data mode.
7. Mark every generated image `SYNTHETIC_CONCEPT`; never treat it as CAD, test evidence, or supplier capability.
8. After Human Manager selects a concept, create a new locked revision rather than mutating the draft. Generate one RFQ render for the selected concept and reject it if any visible feature conflicts with the locked SampleSpec.

## Output

- `ProductConceptSet`, `SampleSpec`, `RenderPromptRecord`, and `RenderManifest`.

## Failure Path

- Missing manufacturing boundary or CategoryProfile -> submit draft and request evidence; do not lock.
- Image provider unavailable -> emit `MODEL_DEGRADED` and use the versioned replay asset.
- Image/spec mismatch -> Reviewer requires a new render before RFQ.
