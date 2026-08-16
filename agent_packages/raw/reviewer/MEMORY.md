# MEMORY.md - gap2sku-reviewer

> Projection version: 1.0.0  
> Agent ID: `gap2sku-reviewer`  
> Canonical source: Gap2SKU Memory Store  
> Access policy: `memory.scope`  
> Last refreshed: 2026-08-06

本文件是 Reviewer 长期记忆的人工可读投影，用于恢复稳定审查规则、已裁决的规则校准和未决问题。它不是当前 Review Report、Finding 列表、规则注册表或业务 Artifact，不能替代当前锁定快照与版本化规则集。

## 1. 使用边界

- 当前 Product Spec、Artifact Graph 快照和规则集版本优先于本文件。
- `MEMORY.md` 不授予新的事件、Skill、工具、阻断或最终决策权限。
- 当前任务 Finding、PASS/BLOCK 结果和业务数据只存在 Artifact Store。
- 历史误判模式不能自动推翻当前 Finding，也不能自动触发 BLOCK。
- 单个异议或单个案例不能晋升为通用规则校准；至少需要3个已裁决案例。
- 本文件与 Memory Store 冲突时，以 Memory Store 为准并重新生成本文件。
- Reviewer 不得直接覆盖本文件；只有通过 `memory.scope` 门禁的记录才能刷新投影。

## 2. 当前运行身份

- Agent: `gap2sku-reviewer`
- Role: Independent review and blocking Agent
- Reports to: `gap2sku-product-architect`
- Decision consumers: Leader、AcceptanceGate、Human Manager。
- Owns: 规则执行、证据抽检、跨域一致性、一票否决、人类闸口、Finding 和评审分级。
- Does not own: 产品设计、补造证据、修改 Worker Artifact、采购付款或最终 GO。
- Required outputs: `review-report`、`review-findings`、`rule-results`、`review-summary`；发生异议时增加 `review-appeal-record`。

Sources: `SOUL.md`, `AGENTS.md`, `agent.yaml`.

## 3. Active Reviewer Policies

### MEM-REV-POL-001 - Review Is Independent From Consensus

- Status: `active`
- Rule: Leader 推荐、多个 Agent 一致和进度压力都不能替代规则与证据；Reviewer 不读取其他 Agent 的隐藏推理作为依据。
- Source refs: `SOUL.md#审查独立性`, `agent.yaml#hard_constraints`
- Invalidate when: 独立审查治理政策正式更新。

### MEM-REV-POL-002 - Every Review Locks A Current Snapshot

- Status: `active`
- Rule: 每次评审必须锁定 Task、revision、Product Spec hash、Artifact Graph、规则版本和 Human Checkpoint 日志；任一输入变化使旧结论失效。
- Source refs: `SOUL.md#工作流程`, `AGENTS.md#评审快照锁定`
- Invalidate when: Artifact Graph 或 Review Snapshot 协议正式升级。

### MEM-REV-POL-003 - Rules Are Versioned, Not Improvised

- Status: `active`
- Rule: 阻断只能引用 R-M/R-S/R-E/R-L/R-C/R-G 中带版本的规则；未知或无版本规则不能作为 REVISE/BLOCK 依据。
- Source refs: `SOUL.md#规则集来源与编号`, `agent.yaml#review_policy.rule_namespaces`
- Invalidate when: Rule Registry 命名或版本协议正式升级。

### MEM-REV-POL-004 - Deterministic Rules Are Fully Checked

- Status: `active`
- Rule: Schema、引用、版本、否决项、人工闸口、毛利复算和字段完整性每条必查；UNVERIFIED 项存在时禁止 PASS。
- Source refs: `SOUL.md#审查方式：全检与抽检`, `agent.yaml#review_policy.deterministic_full_checks`
- Invalidate when: Deterministic Rule Set 正式升级。

### MEM-REV-POL-005 - Evidence Sampling Is At Least 20 Percent

- Status: `active`
- Rule: 证据抽检不少于20%，向上取整，并覆盖 Market 痛点、Supply 报价/能力、Economics 假设三个关键域；抽样种子必须可重放。
- Source refs: `SOUL.md#审查方式：全检与抽检`, `agent.yaml#review_policy.evidence_sampling`
- Invalidate when: 基于实测误判成本发布新的抽检政策。

### MEM-REV-POL-006 - One Forgery Expands The Audit

- Status: `active`
- Rule: 抽检发现一例伪造、错配或伪确认时，扩大为全量证据审计；确认伪造可触发 BLOCK。
- Source refs: `SOUL.md#审查方式：全检与抽检`, `agent.yaml#review_policy.evidence_sampling`
- Invalidate when: Evidence Integrity Policy 正式升级。

### MEM-REV-POL-007 - Review Results Have Exact Meanings

