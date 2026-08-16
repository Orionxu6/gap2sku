# MEMORY.md - gap2sku-market

> Memory version: 1.0.0  
> Project: Gap2SKU  
> Agent: `gap2sku-market`  
> Role: Market and customer-evidence specialist  
> Projection mode: bootstrap-curated  
> Updated: 2026-08-06

## 1. Purpose And Authority

This file is the concise, human-readable projection of Market memory. It indexes reusable and verified market knowledge; it is not the transactional source of truth.

- Task state belongs to TaskStore.
- Market evidence and analysis outputs belong to Artifact Store.
- Version, dependency and invalidation state belongs to Artifact Graph.
- Canonical runtime memory belongs to Memory Store.
- Read and write permissions are governed by `memory.scope`.
- Runtime, `agent.yaml`, `AGENTS.md` and `rubrics.md` override this projection when conflicts exist.

Only records marked `active`, `accepted` and backed by valid `source_refs` may be reused. Historical memory is a labeling prior, not current market evidence.

## 2. Agent Identity

| Field | Confirmed value |
| --- | --- |
| Agent ID | `gap2sku-market` |
| Responsibility | Market demand and customer evidence |
| Reports to | `gap2sku-product-architect` |
| Primary outputs | Demand Structure, Pain Point Set, Competitor Gap Map, Feature Hypotheses |
| Forbidden decisions | Manufacturability, supplier selection, profit, final compliance and final GO |

Market includes Customer Insight responsibility. V1 does not create a separate Customer Agent.

## 3. Active Evidence Policies

### MEM-MKT-POL-001 - Evidence Before Conclusion

- Status: `active`
- Rule: Every key market claim requires an `evidence_id`. A pain-point claim must also resolve to an original review, question or interview excerpt.
- Source refs: `SOUL.md#证据原则`, `agent.yaml#evidence_policy`, `rubrics.md#硬性门禁`
- Invalidate when: Evidence contract or Artifact Schema is formally revised.

### MEM-MKT-POL-002 - Data Mode Must Be Explicit

- Status: `active`
- Rule: Every evidence-backed output declares live, cached, synthetic or mixed. Synthetic, inferred or unverified evidence cannot be presented as live market fact.
- Source refs: `agent.yaml#evidence_policy`, `AGENTS.md#证据接口`
- Invalidate when: The shared data-mode vocabulary changes.

### MEM-MKT-POL-003 - Freshness And Dual Source

- Status: `active`
- Rule: Key quantitative market signals older than 30 days are STALE. Search volume, CPC, market size and category growth require two sources; deviations above 20 percent must be reported.
- Source refs: `SOUL.md#证据原则`, `agent.yaml#evidence_policy`, `AGENTS.md#样本与时效规则`
- Invalidate when: Human Manager approves new category-specific freshness or source rules.

### MEM-MKT-POL-004 - Sample Adequacy

- Status: `active`
- Rule: Preferred review coverage is Top 10 listings or at least 500 one-to-three-star reviews. Scope may be expanded once with disclosure; continued insufficiency requires partial output and NEEDS_EVIDENCE.
- Source refs: `SOUL.md#工作流程`, `agent.yaml#evidence_policy`, `rubrics.md#硬性门禁`
- Invalidate when: A category-specific sample policy is approved.

### MEM-MKT-POL-005 - Five-Filter Pain Test

- Status: `active`
- Rule: A complaint becomes a Feature Hypothesis only after frequency, structural cause, pain severity, design translatability and commercial differentiation checks.
- Source refs: `SOUL.md#痛点筛选规则`, `AGENTS.md#痛点转功能规则`
- Invalidate when: The pain-point decision method is formally replaced.

### MEM-MKT-POL-006 - Anti-Self-Deception

- Status: `active`
- Rule: Every task checks positive reviews, pioneer competitors and survivor bias. Counter-evidence must remain visible.
- Source refs: `SOUL.md#防自欺校验`, `rubrics.md#痛点识别质量`
- Invalidate when: Reviewer approves an alternative evidence-control method.

### MEM-MKT-POL-007 - Demand-Side Signal Required

- Status: `active`
- Rule: Supplier promotion or social-media popularity cannot independently establish an opportunity. At least one level-one or level-two demand-side signal is required.
- Source refs: `SOUL.md#信号源可信度分级`, `agent.yaml#evidence_policy`
- Invalidate when: Signal-tier policy is formally updated.

### MEM-MKT-POL-008 - Early NO-GO Is A Signal

- Status: `active`
- Rule: Market may emit EARLY_NO_GO_SIGNAL when Top 3 concentration exceeds 70 percent or demand evidence fails, but only Leader and Human Manager may decide whether to stop.
- Source refs: `SOUL.md#必须主动协作的情形`, `AGENTS.md#EarlyNO-GO边界`
- Invalidate when: Decision authority or concentration threshold changes.

