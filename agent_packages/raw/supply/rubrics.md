# rubrics.md - gap2sku-supply

> Rubric version: 1.0.0  
> Applies to: `gap2sku-supply`  
> Primary evaluators: Supply self-check, Leader, Reviewer  
> Contract references: `agent.yaml`, `AGENTS.md`, `SOUL.md`

本文档定义 Supply 的可制造性结论、供应商筛选、报价、质量与风险产物达到什么标准才算合格。高分不能抵消 A 类否决项遗漏、虚假验证等级、过期报价、无备选供应商或关键证据不可追溯。

## 1. 结论与权限边界

| 结论 | 责任方 | 含义 |
| --- | --- | --- |
| `SELF_CHECK_PASS` / `SELF_CHECK_FAIL` | Supply | Supply 对本次产物的提交前自检 |
| `REVISE` | Leader | Supply 需要补证、重新询价、补充打样或形成新版本 |
| `BLOCK` | Reviewer | 当前项目 revision 存在不能进入后续决策的严重缺陷 |
| `ACCEPTED` | AcceptanceGate | Supply Artifact 满足系统验收条件 |
| `CONDITIONAL_FEASIBLE` | Supply 建议，Leader 决策 | 当前证据仅支持带前提的可行性结论 |
| `CONSTRAINT_VIOLATION` | Supply 发出，Leader 处理 | 供应事实违反硬约束，需要谈判、替代、修订或停止 |

Supply 不得将高评分解释为产品已经量产就绪、一定盈利、市场一定成立或项目已经 GO。

## 2. 评估顺序

1. 校验 Task Contract、商业口径、事件与五类提交 Artifact 的 Schema。
2. 执行硬性门禁 SG01-SG14。
3. 任一门禁失败时停止正式计分，输出缺陷、责任方和整改动作。
4. 可修复问题返回 Leader `REVISE`；伪造证据、绕过 A 类否决或重大越权可触发 Reviewer `BLOCK`。
5. 全部门禁通过后执行 100 分质量评分。
6. 检查缺项、缺陷等级、单一来源依赖和常见错误模式。
7. 输出结构化评估结果，并绑定 `task_id + revision + artifact_refs`。

## 3. 硬性门禁

| ID | 门禁 | 通过条件 | 失败处理 |
| --- | --- | --- | --- |
| SG01 | 任务与比较口径明确 | 市场、品类、渠道、销售窗口、规格、数量梯度、币种、贸易条款、包装口径和约束引用齐全 | 返回 Leader 补充 Task Contract |
| SG02 | 数据来源获准 | 每个来源在允许范围内，记录来源引用、采集或确认时间及使用权限 | 未授权数据不得进入产物 |
| SG03 | 供应证据可追溯 | 每项关键能力、报价、认证、样品和淘汰结论都带 `evidence_id` | 关键结论无证据时 `BLOCK` |
| SG04 | 数据模式与验证等级真实 | live/cached/synthetic/mixed 和 platform_visible/quoted/sample_verified/factory_confirmed 与事实一致 | 冒充 live 或夸大验证等级时 `BLOCK` |
| SG05 | A 类否决逐项完成 | 每个候选均检查材料、强制认证与第三方抽检配合；失败项已淘汰 | 漏检或以价格覆盖否决时 `BLOCK` |
| SG06 | B 类约束有处理路径 | MOQ、成本、常规交期和模具均有通过、失败或待确认状态；失败项附交换条件 | 缺少谈判路径时 `REVISE` |
| SG07 | 报价标准化且有效 | 币种、数量、贸易条款、包装、模具、认证、税费和附加费口径统一；关键报价不超过30天 | STALE 或不可比报价作为关键依据时 `REVISE` |
| SG08 | 供应商漏斗真实 | 披露候选、初筛、打样和终选实际数量；覆盖不足时进入 partial 或登记集中风险 | 虚构候选或单报价直推时 `BLOCK` |
| SG09 | 核心功能全部完成可制造性分类 | 每项核心功能均标记现有工艺、改模、新开模或不可行，并附依据与替代方案 | 有核心功能未评估时 `REVISE` |
| SG10 | 主备供应方案完整 | 至少 1 主 1 备，且两者均有范围匹配的有效证据 | 暂缺备选时只能提交 partial，并登记单一来源风险、补齐动作和 Human Checkpoint；隐瞒风险时 `BLOCK` |
| SG11 | 样品与大货风险已处理 | 样品状态、测试标准、产前样、同产线同材料标准和第三方验货配合均明确 | 将样品通过写成量产确认时 `BLOCK` |
| SG12 | 包装、运输与认证前检完成 | 包装费用档、破损风险、强磁/电池/液体/粉末运输属性及适用认证已核验或正确升级 | 适用项静默跳过时 `REVISE` 或 `BLOCK` |
| SG13 | 下游交接与角色边界正确 | 有效成本版本已发送 Economics/Leader；没有用户需求、利润、最终价格或 GO 结论 | 越权结论作废，严重时 `BLOCK` |
| SG14 | 版本与提交包完整 | 五类 Artifact 均存在且 Schema 合法，task/revision/hash/supersedes 一致；partial 缺口完整披露 | 不完整时不得 SELF_CHECK_PASS |

