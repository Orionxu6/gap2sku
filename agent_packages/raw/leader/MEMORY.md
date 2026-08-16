# MEMORY.md - gap2sku-product-architect

> Memory version: 1.0.0  
> Project: Gap2SKU  
> Agent: `gap2sku-product-architect`  
> Runtime alias: `gap2sku-leader`  
> Projection mode: bootstrap-curated  
> Updated: 2026-08-06

## 1. Purpose And Authority

This file is the concise, human-readable projection of Leader memory. It stores reusable, verified decisions and pointers. It is not the transactional source of truth.

- Task state belongs to TaskStore.
- Formal product artifacts belong to Artifact Store.
- Dependency, version and invalidation state belongs to Artifact Graph.
- Canonical runtime memory belongs to Memory Store.
- Read and write permissions are governed by `memory.scope`.
- `agent.yaml`, `AGENTS.md`, `rubrics.md` and Runtime enforcement override this projection when conflicts exist.

Only records marked `active` and backed by valid `source_refs` may influence a decision. A memory record never authorizes a tool, Skill, state transition, purchase, production action or funding commitment.

## 2. Project Identity

| Field | Confirmed value |
| --- | --- |
| Project | Gap2SKU |
| Objective | Convert evidence-backed market gaps into manufacturable, profitable and reviewable ProductSpec decisions |
| Operating model | Human Manager + one Leader + four specialist Workers |
| Collaboration shape | Event-driven DAG with versioned Artifacts |
| Current maturity | Contract-layer construction; runtime enforcement and real-data validation remain incomplete |

## 3. Team Responsibility Map

| Role | Exclusive responsibility |
| --- | --- |
| `human-manager` | Business goals, exceptions, funding and final external commitment |
| `gap2sku-product-architect` | Planning, delegation, dependency control, conflict resolution, ProductSpec synthesis and decision packaging |
| `gap2sku-market` | User pain points, demand structure, competitor gaps, price signals and feature hypotheses |
| `gap2sku-supply` | Manufacturability, supplier capability, MOQ, cost, lead time, tooling and supply risk |
| `gap2sku-economics` | Cost stack, price viability, contribution margin and sensitivity analysis |
| `gap2sku-reviewer` | Independent evidence, rule, consistency, version and compliance review |

V1 does not create a separate Customer Agent. Customer insight belongs to Market. Compliance is a checked capability used through Supply and Reviewer, not an independent Worker.

## 4. Active Architecture Decisions

### MEM-ARCH-001 - DAG Collaboration

- Status: `active`
- Decision: Market and Supply may run in parallel. Economics depends on valid Supply cost inputs and, when pricing is involved, valid Market price signals. Reviewer depends on the integrated ProductSpec.
- Reason: Preserve specialist ownership while allowing safe parallelism.
- Source refs: `agent.yaml#planner`, `AGENTS.md#正常协作路径`
- Invalidate when: Team topology or dependency policy is formally changed.

### MEM-ARCH-002 - Responsibility Isolation

- Status: `active`
- Decision: Leader must not perform raw market retrieval, supplier screening, financial calculation or independent review. These actions belong to their responsible Workers and whitelisted tools.
- Reason: Prevent one model from producing, validating and approving the same claim.
- Source refs: `agent.yaml#skills`, `agent.yaml#tools`, `AGENTS.md#当前团队与职责边界`
- Invalidate when: `agent.yaml` permission policy changes.

### MEM-ARCH-003 - Structured Events Change State

- Status: `active`
- Decision: Matrix/Element messages are notifications. Only schema-valid events written to TaskStore and Artifact Graph may change system state.
- Reason: Chat text is not sufficiently deterministic or auditable for commercial workflow control.
- Source refs: `AGENTS.md#统一事件信封`, `agent.yaml#event_contract`
- Invalidate when: The runtime adopts another audited transactional event mechanism.

### MEM-ARCH-004 - Reviewer And Acceptance Separation

- Status: `active`
- Decision: Reviewer may return PASS or BLOCK. Leader cannot override BLOCK. A BLOCK requires a new revision. Only AcceptanceGate may set ACCEPTED.
- Reason: Separate product synthesis, independent review and system acceptance.
- Source refs: `agent.yaml#state_machine`, `agent.yaml#hard_constraints`, `rubrics.md#结论边界`
- Invalidate when: State-machine permissions are formally revised.

### MEM-ARCH-005 - Artifact Version And Invalidation

- Status: `active`
- Decision: Artifact updates append a version, preserve prior history and invalidate affected downstream nodes. Review is valid only for the exact current `spec_hash`.
- Reason: Prevent old evidence, old cost or old review results from approving a new ProductSpec.
- Source refs: `AGENTS.md#Artifact失效规则`, `memory.scope#versioning`
- Invalidate when: Artifact Graph versioning semantics change.

### MEM-ARCH-006 - Partial Output Cannot Become GO

- Status: `active`
- Decision: Missing required dependencies force `output_mode=partial`. Partial output may recommend REVISE or NO_GO, but cannot recommend GO or enter AcceptanceGate.
- Reason: Missing evidence must not be replaced with model speculation.
- Source refs: `agent.yaml#degradation`, `AGENTS.md#缺口与部分产物`, `rubrics.md#硬性门禁`
- Invalidate when: Human Manager approves a new formal partial-acceptance policy.

