# MEMORY.md - gap2sku-economics

> Projection version: 1.0.0  
> Agent ID: `gap2sku-economics`  
> Canonical source: Gap2SKU Memory Store  
> Access policy: `memory.scope`  
> Last refreshed: 2026-08-06

本文件是 Economics 长期记忆的人工可读投影，用于快速恢复稳定规则、已验收校准和未决问题。它不是财务账簿、报价表、任务状态或当前经济模型，不能替代 Task Contract、Economics Artifact 和确定性计算器。

## 1. 使用边界

- 当前有效的 Task Contract、费率、成本和市场证据优先于本文件。
- `MEMORY.md` 不授予新的事件、Skill、工具、状态或最终决策权限。
- 当前任务售价、成本、毛利、利润、损失和现金占用只存在 Artifact Store。
- 历史校准只是先验区间，不能跳过当前输入核验和确定性重算。
- 单个项目结果不能晋升为通用校准；经验校准至少需要 3 个已验收真实样本。
- 本文件与 Memory Store 冲突时，以 Memory Store 为准并重新生成本文件。
- Economics 不得直接覆盖本文件；只有通过 `memory.scope` 门禁的记录才能刷新投影。

## 2. 当前运行身份

- Agent: `gap2sku-economics`
- Role: Unit economics and commercial-risk specialist Worker
- Reports to: `gap2sku-product-architect`
- Owns: 成本口径、确定性核算、毛利红线、三档情景、盈亏平衡、回本、最坏损失与现金占用。
- Does not own: 市场需求、供应商真实性、最终功能、采购付款及最终 GO/NO-GO。
- Required outputs: `unit-economics`、`cost-stack`、`sensitivity-analysis`、`pricing-viability-report`、`economics-risk-register`。

Sources: `SOUL.md`, `AGENTS.md`, `agent.yaml`.

## 3. Active Economics Policies

### MEM-ECO-POL-001 - Deterministic Verification Is Mandatory

- Status: `active`
- Rule: LLM 可以解释和提出方案，但所有金额、比例、盈亏平衡、回本、损失与情景结果必须由确定性工具计算并校验。
- Source refs: `SOUL.md#计算与证据原则`, `agent.yaml#economics_policy.formula_contract`
- Invalidate when: 计算引擎或公式契约正式升级。

### MEM-ECO-POL-002 - Every Cost Category Gets A Status

- Status: `active`
- Rule: 每个成本类别必须标记 confirmed、estimated、not_applicable 或 missing；缺失不能静默填零，不适用必须给原因。
- Source refs: `SOUL.md#成本堆叠清单`, `AGENTS.md#成本堆叠接口`
- Invalidate when: Cost Stack Schema 正式升级。

### MEM-ECO-POL-003 - Estimated Inputs Need A Failure Threshold

- Status: `active`
- Rule: 估算输入必须包含依据、区间、置信度、生效时间和失效阈值；关键输入缺失时只能 partial，不能给无条件盈利结论。
- Source refs: `SOUL.md#计算与证据原则`, `agent.yaml#economics_policy.input_status`
- Invalidate when: 经济输入契约正式升级。

### MEM-ECO-POL-004 - Margin Redline Is A Contract, Not A Preference

- Status: `active`
- Rule: 默认毛利率红线为30%；25%-30%属于观察区，需要 Human Manager 特批；低于25%必须给 NO-GO 建议。Market 痛点不能覆盖红线。
- Source refs: `SOUL.md#红线与决策输出`, `agent.yaml#economics_policy.margin_redline`
- Invalidate when: Task Contract 或 Human Manager 正式更新红线政策。

### MEM-ECO-POL-005 - Three Scenarios Use Fixed Definitions

- Status: `active`
- Rule: 每次必须计算基准、保守、压力情景；压力情景同时施加实现售价-10%、工厂成本+10%、退货率翻倍和旺季附加费。
- Source refs: `SOUL.md#情景定义（三档，口径固定）`, `agent.yaml#economics_policy.scenarios`
- Invalidate when: Scenario Schema 正式升级。

### MEM-ECO-POL-006 - Quoted Supply Cost Requires Extra Buffer

- Status: `active`
- Rule: Supply 成本只有 `quoted` 级、尚未样品验证时，Economics 增加5%成本缓冲并降低结论置信度。
- Source refs: `SOUL.md#异常与降级`, `agent.yaml#economics_policy.margin_redline`
- Invalidate when: 供应验证等级或缓冲政策正式更新。

### MEM-ECO-POL-007 - New Launch Advertising Uses Per-Order Cost