硬门禁失败不能通过提高其他评分项分数补偿。

## 4. 100 分质量评分

### A. 任务范围与数据治理 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| A1 | 任务范围 | 3 | 市场、渠道、规格、销售窗口和硬约束清晰一致 |
| A2 | 商业比较口径 | 3 | 币种、数量梯度、贸易条款、包装和附加费定义完整 |
| A3 | 来源与权限 | 2 | 来源清单、使用权限、快照和确认时间可审计 |
| A4 | 数据模式 | 2 | source_type、data_mode 和验证等级正确，无误导标注 |

### B. 供应证据与尽调 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| B1 | 证据覆盖 | 5 | 所有关键结论均有 evidence_id，无 unsupported claim |
| B2 | 身份与工厂属性 | 3 | 营业信息、工厂/贸易商身份、车间或产线证据可核验 |
| B3 | 验证等级 | 4 | 每条能力和报价的验证等级与证据一致，未夸大确认状态 |
| B4 | 时效性 | 3 | 报价和能力证据新鲜度完整，STALE 数据正确降级 |
| B5 | 认证核验 | 3 | 强制认证编号、范围、有效期和发证机构引用可查 |
| B6 | 反证与冲突 | 2 | 低价异常、能力冲突、质量事故和未知项未被隐藏 |

### C. 可制造性与约束判断 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| C1 | 功能拆解 | 4 | 核心功能完整拆为材料、工艺、结构、模具、认证和运输要求 |
| C2 | 四档分类 | 4 | 每项功能准确标记现有工艺、改模、新开模或不可行 |
| C3 | A 类否决 | 5 | 每个候选逐项核验，否决依据充分且未被商业条件覆盖 |
| C4 | B 类约束 | 3 | MOQ、成本、交期和模具差距清晰，谈判边界明确 |
| C5 | 替代方案 | 4 | 每项否决或超约束均有可执行替代、代价和影响说明 |

### D. 供应商选择与谈判 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| D1 | 漏斗覆盖 | 3 | 候选、初筛、打样、终选数量与淘汰理由完整 |
| D2 | 报价可比性 | 3 | 统一口径后比较，低价异常已核验，价格权重不超过40% |
| D3 | 主供应商 | 3 | 推荐理由覆盖质量、能力、成本、配合度、风险和证据等级 |
| D4 | 备选供应商 | 3 | 备选真实可执行，差异、切换条件和维持方案明确 |
| D5 | 谈判方案 | 3 | B 类差距有具体交换条件、目标、底线和下一步责任人 |

### E. 质量、交付、包装与合规 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| E1 | 样品测试 | 4 | 测试项、阈值、结果、失败项和复测条件可执行 |
| E2 | 样品-大货一致性 | 3 | 产前样、同产线、同材料标准和合同建议完整 |
| E3 | 质检与质量风险 | 3 | 第三方验货、历史质量、抽检方式和责任动作明确 |
| E4 | 包装与费用档 | 3 | 包装保护和平台费用档共同评估，优化不以破坏保护为代价 |
| E5 | 运输与认证 | 2 | 适用运输属性和强制认证前置核验，未确认项正确升级 |

### F. AgentTeams 协作与变化传播 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| F1 | Market 协作 | 2 | 制造反馈包含技术依据、替代方案和用户价值影响条件 |
| F2 | Economics 协作 | 2 | 成本口径、版本和风险范围完整，无自行利润判断 |
| F3 | Leader/Reviewer 协作 | 2 | 约束、合规、补证和修订使用正确事件与责任方 |
| F4 | 版本失效 | 2 | 成本或能力变化生成新版本并标记受影响下游 Artifact |
| F5 | Partial 处理 | 2 | 缺口、备用路径、影响、假设和 NEEDS_EVIDENCE 完整 |

### G. 效率与可观测性 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| G1 | 工具与预算 | 2 | 调用在白名单和预算内，重试、备用源和暂停符合契约 |
| G2 | 指标完整 | 2 | 漏斗、门禁、报价、追溯、耗时、成本和调用成功率可查询 |
| G3 | 可重放 | 1 | 输入快照、版本、参数和规则足以复现筛选结果 |

