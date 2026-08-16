# rubrics.md - gap2sku-product-architect

> Rubric version: 1.0.0  
> Applies to: `gap2sku-product-architect`  
> Primary evaluators: `gap2sku-reviewer`, Leader self-check, AcceptanceGate  
> Contract references: `agent.yaml`, `AGENTS.md`, `SOUL.md`

本文档定义 Leader 的任务规划、跨 Agent 协作、ProductSpec 整合和决策产物达到什么标准才算合格。评分不能替代 Schema 校验、Reviewer 结论、Human Checkpoint 或 AcceptanceGate。

## 1. 结论边界

以下结论含义不同，不得混用：

| 结论 | 唯一责任方 | 含义 |
| --- | --- | --- |
| `PASS` / `BLOCK` | Reviewer | 当前 revision 是否通过独立评审 |
| `ACCEPTED` | AcceptanceGate | 当前任务是否满足系统验收条件 |
| `GO` / `REVISE` / `NO_GO` / `UNDECIDED` | Leader 在 DecisionRecord 中提出，Human Manager 最终决定 | 商业推进建议 |

Leader 自评只能输出 `SELF_CHECK_PASS` 或 `SELF_CHECK_FAIL`，不能自行输出 Reviewer PASS，也不能把任务标记为 ACCEPTED。

## 2. 评估顺序

评估必须按以下顺序执行：

1. 校验任务、事件和全部必需 Artifact 的 Schema。
2. 执行硬性门禁 G01-G12。
3. 若存在可修复门禁失败，停止计分；Reviewer 返回 `BLOCK` 并发出 `REVISION_REQUIRED`。
4. 若存在不可修复或触发一票否决的失败，Reviewer 返回 `BLOCK`，Leader 形成 `NO_GO` 建议或请求 Human Manager 决策。
5. 全部门禁通过后，执行 100 分质量评分。
6. 检查缺项、常见错误模式和缺陷等级。
7. 输出结构化评估结果和下一步动作。

不得用总分抵消硬性门禁失败。

## 3. 硬性门禁

| ID | 门禁 | 通过条件 | 失败处理 |
| --- | --- | --- | --- |
| G01 | 任务契约有效 | `task_id`、`revision`、目标市场、业务目标、约束引用、必需产物和审批要求齐全 | 缺失可补充时 `REVISE` |
| G02 | 输入合法 | 所有输入 Artifact 存在、Schema 合法、版本正确、状态为 accepted/valid，且没有未解释的 stale | 标记受影响节点，生成 ImpactPlan 后 `REVISE` |
| G03 | 证据可追溯 | ProductSpec 和 DecisionRecord 的关键事实均可追溯到 `artifact_refs` 与 `evidence_refs` | 关键结论无证据时 `BLOCK` |
| G04 | 数据模式透明 | 每组关键证据标明 `data_mode`、来源时间、适用市场和 `confidence`；合成数据不得表述为真实市场事实 | 误导性表述 `BLOCK`，普通缺标 `REVISE` |
| G05 | 硬约束已检查 | 价格、成本、MOQ、交期、尺寸、开模、合规及任务特定红线均有检查结果 | 违反硬约束且无已批准例外时 `BLOCK` |
| G06 | 职责隔离 | Market、Supply、Economics、Reviewer 的专业结论由对应责任 Agent 产出；Leader 未伪造、改写或代替其 Artifact | 越权产物作废并 `BLOCK` |
| G07 | Artifact Graph 一致 | 依赖边、版本、hash、supersedes 和失效传播完整；Review 的 `spec_hash` 与当前 ProductSpec 一致 | 生成 ImpactPlan 并 `REVISE` |
| G08 | 冲突已决策 | 跨 Agent 冲突有 DecisionRecord 或 Human Decision，且保留双方原始证据与取舍理由 | 未处理冲突时 `REVISE` |
| G09 | 风险没有隐藏 | 合规、供应、利润、证据质量和执行风险均进入 RiskRegister，包含等级、责任方、缓解和升级条件 | 严重风险被隐藏或降级时 `BLOCK` |
| G10 | Human Checkpoint 完成 | 命中的 CP-01 至 CP-07 均有有效 `HUMAN_DECISION`；human_hold 已按规则释放 | 保持 human_hold，不得继续验收 |
| G11 | 评审提交包完整 | 包含 ProductSpec、DecisionRecord、Constraints、关键输入引用、当前 `spec_hash`、数据模式和置信度分布 | 缺失时不启动正式评审，返回 `REVISION_REQUIRED` |
| G12 | 非 partial 模式 | 必需依赖齐全，`output_mode` 不是 partial | partial 只能输出 `REVISE` 或 `NO_GO`，禁止验收 |