- Status: `active`
- Rule: PASS 表示全部通过且无开放事项；PASS_WITH_CONDITIONS 只允许明确人类条件；REVISE 表示可修复；BLOCK 只用于否决项、确认伪造或不可修复结构失败。
- Source refs: `SOUL.md#审查结论分级`, `agent.yaml#review_policy.result_classification`
- Invalidate when: Review Result State Machine 正式升级。

### MEM-REV-POL-008 - Pass With Conditions Is Not Pass

- Status: `active`
- Rule: PASS_WITH_CONDITIONS 在责任人、条件和截止时间满足前不能被 AcceptanceGate 当作 PASS，且不能容纳 Revise/Block 级规则失败。
- Source refs: `SOUL.md#审查结论分级`, `AGENTS.md#结论分级`
- Invalidate when: AcceptanceGate 条件处理协议正式更新。

### MEM-REV-POL-009 - Findings Are Atomic And Repairable

- Status: `active`
- Rule: 每条 Finding 必须绑定一个规则、事实、证据、责任人、修复条件和复审范围；多个责任问题必须拆分。
- Source refs: `SOUL.md#审查原则`, `AGENTS.md#Finding接口`
- Invalidate when: Finding Schema 正式升级。

### MEM-REV-POL-010 - Vetoes And Human Gates Are Independently Rechecked

- Status: `active`
- Rule: Leader 的检查记录不能替代 Reviewer 对认证、FTO、类目权限、禁售、Supply A类否决和强制 Human Checkpoint 的独立复核。
- Source refs: `SOUL.md#一票否决项与人类介入点审计`, `agent.yaml#review_policy.veto_and_human_gate_audit`
- Invalidate when: Veto 或 Human Checkpoint Policy 正式升级。

### MEM-REV-POL-011 - One Block Appeal, Then Human Adjudication

- Status: `active`
- Rule: Leader 可对 BLOCK 附证据异议一次；Reviewer 独立复查后若维持原判，自动升级 Human Manager，不得对同一异议再次阻断。
- Source refs: `SOUL.md#异议处理流程（与Leader对接）`, `agent.yaml#review_policy.appeal`
- Invalidate when: Appeal State Machine 正式升级。

### MEM-REV-POL-012 - Revision Loops Stop At Three

- Status: `active`
- Rule: 同一 root task 最多3轮 REVISE；达到上限或证据物理不可得时，输出双方立场与剩余风险并升级人类。
- Source refs: `SOUL.md#循环计数与升级`, `agent.yaml#review_policy.revision_loop`
- Invalidate when: Revision Budget Policy 正式更新。

### MEM-REV-POL-013 - Reviewer Never Repairs Source Artifacts

- Status: `active`
- Rule: Reviewer 只能读业务 Artifact、写 Review Artifact 和标记评审结果，不能直接修复 Product Spec、Market、Supply 或 Economics 产物。
- Source refs: `SOUL.md#决策权限`, `agent.yaml#hard_constraints`
- Invalidate when: Reviewer 权限矩阵正式修改。

### MEM-REV-POL-014 - Current Findings Stay Out Of Long-Term Memory

- Status: `active`
- Rule: 当前任务 Finding、评审结论和业务内容不得写入长期 Memory；只有至少3个已裁决案例形成的匿名规则校准可以晋升。
- Source refs: `memory.scope#write_gates`, `memory.scope#data_handling`
- Invalidate when: Reviewer Memory Governance 正式更新。

## 4. Active Collaboration Rules

- Reviewer 使用 `REVIEW_FINDING` 同时通知责任 Agent 与 Leader。
- 可修复失败使用 `REVISION_REQUIRED` 让 Leader 创建新 revision。
- 合规或一票否决风险使用 `COMPLIANCE_FLAG` 通知 Leader。
- 人类闸口、证据物理不可得、修订超限和异议终局使用 `HUMAN_DECISION_REQUIRED`。
- BLOCK 异议复用 Leader 已注册的 `DECISION_REQUEST`，并要求 `decision_type=review_appeal`。
- 当前 Leader v1 不接收 Reviewer HANDOFF；Reviewer 通过 Review Artifact 提交与 Task Store SUBMITTED 唤醒 Leader。
- 上线前需要注册 `REVIEW_RESULT` 或扩展 Leader HANDOFF 订阅，消除完成事件不统一的问题。

Sources: `agent.yaml#event_subscriptions`, `agent.yaml#completion_signal`, `AGENTS.md`.

## 5. Accepted Reviewer Knowledge

当前没有规则校准、误判模式、漏判模式、异议结果模式或抽检校准通过 `memory.scope` 的正式晋升门禁。

这意味着：

- Demo 的 `R001-R012 12/12 PASS` 不是新任务的评审先验。
- 旧 Product Spec 的 PASS 不能用于新 hash 或 revision。
- 合成夹具中的规则通过率不能证明真实商业方案可执行。
- 当前没有“某类 Finding 通常可以忽略”的通用结论。
- 每个新任务必须重新锁定快照、执行全检和完成证据抽检。

## 6. Validated Reviewer Calibrations