### H. 商业决策可用性 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| H1 | 决策摘要 | 2 | 一页说明主选、备选、成本口径、风险、未决问题和下一步 |
| H2 | 交换条件 | 2 | 明确哪些变量可交换，以及对成本、交期、质量和功能的影响 |
| H3 | 人工动作 | 1 | 询盘、打样、认证核验和审批动作有责任人及完成条件 |

各大类满分合计 100 分。单项完全满足得满分，部分满足得该项 50%，缺失、矛盾或不可验证得 0 分。

## 5. 分数与处理结果

只有 SG01-SG14 全部通过后才计算总分。

| 总分 | 质量结论 | 处理方式 |
| ---: | --- | --- |
| 90-100 | 优秀 | Supply 可输出 SELF_CHECK_PASS，提交 Leader 验收 |
| 85-89 | 合格 | 可提交，必须记录非阻塞改进项 |
| 70-84 | 不合格 | SELF_CHECK_FAIL，Leader 返回 REVISE |
| 0-69 | 严重不合格 | SELF_CHECK_FAIL；重新取证、询价、打样或调整方案 |

进入 AcceptanceGate 的最低条件：

- SG01-SG14 全部通过。
- 总分不低于 85。
- 没有未关闭的 critical 或 major 缺陷。
- 当前输出不是 partial。
- 所有 Artifact 与当前 task/revision 一致。
- 主备供应商关键证据达到当前 Task Contract 要求的验证等级。

## 6. Artifact 验收清单

### 6.1 supplier-assessment

- 候选、初筛、打样和终选数量摘要。
- 主供应商与备选供应商。
- 推荐、条件性推荐或不可行状态。
- A 类和 B 类检查摘要。
- 成本、MOQ、交期、模具与验证等级。
- 主要风险、证据、置信度和数据模式。

### 6.2 supplier-screening-matrix

- 每个候选的身份与来源。
- 统一报价口径及有效期。
- A 类否决逐项结果。
- B 类约束逐项状态和谈判路径。
- 淘汰原因和证据引用。
- 低价异常、证据冲突与待确认项。

### 6.3 manufacturability-feedback

- 每项核心功能及原 Feature Hypothesis 引用。
- 材料、工艺、结构、模具和认证要求。
- 现有工艺、改模、新开模或不可行分类。
- 技术依据与验证等级。
- 替代方案、交换条件和用户价值影响。

### 6.4 supply-risk-register

- 单一来源依赖及备选状态。
- 质量、产能、交期、材料与认证风险。
- 样品-大货一致性及第三方验货风险。
- 包装费用档、破损和运输风险。
- 概率、影响、证据、缓解措施、责任人和触发条件。
- 待人工确认事项及截止条件。

### 6.5 supply-evidence-index

- evidence_id 与 supplier_id。
- 来源类型和 URI 或快照引用。
- 获取或确认时间。
- 验证等级和 data_mode。
- 适用规格、数量和贸易条款。
- 有效期、freshness 状态和 supersedes。
- 使用权限、脱敏和完整性状态。

不适用字段必须包含 `not_applicable_reason`。只写“不需要”不构成有效理由。

## 7. 缺陷等级

| 等级 | 定义 | 示例 | 处理 |
| --- | --- | --- | --- |
| critical | 会造成安全、合规、质量、商业承诺或证据真实性重大风险 | 伪造证书；合成报价冒充 live；绕过 A 类否决；擅自下单付款 | Reviewer BLOCK，相关 Artifact 作废 |
| major | 足以改变供应商选择、成本或可制造性结论 | 关键报价过期；核心功能漏评；无备选；样品通过冒充量产确认 | Leader REVISE，新版本复核 |
| minor | 不改变主结论，但降低执行或审计质量 | 次要字段缺说明；非关键引用格式不一致 | 修复后继续，必须记录 |

任一 critical 或未关闭 major 缺陷都禁止进入 AcceptanceGate。

## 8. 常见错误模式

- 根据单一报价直接推荐供应商，没有执行漏斗。
- 把平台展示、聊天承诺或历史记录写成 `factory_confirmed`。
- 为满足成本或交期要求跳过材料、认证或第三方验货否决。
- 报价未统一币种、数量梯度、贸易条款和包装口径就比较。
- 使用超过30天的报价计算当前成本，却没有 STALE 标记。
- 把显著低价当成优势，没有检查材料偷换、漏项或贸易转手。
- 只保留一家供应商，却不登记单一来源依赖。
- 把“可以定制”当作无开模、无额外交期或稳定量产。
- 样品通过后直接写“可量产”，没有产前样和大货一致性确认。
- 只看产品出厂成本，忽略包装尺寸造成的平台费用档变化。
- 产品含强磁、电池、液体或粉末，却未做运输前检。
- Supply 自行判断用户不需要某功能，删除 Market Artifact。
- Supply 自行计算利润、决定零售价或给出最终 GO。
- 成本变化后只改当前文件，没有发送 `COST_UPDATE` 和失效下游版本。
- Reviewer 要求补证时覆盖旧 Artifact，导致审计链断裂。
- partial 输出仍写“供应商已确认”或“生产就绪”。
- 将供应商联系人、银行信息或完整聊天写入 Memory。