## 4. 100 分质量评分

### A. 任务规划与依赖设计 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| A1 | 目标与约束转译 | 4 | 将业务目标转成可验证目标，明确 must-have、可协商项和一票否决项 |
| A2 | 子任务边界 | 4 | 每个任务有唯一责任 Agent、输入引用、预期产物和验收标准，无职责重叠 |
| A3 | DAG 与依赖 | 4 | 并行、串行和阻塞关系正确，Economics 不在有效成本和价格信号前启动 |
| A4 | 变更规划 | 3 | 变更前生成 ImpactPlan，仅重跑受影响子图并说明保留节点 |

扣分规则：部分满足得该项 50%；缺失、矛盾或不可执行得 0 分。若依赖错误导致使用旧数据，除扣分外触发 G02/G07。

### B. Artifact 质量与证据追溯 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| B1 | 输入验收 | 4 | 只整合通过各自 rubrics 且 accepted/valid 的 Worker Artifact |
| B2 | 引用完整 | 5 | 关键规格、成本、价格、功能和风险均有精确 Artifact 与 Evidence 引用 |
| B3 | 版本一致 | 4 | revision、hash、supersedes、时间和来源快照一致，无静默覆盖 |
| B4 | 数据质量披露 | 4 | 真实、合成、缓存或推断数据明确区分，并披露样本量、时效和局限 |
| B5 | 可重建性 | 3 | 可通过 `task_id + revision + artifact_refs` 重建当前结论 |

### C. 多 Agent 协作与冲突解决 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| C1 | 派发协议 | 3 | 所有派发使用 TASK_ASSIGNMENT，字段完整，责任与截止条件明确 |
| C2 | 事件协作 | 3 | 协作使用事件信封，状态变化写入 TaskStore/Artifact Graph，不依赖聊天文本改变状态 |
| C3 | 冲突分类 | 4 | 能区分事实冲突、约束冲突、商业取舍、版本冲突和评审失败 |
| C4 | 决策闭环 | 3 | 冲突有证据、备选方案、取舍、责任人和下游影响，不以简单平均替代判断 |
| C5 | 完成通知 | 2 | Worker、Leader 和 Human 的完成/阻塞/需决策状态可被主动发现并审计 |

### D. ProductSpec 整合质量 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| D1 | 用户与定位 | 3 | 目标用户、场景、核心痛点、价值主张和价格带一致 |
| D2 | 功能决策 | 4 | 每项核心功能连接痛点证据、实现方式、供应可行性、成本影响和优先级 |
| D3 | 关键规格 | 4 | 尺寸、材料、性能、包装、质量及验证方法可执行，无模糊形容词替代指标 |
| D4 | 供应方案 | 3 | 供应商选择、MOQ、交期、开模、备选方案和风险与 Supply Artifact 一致 |
| D5 | 利润模型 | 3 | 售价、成本堆叠、平台费用、营销、物流、损耗、毛利和敏感性与 Economics 一致 |
| D6 | 一致性 | 3 | 定位、功能、供应、利润和风险之间无未解释矛盾 |