- Status: `active`
- Rule: 新品期使用单均广告成本建模，不能直接套成熟 listing 的 ACoS；参考压力区间为售价的30%-50%，实际值仍需当前证据。
- Source refs: `SOUL.md#关键假设审计（最脆弱假设清单）`, `agent.yaml#economics_policy.assumption_audit`
- Invalidate when: 广告建模政策或渠道阶段定义更新。

### MEM-ECO-POL-008 - Return Rate Uses The Higher Supported Value

- Status: `active`
- Rule: 退货率取类目均值与 Market 退货证据中的较高者，敏感类目必须额外加压。
- Source refs: `SOUL.md#关键假设审计（最脆弱假设清单）`, `agent.yaml#economics_policy.assumption_audit`
- Invalidate when: 退货风险模型正式升级。

### MEM-ECO-POL-009 - List Price Is Not Realized Price

- Status: `active`
- Rule: 实现售价必须根据促销频率、折扣和销售调整从标价折算；价格上限不等于用户一定接受。
- Source refs: `SOUL.md#关键假设审计（最脆弱假设清单）`, `AGENTS.md#与Market协作`
- Invalidate when: Pricing Viability Schema 正式升级。

### MEM-ECO-POL-010 - Profitability Is A Recommendation Class

- Status: `active`
- Rule: Economics 可输出 profitable、conditionally_profitable、revise 或 no_go_recommendation，但最终 GO/NO-GO 属于 Leader 与 Human Manager，禁止保证盈利。
- Source refs: `SOUL.md#决策权限`, `AGENTS.md#毛利红线与决策权限`
- Invalidate when: 决策权限矩阵正式修改。

### MEM-ECO-POL-011 - Input Changes Invalidate Downstream Results

- Status: `active`
- Rule: 供应成本、包装档、物流、平台费率、汇率、售价、促销、CPC、退货率、销量假设或公式版本变化时，必须新建 Economics 版本并声明 ProductSpec 与 Review 等失效范围。
- Source refs: `SOUL.md#必须主动协作的情形`, `AGENTS.md#Artifact版本规则`
- Invalidate when: Artifact Graph 失效协议正式升级。

### MEM-ECO-POL-012 - Absolute Task Economics Stay Out Of Memory

- Status: `active`
- Rule: 当前任务的绝对售价、成本、毛利、利润、损失与现金占用不得写入长期 Memory；只允许至少3个真实项目形成的匿名偏差区间。
- Source refs: `memory.scope#write_gates`, `memory.scope#data_handling`
- Invalidate when: 商业数据分级与记忆治理政策正式更新。

## 4. Active Collaboration Rules

- Economics 通过 `COST_CLARIFICATION_REQUEST` 请求 Supply 补齐成本口径，并同步 Leader。
- Economics 通过 `PRICE_VIABILITY_REQUEST` 请求 Leader 路由 Market 补充价格、促销、CPC 和用户价格证据。
- Supply 的 `COST_UPDATE` 会使旧 Economics 结论失效，只重算受影响子图。
- 毛利、压力情景或现金风险超过边界时，Economics 发送 `RISK_ALERT` 给 Leader。
- `INSUFFICIENT_EVIDENCE` 统一映射为 `NEEDS_EVIDENCE`。
- Reviewer Finding 创建新 Economics revision；旧结果不得覆盖。
- Economics 通过 `HANDOFF` 提交，不能将自己的 Artifact 标记为 ACCEPTED。

Sources: `agent.yaml#event_subscriptions`, `agent.yaml#event_emissions`, `AGENTS.md`.

## 5. Accepted Economics Knowledge

当前没有估算偏差、退货率、广告成本、物流成本、促销实现率或平台费率记录通过 `memory.scope` 的正式晋升门禁。

这意味着：

- Demo 中 `$7.00` 工厂成本、`$39.99` 售价和 `45%` 毛利率不是可复用商业事实。
- 合成夹具的运费、平台费、广告费和退货率不能用于真实项目。
- 当前没有“该品类通常能赚多少”的通用结论。
- 当前没有任何历史校准可以替代实时费率、报价与市场证据。
- 每个真实项目都必须按当前输入重新确定性计算。

## 6. Validated Reusable Calibrations

当前没有动态经济校准被晋升为 canonical Knowledge Memory。

可晋升校准必须满足：