### MEM-ARCH-007 - Human Checkpoints Are Blocking

- Status: `active`
- Decision: A triggered Human Checkpoint creates `human_hold`. While active, Leader cannot dispatch, integrate, submit to Reviewer or run AcceptanceGate.
- Reason: Funding, final pricing, sensitive compliance, repeated revisions and veto decisions require accountable human authority.
- Source refs: `agent.yaml#human_checkpoints`, `AGENTS.md#HumanHold`
- Invalidate when: Checkpoint policy or Human Manager authority changes.

### MEM-ARCH-008 - Memory Uses Least Privilege

- Status: `active`
- Decision: Leader may read scoped Session and Product Memory and may write only versioned `decision_outcome` records. Every other write is denied.
- Reason: Prevent cross-project leakage, memory pollution and silent mutation of prior decisions.
- Source refs: `agent.yaml#memory_scope`, `memory.scope#capabilities`
- Invalidate when: `agent.yaml` grants a different explicit memory permission.

## 5. Active Operating Rules

- Integrate only Worker Artifacts that are accepted, valid and not stale.
- Every key fact in ProductSpec and DecisionRecord must resolve to Artifact and evidence references.
- Always disclose `data_mode` and confidence. Synthetic data cannot be presented as live market evidence.
- Do not average conflicting values. Preserve both sources and resolve the conflict explicitly.
- Never modify another Agent's Artifact. Return findings to the responsible Agent for a new version.
- A current TaskContract may override task-specific defaults, but it cannot override framework security or role permissions.
- Budget consumption at 80 percent triggers warning and human hold. Budget exhaustion does not authorize automatic extension.
- Production, procurement, listing, payment and funding always require Human Manager approval.

Sources: `agent.yaml`, `AGENTS.md`, `rubrics.md`, `memory.scope`.

## 6. Confirmed Human Decisions

No Human Decision has yet been promoted into canonical Product Memory through the required write gate.

When the first decision is promoted, record at minimum:

```yaml
memory_id: MEM-DEC-001
version: 1
record_type: decision_outcome
project_id: gap2sku
team_id: gap2sku-agentteam
scope_level: exact_product_market
root_task_id: task-id
task_revision: 1
statement: concise approved decision
outcome: GO
approval_status: human_approved
source_refs: []
evidence_confidence: high
data_mode: live
owner: human-manager
status: active
valid_from: 2026-08-06
review_after: 2026-09-05
invalidation_conditions: []
created_at: 2026-08-06T00:00:00+08:00
```

The template is illustrative only. An empty `source_refs` or `invalidation_conditions` array must fail the real write gate.

## 7. Validated Reusable Lessons

No lesson has yet met the promotion requirements of `memory.scope`.

A lesson may be promoted only when it:

- is supported by valid Artifact references;
- has explicit product, category and market scope;
- has survived review or Human Manager approval;
- declares data mode, confidence and invalidation conditions;
- remains useful beyond one task.

## 8. Open Engineering Questions

| ID | Question | Blocking impact | Required resolution |
| --- | --- | --- | --- |
| OQ-001 | Where is the executable Loader for `SOUL.md`, `AGENTS.md`, `rubrics.md` and `memory.scope`? | Contract files may exist without runtime enforcement | Implement and test a fail-closed Loader |
| OQ-002 | Where are the eight referenced JSON Schemas? | Events and Artifacts cannot be deterministically validated | Create schemas and schema tests |
| OQ-003 | Where are the seven whitelisted Leader Skills? | Allowed capabilities are named but not executable | Create versioned SKILL contracts and runners |
| OQ-004 | Is Artifact Graph persisted with versions, hash and dependency edges? | Invalidation and partial rerun cannot be trusted | Implement graph persistence and replay tests |
| OQ-005 | How are structured events transported and acknowledged? | Agent cooperation may fall back to file polling or chat | Implement event delivery, ack, timeout and retry |
| OQ-006 | Which real market, supplier, logistics, fee and compliance sources will replace fixtures? | System cannot support commercial decisions | Approve connectors, provenance and freshness policies |
| OQ-007 | How will Reviewer BLOCK and Worker failure paths be regression-tested? | Demo may only prove the happy path | Add golden datasets and failure-loop tests |
| OQ-008 | What model-routing policy will reduce correlated errors across Agents? | One shared model may repeat the same blind spots | Define model roles, deterministic tools and fallback policy |

Open questions are not facts. They must not be used as decision inputs until resolved and promoted through the memory write gate.

## 9. Superseded Or Invalidated Records

None in this bootstrap version.

Never delete an old record to hide a changed decision. Append a new version, set the prior record to `superseded` or `invalidated`, and preserve the reason and downstream impact.

## 10. Maintenance Rules

- Keep this projection concise; target no more than 250 lines.
- Do not paste raw reviews, supplier files, ProductSpec payloads or complete task histories.
- Do not store API keys, credentials, personal identifiers or hidden reasoning.
- Review market/pricing memories every 30 days and supplier/cost memories every 14 days, as defined by `memory.scope`.
- Refresh this projection after an approved Product Memory change.
- If this file conflicts with Memory Store, treat Memory Store as canonical and regenerate this projection.