### E. 决策质量 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| E1 | 推荐明确 | 3 | `GO/REVISE/NO_GO/UNDECIDED` 与当前证据和权限一致 |
| E2 | 备选方案 | 4 | 至少两个现实可执行选项；被排除方案有证据化理由 |
| E3 | 假设与失效条件 | 3 | 关键假设、验证办法、失效阈值和触发后的动作明确 |
| E4 | 一票否决检查 | 3 | 每项 veto 有 PASS/FAIL/UNKNOWN、证据和责任人 |
| E5 | 下游影响 | 2 | 决策对功能、供应、利润、合规、时间和评审的影响完整 |

### F. 风险、合规与人类介入 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| F1 | 风险登记 | 3 | 风险包含概率、影响、等级、owner、缓解措施和升级条件 |
| F2 | 合规处理 | 3 | 敏感品类和不确定合规项没有被降级，已路由对应检查与 Human Manager |
| F3 | Checkpoint 执行 | 2 | CP-01 至 CP-07 的命中、通知、决定和释放记录完整 |
| F4 | 人类决策材料 | 2 | DecisionBrief 能让 Manager 看清推荐、证据、风险、未确认项和审批动作 |

### G. 效率与可观测性 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| O1 | 预算控制 | 2 | token、工具调用、耗时、子任务和 revision 未超限；80% 时正确触发预警 |
| O2 | 局部重跑 | 1 | 变更只重跑受影响节点，保留有效 Artifact |
| O3 | 审计完整 | 2 | 每个 tick、事件、工具调用、状态转换、版本和 checkpoint 都可查询 |

## 5. 分数与处理结果

分数只在 G01-G12 全部通过后计算。

| 总分 | 质量结论 | 必须动作 |
| ---: | --- | --- |
| 90-100 | 优秀 | Reviewer 可返回 `PASS`；满足其他门禁后可进入 AcceptanceGate |
| 85-89 | 合格 | Reviewer 可返回 `PASS`，同时记录非阻塞改进项 |
| 70-84 | 不合格 | Reviewer 返回 `BLOCK` 并发出 `REVISION_REQUIRED`，Leader 创建新 revision |
| 0-69 | 严重不合格 | Reviewer 返回 `BLOCK`；若存在不可修复商业或约束冲突，Leader 形成 `NO_GO` 建议 |

进入 AcceptanceGate 的最低条件：

- G01-G12 全部通过。
- 总分不低于 85。
- 没有未关闭的 critical 或 major 缺陷。
- Reviewer 对当前 `spec_hash` 返回 PASS。
- 所有 Human Checkpoint 已处理。
- 当前输出不是 partial。

## 6. Artifact 缺项清单

评估前逐项检查：

### 6.1 输入 Artifact

- `task-contract`
- `demand-structure`
- `pain-point-set`
- `competitor-gap-map`
- `feature-hypotheses`
- `supplier-assessment`
- `supplier-screening-matrix`
- `manufacturability-feedback`
- `supply-risk-register`
- `unit-economics`
- `cost-stack`
- `sensitivity-analysis`
- `compliance-risk-report`，适用时必需
- 当前 revision 的 `review-report` 与 `review-findings`

### 6.2 Leader 输出 Artifact

- `task-plan`
- `product-spec`
- `decision-record`
- `risk-register`
- `open-questions`
- `impact-plan`，发生变更、失效或局部重跑时必需
- `decision-brief`

缺少非适用 Artifact 时必须给出 `not_applicable_reason`。只写“不需要”不算有效理由。

## 7. 缺陷等级

| 等级 | 定义 | 示例 | 处理 |
| --- | --- | --- | --- |
| critical | 可能造成违法、资金损失、错误生产或系统越权 | 合规红线被忽略；使用错误成本后仍建议 GO；Leader 自行 ACCEPT | Reviewer `BLOCK`，立即停止 |
| major | 会显著改变产品、供应或利润决策 | 核心功能无证据；供应报价 stale；Review hash 不一致 | `REVISE`，新 revision 复核 |
| minor | 不改变主要决策但降低可读性或审计质量 | 次要字段说明不足；非关键引用格式不统一 | 修复后可继续，不得累计隐藏 |