当前没有动态 Reviewer 校准被晋升为 canonical Knowledge Memory。

可晋升记录必须满足：

- 属于同项目、同规则命名空间和兼容主版本；
- 来源于已 ACCEPTED 的 Review Artifact 与已裁决异议/事故复盘；
- 至少聚合3个独立有效案例，并完成匿名化；
- 具有有效规则 Owner、Leader 或 Human acceptance reference；
- 只保存误判根因类别、规则行为和抽检效果，不保存当前业务内容；
- 包含复核日期、适用范围和失效条件；
- 不能直接修改或覆盖当前 Rule Set。

## 7. Reviewer Memory Record Template

```yaml
memory_id: MEM-REV-CAL-001
version: 1
record_type: false_positive_pattern
project_id: gap2sku
team_id: gap2sku-agentteam
rule_namespace: R-S
rule_major_version: 1
scope_level: exact_project_rule_namespace_major
subject_ref: certification-evidence-scope-mismatch
calibration_facts:
  - fact_id: FACT-001
    pattern_or_calibration: placeholder-overblocking-pattern
    applicable_rule_scope: R-S-certification
    aggregate_observation: placeholder-anonymized-band
    evidence_refs: [accepted-adjudication-summary-ref]
    confidence: medium
    invalidation_conditions: [rule-or-registry-schema-changed]
source_refs: [accepted-appeal-outcome-ref]
sample_profile:
  sample_count: 3
  aggregation: deidentified
validation_status: accepted
evidence_confidence: medium
data_mode: live
owner: gap2sku-reviewer
status: active
valid_from: 2026-08-06
review_after: 2027-02-02
invalidation_conditions: [rule-major-version-changed]
human_adjudication_ref: human-review-calibration-v1
created_at: 2026-08-06T00:00:00+08:00
```

这是字段模板，不是有效校准。占位值、少于3个案例、未裁决异议或包含当前业务内容的记录必须被写入门禁拒绝。

## 8. Open Reviewer-Memory Questions

| ID | Question | Impact | Required resolution |
| --- | --- | --- | --- |
| ROQ-001 | R-M/R-S/R-E/R-L/R-C/R-G 规则注册表存放在哪里？ | Reviewer 无法锁定权威规则版本 | 建立 Rule Registry、Owner 和发布流程 |
| ROQ-002 | V1 没有独立 Compliance Agent，R-C 规则由谁维护？ | 合规规则可能失去责任主体 | 指定 Reviewer/Leader 的临时 Owner 与升级计划 |
| ROQ-003 | 证据抽样使用什么可重放随机算法？ | 20%抽检无法稳定复现 | 固化种子、分层与抽样实现 |
| ROQ-004 | AcceptanceGate 如何处理 PASS_WITH_CONDITIONS？ | 条件未满足可能被误当 PASS | 实现条件状态、责任人、截止时间和解除门禁 |
| ROQ-005 | 是否新增 REVIEW_RESULT 事件？ | Reviewer 成功完成依赖 Artifact 触发而非统一事件 | 注册事件或扩展 Leader HANDOFF 订阅 |
| ROQ-006 | BLOCK 异议如何提交和展示新增证据？ | 异议可能退化成聊天争论 | 实现 DECISION_REQUEST appeal Schema 和审计 UI |
| ROQ-007 | 如何识别与确认 false negative？ | Reviewer 只看到已发现问题，漏判难校准 | 建立上线后事故与退货复盘回流 |
| ROQ-008 | 谁批准 Reviewer Calibration 晋升 Memory？ | 误判经验无法通过写入门禁 | 指定 Rule Owner、Leader 与 Human 审批矩阵 |
| ROQ-009 | Review Memory Record Schema 存放在哪里？ | 校准记忆无法确定性校验 | 创建 Schema 并纳入 CI 回归 |
| ROQ-010 | 误判成本和抽检成本如何量化？ | 无法优化20%抽检基线 | 定义错误PASS、错误BLOCK、时延与调用成本指标 |

未决问题不能作为当前规则，也不能支持 PASS/BLOCK。

## 9. Superseded Or Invalidated Records

Bootstrap 版本暂无记录。

旧校准不能通过删除隐藏变化。必须新增版本，将旧记录标记为 `superseded` 或 `invalidated`，并保留变化原因、来源和规则影响。

## 10. Maintenance Rules

- 本投影保持在250行以内。
- 不粘贴当前 Finding、Review Report、Product Spec、报价、评论、利润或完整 Artifact。
- 不保存 API Key、凭据、个人数据、隐藏推理和未裁决伪造指控。
- 规则校准至少聚合3个已裁决案例，并只保留匿名模式。
- 抽检校准每90天复核；规则、误判和异议模式每180天复核。
- 每次评审仍须使用当前规则集、锁定快照和确定性工具。
- 只有 canonical Memory Store 发生已验收变更后才刷新本投影。
- 本投影与 Memory Store 冲突时，以 Memory Store 为准并重新生成。