- 属于同项目、同品类、同市场和同渠道；
- 来源于已 ACCEPTED 的 Economics Artifact 与真实实际结果；
- 至少聚合 3 个有效项目，并完成匿名化；
- 只保存偏差比例或区间，不保存单个任务绝对商业数值；
- 具有有效 Leader acceptance reference；
- 包含样本画像、复核日期与失效条件；
- 当前任务仍需重新核验并通过确定性计算。

## 7. Economics Memory Record Template

```yaml
memory_id: MEM-ECO-CAL-001
version: 1
record_type: advertising_cost_calibration
project_id: gap2sku
team_id: gap2sku-agentteam
category_id: category-id
market: US
channel: amazon
scope_level: exact_category_market_channel
subject_ref: new-launch/per-order-ad-cost
calibration_or_policy_facts:
  - fact_id: FACT-001
    metric_name: estimate_to_actual_ratio
    aggregate_ratio_or_band: [placeholder-lower, placeholder-upper]
    applicable_stage_or_scope: first-90-days
    evidence_refs: [accepted-aggregate-calibration-ref]
    confidence: medium
    invalidation_conditions: [channel-ad-policy-or-bidding-model-changed]
source_refs: [accepted-estimate-ref, accepted-actual-ref]
sample_profile:
  sample_count: 3
  aggregation: deidentified
validation_status: accepted
evidence_confidence: medium
data_mode: live
owner: gap2sku-economics
status: active
valid_from: 2026-08-06
review_after: 2026-11-04
invalidation_conditions: [sample-invalid-or-channel-policy-changed]
leader_acceptance_ref: economics-calibration-acceptance-v1
created_at: 2026-08-06T00:00:00+08:00
```

这是字段模板，不是有效校准记录。占位值、少于3个样本、缺少真实结果或包含绝对商业数据的记录必须被写入门禁拒绝。

## 8. Open Economics-Memory Questions

| ID | Question | Impact | Required resolution |
| --- | --- | --- | --- |
| EOQ-001 | 第一批真实项目的估算与实际数据从哪里取得？ | 无法建立经济校准闭环 | 批准订单、广告、物流和退货数据接入方案 |
| EOQ-002 | 如何定义“实际结果已验收”？ | 估算偏差记录无法通过门禁 | 发布 actual-result Schema 与验收责任人 |
| EOQ-003 | 平台费率接入哪个权威版本源？ | 佣金、配送和仓储可能过期 | 接入有效日期和版本可查的费率源 |
| EOQ-004 | 汇率、物流与关税的更新频率是多少？ | 压力情景可能使用失真输入 | 定义刷新 SLA、备用源和 STALE 规则 |
| EOQ-005 | 新品期广告成本如何按阶段校准？ | 直接使用成熟 ACoS 会高估利润 | 定义冷启动阶段和单均广告成本口径 |
| EOQ-006 | 最坏损失和回本周期采用什么现金流公式？ | 团队可能使用不同口径 | 固化 economics-formula-v1 并建立 golden tests |
| EOQ-007 | 谁批准经验校准从 Artifact 晋升为 Memory？ | 记忆写入无法通过授权门禁 | 实现 Leader acceptance reference |
| EOQ-008 | Economics Memory Record Schema 存放在哪里？ | 记忆无法确定性校验 | 创建 Schema 并纳入 CI 回归 |
| EOQ-009 | 商业敏感数据如何聚合与脱敏？ | 可能泄露单项目价格和利润 | 制定最小样本、区间化和访问审计策略 |
| EOQ-010 | Artifact 失效如何自动标记相关经济校准？ | 旧公式或错误实际值可能继续被使用 | 接通 Artifact Graph 与 Memory Store |

未决问题不能作为经济输入，也不能支持 ProductSpec 的利润结论。

## 9. Superseded Or Invalidated Records

Bootstrap 版本暂无记录。

旧记录不能通过删除隐藏变化。必须新增版本，将旧记录标记为 `superseded` 或 `invalidated`，并保留变化原因、来源和下游影响。

## 10. Maintenance Rules

- 本投影保持在 250 行以内。
- 不粘贴当前报价、售价、毛利、利润、损失、现金占用、订单或完整 Artifact。
- 不保存 API Key、凭据、个人数据、银行和付款信息。
- 经验校准至少聚合3个已验收真实项目，并只保留匿名比例或区间。
- 广告、物流、退货和促销校准每90天复核；估算偏差每180天复核。
- 平台费率引用每30天检查一次，并以权威当前版本优先。
- 每次使用历史校准后仍须根据当前输入重新确定性计算。
- 只有 canonical Memory Store 发生已验收变更后才刷新本投影。
- 本投影与 Memory Store 冲突时，以 Memory Store 为准并重新生成。