任一 critical 或未关闭 major 缺陷都禁止进入 AcceptanceGate。

## 8. 常见错误模式

- 用聊天消息或模型总结替代 Artifact Store 中的正式产物。
- 把 Worker 的 `SUBMITTED` 当成 accepted/valid。
- Leader 直接修改 Worker Artifact，而不是退回责任 Agent 新建版本。
- 市场需求强就忽略供应、利润或合规红线。
- 供应可做就默认市场愿意购买。
- 只给一个方案，却声称完成了取舍分析。
- 对冲突结论取平均值，而不判断证据质量和适用范围。
- 用合成数据得出真实采购、销量或供应商承诺。
- ProductSpec 已更新，但继续沿用旧 `spec_hash` 的 Reviewer PASS。
- 成本变化后整条流水线重跑，或完全不失效下游 Artifact。
- 缺少数据时由模型补值，并把推断写成事实。
- 预算或 revision 达到上限后继续执行。
- Human Checkpoint 命中后仍继续派发或整合。
- Reviewer BLOCK 后申诉、覆盖结果或直接改成 PASS。
- DecisionBrief 只展示推荐，不展示风险、未决项和审批动作。

## 9. 评估输出格式

Reviewer 或 Leader 自检必须输出以下结构，不得只返回一个分数：

```yaml
rubric_version: 1.0.0
task_id: laptop-stand-us-20260803-001
revision: 1
evaluator: gap2sku-reviewer
evaluated_artifact_refs:
  - product-spec-v1
  - decision-record-v1
gate_results:
  G01: {status: PASS, evidence_refs: [task-contract-v1]}
  G02: {status: PASS, evidence_refs: [artifact-graph-snapshot-v3]}
  G03: {status: FAIL, evidence_refs: [], reason: core_feature_missing_evidence}
score:
  task_planning: 13
  artifact_traceability: 15
  collaboration: 12
  product_spec: 17
  decision_quality: 12
  risk_and_human: 8
  efficiency_observability: 4
  total: 81
defects:
  - id: DEF-001
    severity: major
    criterion: B2
    artifact_ref: product-spec-v1
    finding: FH-003 没有 evidence_ref
    owner: gap2sku-market
    required_action: 补充证据或移除该核心功能
result: BLOCK
acceptance_gate_eligible: false
next_actions:
  - event_type: REVISION_REQUIRED
    target_agent: gap2sku-product-architect
    reason: unresolved_major_defect
```

若任一门禁失败，`acceptance_gate_eligible` 必须为 `false`。评估结果必须与当前 `task_id`、`revision` 和 `spec_hash` 绑定。

## 10. Leader 提交前自检

Leader 在提交 Reviewer 前必须逐项回答：

1. 我是否只整合了 accepted/valid 且未 stale 的 Artifact？
2. 每个核心功能是否同时连接用户证据、供应实现和成本影响？
3. 当前售价是否同时有市场价格信号和 Economics 验算？
4. 所有关键结论是否能定位到 evidence_ref，而不是仅引用 Agent 总结？
5. 我是否保留了冲突双方原始证据，并形成可审计取舍？
6. 是否存在被我弱化、隐藏或遗漏的风险与 UNKNOWN？
7. 当前 ProductSpec 与 Reviewer 将收到的 `spec_hash` 是否一致？
8. 是否命中任何 Human Checkpoint，且已获得有效决定？
9. 当前输出是否为 partial；若是，是否已禁止 GO 与 AcceptanceGate？
10. 我是否给 Human Manager 提供了可以直接作决定的一页 DecisionBrief？

任一回答为“否”或“未知”，不得发送 `submit_to_reviewer`。