## 4. Active Collaboration Rules

- Market sends manufacturability questions to Supply through `CONSULT` with `consult_type=manufacturability`.
- Market sends price viability questions to Leader through `PRICE_VIABILITY_REQUEST` for routing to Economics.
- Supply rejection of a core feature does not erase user evidence; unresolved trade-offs trigger `EVIDENCE_CHALLENGE` to Leader.
- Sensitive categories trigger `NEEDS_EVIDENCE` with compliance-precheck context; Market does not perform final compliance review.
- Reviewer findings create new Market Artifact versions; old accepted or submitted versions are never overwritten.
- Market submits through `HANDOFF` and cannot mark its own Artifact ACCEPTED.

Sources: `agent.yaml#event_subscriptions`, `agent.yaml#event_emissions`, `AGENTS.md`.

## 5. Accepted Market Taxonomies

No market, pain-point, scenario or review-label taxonomy has yet passed the `memory.scope` promotion gate.

This means:

- No laptop-stand pain point is currently reusable Market Memory.
- No synthetic review frequency is a current market fact.
- No competitor price, rank or concentration value is stored as evergreen knowledge.
- Every new task must collect or receive current evidence before making a market claim.

## 6. Validated Reusable Lessons

No reusable market lesson has yet been promoted into canonical Knowledge Memory.

A lesson or taxonomy may be promoted only when it:

- belongs to the same project, category and market;
- comes from accepted Market Artifacts;
- has a valid Leader acceptance reference;
- includes source, sample, data mode and confidence metadata;
- contains reusable label definitions rather than one task's current metrics;
- declares review date and invalidation conditions.

## 7. Taxonomy Record Template

```yaml
memory_id: MEM-MKT-TAX-001
version: 1
record_type: pain_point_taxonomy
project_id: gap2sku
team_id: gap2sku-agentteam
category_id: category-id
market: US
scope_level: exact_category_market
taxonomy_name: category-pain-points
taxonomy_version: 1
labels:
  - label_id: PP-001
    canonical_name: placeholder-label
    definition: verified reusable definition
    inclusion_rules: []
    exclusion_rules: []
    example_evidence_refs: []
    counterexample_evidence_refs: []
source_refs: []
sample_profile_ref: sample-profile-v1
validation_status: accepted
evidence_confidence: high
data_mode: live
owner: gap2sku-market
status: active
valid_from: 2026-08-06
review_after: 2027-02-02
invalidation_conditions: []
leader_acceptance_ref: market-acceptance-v1
created_at: 2026-08-06T00:00:00+08:00
```

This is a field template, not an active memory record. Empty source, inclusion, exclusion, example or invalidation arrays must fail the real write gate.

## 8. Open Market-Memory Questions

| ID | Question | Impact | Required resolution |
| --- | --- | --- | --- |
| MOQ-001 | Which real review source is approved for the first commercial case? | No live pain taxonomy can be promoted | Approve source, rights, capture and freshness policy |
| MOQ-002 | How will review author identifiers be redacted? | Raw evidence may expose personal data | Define ingestion redaction and reference-only storage |
| MOQ-003 | What is the category identifier and taxonomy namespace? | Labels may collide across categories | Approve canonical category and label IDs |
| MOQ-004 | Who accepts Market Artifact before memory promotion? | Taxonomy writes cannot pass the gate | Implement Leader acceptance reference |
| MOQ-005 | Where is the Market taxonomy Schema? | Memory records cannot be deterministically validated | Create and test the memory-record Schema |
| MOQ-006 | How will taxonomy quality be evaluated across cases? | One-case labels may overfit | Validate with historical and live category samples |
| MOQ-007 | How will stale source Artifacts invalidate Knowledge Memory? | Old labels may survive unsupported | Connect Artifact Graph invalidation to Memory Store |
| MOQ-008 | Which labels are reusable versus task-specific? | Memory may accumulate temporary conclusions | Define promotion and rejection examples |

Open questions are not market evidence and cannot support a ProductSpec decision.

## 9. Superseded Or Invalidated Records

None in this bootstrap version.

Never delete an old taxonomy to hide a changed definition. Append a new version, mark the prior record `superseded` or `invalidated`, and preserve changed labels, source refs and downstream impact.

## 10. Maintenance Rules

- Keep this projection below 250 lines.
- Do not paste raw reviews, full interview transcripts, web pages or Artifact payloads.
- Do not store API keys, credentials, review usernames or personal identifiers.
- Do not store current price, CPC, sales rank or review-frequency values as evergreen rules.
- Revalidate taxonomy records every 180 days and evidence patterns every 90 days.
- Recheck every retrieved label against current task evidence before use.
- Refresh this projection only after an accepted Knowledge Memory change.
- If this projection conflicts with Memory Store, treat Memory Store as canonical and regenerate this file.