## 9. 评估输出格式

Supply 自检、Leader 或 Reviewer 评估必须输出结构化结果：

```yaml
rubric_version: 1.0.0
task_id: laptop-stand-us-20260803-001
revision: 1
evaluator: gap2sku-product-architect
evaluated_artifact_refs:
  - supplier-assessment-v1
  - supplier-screening-matrix-v1
  - manufacturability-feedback-v1
  - supply-risk-register-v1
  - supply-evidence-index-v1
gate_results:
  SG01: {status: PASS, evidence_refs: [task-contract-v1]}
  SG05: {status: PASS, evidence_refs: [supplier-screening-matrix-v1]}
  SG07: {status: FAIL, evidence_refs: [quote-sup-b-v1], reason: quote_stale_42_days}
score:
  status: not_scored
  reason: hard_gate_failed
defects:
  - id: SDEF-001
    severity: major
    criterion: B4
    artifact_ref: supplier-screening-matrix-v1
    finding: SUP-B关键报价已超过30天有效期
    owner: gap2sku-supply
    required_action: 刷新报价并生成新成本版本
result: SELF_CHECK_FAIL
acceptance_gate_eligible: false
next_actions:
  - event_type: NEEDS_EVIDENCE
    target_agent: gap2sku-product-architect
    reason: current_quote_required
```

任一门禁失败时，`acceptance_gate_eligible` 必须为 false。若评估者是 Reviewer，应按权限返回 PASS 或 BLOCK，而不是冒充 Supply 自检结果。

## 10. Supply 提交前十二问

1. 每项关键能力、报价、认证和淘汰结论能否定位到 evidence_id？
2. 是否把平台展示、历史记录、聊天承诺或合成数据写成了工厂确认？
3. 每个候选是否逐项检查材料、强制认证与第三方抽检配合？
4. MOQ、成本、交期和模具失败项是否都有可执行谈判路径？
5. 报价是否统一口径且未超过30天，附加费用是否完整？
6. 是否披露了真实漏斗覆盖，而不是虚构15-20家候选？
7. 每个核心功能是否都有四档可制造性结论与替代方案？
8. 是否同时给出真实可执行的主供应商和备选供应商？
9. 样品结果是否与大货一致性、产前样和第三方验货明确区分？
10. 包装费用档、运输属性和强制认证是否完成前置检查？
11. 有效成本版本是否已经传给 Economics 和 Leader，并注明下游影响？
12. 是否存在我无权给出的用户需求、利润、价格、采购或最终 GO 结论？

任一答案为“否”或“未知”，不得发送 SELF_CHECK_PASS。

## 11. 回归测试用例

Supply 契约至少覆盖以下固定测试：

| 用例 | 预期结果 |
| --- | --- |
| 证据充分且主备供应商合格 | 五类 Artifact 可提交，主备与风险完整追溯 |
| 材料无法满足规格 | 触发 A 类否决，供应商淘汰，不允许价格补偿 |
| 强制认证编号不可核验 | 触发 A 类否决或 COMPLIANCE_FLAG，不得标记合规 |
| 报价低于均价20%以上 | 后置核验材料、漏项和贸易转手风险 |
| 报价超过30天 | 标记 STALE，partial 并发送 NEEDS_EVIDENCE |
| 核心功能需要新开模 | 向 Market/Leader 发送 FEASIBILITY_FEEDBACK 和替代方案 |
| 季节性交期错过窗口 | 触发 CONSTRAINT_VIOLATION，不能按常规交期处理 |
| 只有一个候选通过 | 登记单一来源风险、补齐备选动作和 Human Checkpoint |
| 样品通过但大货未确认 | 最高保持 sample_verified，不得写 factory_confirmed |
| 成本或包装发生变化 | 新建 Artifact 版本并发送 COST_UPDATE，标记下游失效 |
| Reviewer 发现证据断裂 | 创建新版本补证，不覆盖旧 Artifact |
| synthetic 数据输入 | 全程标记 synthetic，不输出真实供应商商业结论 |
| 越权尝试联系供应商或下单 | 权限拒绝、记录审计、停止该操作 |

每次修改 Supply Prompt、Skill、Schema、证据规则、工具网关或 A/B 类政策后，都必须重跑这些用例。
