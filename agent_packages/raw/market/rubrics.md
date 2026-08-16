# rubrics.md - gap2sku-market

> Rubric version: 1.0.0  
> Applies to: `gap2sku-market`  
> Primary evaluators: Market self-check, Leader, Reviewer  
> Contract references: `agent.yaml`, `AGENTS.md`, `SOUL.md`

本文档定义 Market 的市场证据、痛点分析、竞品缺口和功能假设达到什么标准才算合格。高分不能抵消来源不明、数据模式造假、越权结论或关键证据缺失。

## 1. 结论与权限边界

| 结论 | 责任方 | 含义 |
| --- | --- | --- |
| `SELF_CHECK_PASS` / `SELF_CHECK_FAIL` | Market | Market 对本次产物的提交前自检 |
| `REVISE` | Leader | Market 产物需要补证、修订或重新分析 |
| `BLOCK` | Reviewer | 当前项目 revision 存在不能进入后续决策的严重缺陷 |
| `ACCEPTED` | AcceptanceGate | Market Artifact 满足系统验收条件 |
| `EARLY_NO_GO_SIGNAL` | Market 建议，Leader 与 Human Manager 决策 | 市场证据不支持继续投入的提前预警 |

Market 不得将高评分解释为市场一定成立、产品一定畅销或项目已经 GO。

## 2. 评估顺序

1. 校验 Task Contract、事件和六类提交 Artifact 的 Schema。
2. 执行硬性门禁 MG01-MG12。
3. 任一门禁失败时停止正式计分，输出缺陷和责任动作。
4. 可修复缺陷返回 Leader `REVISE`；严重造假、越权或不可追溯问题可触发 Reviewer `BLOCK`。
5. 全部门禁通过后执行 100 分质量评分。
6. 检查缺项、缺陷等级和常见错误模式。
7. 输出结构化评估结果，并绑定 `task_id + revision + artifact_refs`。

## 3. 硬性门禁

| ID | 门禁 | 通过条件 | 失败处理 |
| --- | --- | --- | --- |
| MG01 | 市场范围明确 | 目标市场、品类、渠道、用户、时间窗口和约束引用齐全 | 返回 Leader 补充 Task Contract |
| MG02 | 数据来源获准 | 每个来源在允许范围内，并记录来源引用、时间和使用权限 | 未授权数据不得进入产物 |
| MG03 | 证据可追溯 | 每项关键结论带 `evidence_id`；痛点能够回溯到原文样本 | 关键结论无证据时 `BLOCK` |
| MG04 | 数据模式真实 | live、cached、synthetic、mixed 标注与实际一致 | 将合成或缓存数据冒充 live 时 `BLOCK` |
| MG05 | 时效合格 | 关键市场量化数据在30天内，或已标记 STALE 且不是唯一关键支撑 | 过期单源结论必须 `REVISE` |
| MG06 | 样本充分或正确降级 | 达到参考样本，或按规则扩大一次后明确进入 partial | 样本不足却声称需求确认时 `BLOCK` |
| MG07 | 双源校验完成 | 搜索量、CPC、市场规模和类目增长完成双源验证 | 缺失时 `REVISE`；偏差超过20%必须上报 |
| MG08 | 痛点通过五道筛选 | 频率、结构性、严重度、可设计性、商业差异化均有记录 | 未通过不得进入核心功能假设 |
| MG09 | 防自欺检查完成 | 好评验证、先行者对照、幸存者偏差声明均存在 | 缺失时 `REVISE` |
| MG10 | 角色没有越权 | 没有供应可行、利润达标、销量保证或最终 GO 结论 | 越权结论作废；严重时 `BLOCK` |
| MG11 | 版本与引用一致 | task、revision、hash、supersedes 和输入引用一致，无未解释 stale | 生成新版本并 `REVISE` |
| MG12 | 提交包完整 | 六类 Artifact 均存在且 Schema 合法；partial 缺口已完整披露 | 不完整时不得 SELF_CHECK_PASS |

硬门禁失败不能通过增加其他评分项分数补偿。

## 4. 100 分质量评分

### A. 任务范围与数据治理 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| A1 | 市场范围 | 3 | 市场、品类、渠道、用户、场景和时间窗口清晰且一致 |
| A2 | 来源与授权 | 3 | 来源清单完整，使用权限、抓取时间和快照引用可查 |
| A3 | 数据模式 | 2 | source_type 与 data_mode 正确区分，无误导性标注 |
| A4 | 范围变化 | 2 | 扩样、换源和相似品类引入均有原因与影响披露 |

### B. 证据质量与追溯 - 25 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| B1 | 证据覆盖 | 6 | 所有关键结论均有有效 evidence_id，无 unsupported claim |
| B2 | 原文回溯 | 5 | 每个核心痛点有原文片段、来源、时间和市场引用 |
| B3 | 样本结构 | 4 | 样本量、listing覆盖、星级分布、去重和异常处理完整 |
| B4 | 时效性 | 3 | 新鲜度统计完整，STALE 数据正确降权和披露 |
| B5 | 双源一致性 | 4 | 关键量化信号双源完成，偏差与保守值处理正确 |
| B6 | 偏差和反证 | 3 | 选择偏差、幸存者偏差、相反样本和未知项未被隐藏 |

### C. 痛点识别质量 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| C1 | 聚类与去重 | 3 | 同义痛点正确归并，物流噪音、误解和偶发个案被区分 |
| C2 | 频率计算 | 4 | 使用目标品类1-3星评论占比，分母、分子和阈值明确 |
| C3 | 结构性判断 | 4 | 能说明问题来自产品设计还是执行噪音，并给出证据 |
| C4 | 痛苦程度 | 3 | 区分退货退款、强烈不满和轻微抱怨，不做平均排序 |
| C5 | 可设计性 | 3 | 痛点能够映射到尺寸、材料、结构或参数方向 |
| C6 | 商业影响 | 3 | 能解释改进是否可展示、是否影响购买或退货 |

### D. 需求结构与竞品缺口 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| D1 | 用户与场景 | 3 | 用户分层、使用场景、购买动机和差异明确 |
| D2 | 竞品可比性 | 3 | 竞品属于相同市场、价格带和使用场景，比较口径一致 |
| D3 | 缺口判断 | 4 | 清楚区分已解决、部分解决和未解决，不把功能缺失直接等同需求 |
| D4 | 先行者对照 | 2 | 检查已解决痛点竞品的实际表现及替代解释 |
| D5 | 集中度判断 | 3 | Top 3 集中度计算可追溯，超过70%时正确发出预警 |

### E. Feature Hypothesis 质量 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| E1 | 痛点追溯 | 4 | 每项假设连接痛点、用户、场景、原文证据和竞品缺口 |
| E2 | 假设而非承诺 | 3 | 使用待验证表达，不宣称已经可制造或必然提升销量 |
| E3 | 优先级 | 3 | Must-have、Should-have、Explore、Reject 有证据化理由 |
| E4 | 反证与失效条件 | 2 | 包含反例、置信度和什么证据会推翻该假设 |
| E5 | 下游验证请求 | 3 | Supply、Economics及适用的合规问题明确且可执行 |

### F. AgentTeams 协作与风险处理 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| F1 | 事件使用 | 3 | 咨询、挑战、补证、Early NO-GO和交接使用正确事件 |
| F2 | 责任边界 | 3 | 不替 Supply、Economics、Reviewer 或 Leader 做决定 |
| F3 | 冲突表达 | 2 | 能说明供应或利润约束造成的用户价值损失及替代路径 |
| F4 | Partial处理 | 2 | 缺口、备用路径、影响和 NEEDS_EVIDENCE 完整 |

### G. 效率与可观测性 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| O1 | 工具与预算 | 2 | 调用在白名单和预算内，重试与备用路径符合契约 |
| O2 | 指标完整 | 2 | 证据覆盖、时效、样本、追溯、耗时和成本可查询 |
| O3 | 可重放 | 1 | 输入快照、版本和参数足以复现本次分析 |

各大类满分合计100分。单项完全满足得满分，部分满足得该项50%，缺失、矛盾或不可验证得0分。

## 5. 分数与处理结果

只有 MG01-MG12 全部通过后才计算总分。

| 总分 | 质量结论 | 处理方式 |
| ---: | --- | --- |
| 90-100 | 优秀 | Market 可输出 SELF_CHECK_PASS，提交 Leader 验收 |
| 85-89 | 合格 | 可提交，必须记录非阻塞改进项 |
| 70-84 | 不合格 | SELF_CHECK_FAIL，Leader 返回 REVISE |
| 0-69 | 严重不合格 | SELF_CHECK_FAIL；重新取证或终止本次市场判断 |

进入 AcceptanceGate 的最低条件：

- MG01-MG12 全部通过。
- 总分不低于85。
- 没有未关闭的 critical 或 major 缺陷。
- 当前输出不是 partial。
- 所有 Artifact 与当前 task/revision 一致。

## 6. Artifact 验收清单

### 6.1 demand-structure

- 目标用户与分层。
- 使用场景和购买动机。
- 需求端信号及来源。
- 搜索或类目信号。
- Top 3 集中度。
- 证据、置信度和数据模式。

### 6.2 pain-point-set

- 每条痛点标签、占比和严重度。
- 五道筛选逐项结果。
- 原文片段引用。
- 样本画像和分母定义。
- 偏差、反证和适用范围。

### 6.3 competitor-gap-map

- 可比竞品及选择理由。
- 售价、评分、评论量和功能事实。
- 已解决、部分解决和未解决缺口。
- 先行者对照。
- Top 3 集中度及证据。

### 6.4 feature-hypotheses

- 痛点和证据引用。
- 用户、场景和预期价值。
- 优先级与理由。
- 反证、置信度和失效条件。
- Supply、Economics或合规待验证项。

### 6.5 market-evidence-summary

- 来源清单和时效分布。
- 样本局限和口径变化。
- 置信度分布。
- unsupported claims清单。
- 未解决证据缺口。

### 6.6 market-raw-evidence-index

- evidence_id。
- 来源类型与URI或快照引用。
- 抓取时间、市场和原文引用。
- 使用权限与脱敏状态。

不适用字段必须包含 `not_applicable_reason`。只写“不需要”不构成有效理由。

## 7. 缺陷等级

| 等级 | 定义 | 示例 | 处理 |
| --- | --- | --- | --- |
| critical | 会造成虚假市场判断、越权决策或数据违规 | 合成数据冒充live；捏造评论；保证销量；使用未授权数据 | Reviewer BLOCK，相关Artifact作废 |
| major | 足以改变痛点、优先级或功能判断 | 核心痛点无原文；样本不足却确认需求；漏掉双源冲突 | Leader REVISE，新版本复核 |
| minor | 不改变主要判断，但降低表达或审计质量 | 次要字段缺说明；非关键引用格式不一致 | 修复后继续，必须记录 |

任一 critical 或未关闭 major 缺陷都禁止进入 AcceptanceGate。

## 8. 常见错误模式

- 用评论绝对数量替代低星评论占比。
- 将一条高情绪评论当作高频结构性痛点。
- 把物流破损、错误使用和产品设计问题混为一类。
- 把“竞品没有该功能”直接解释为市场需求。
- 只分析差评，不检查好评和先行者竞品。
- 样本扩展到相似品类后不披露口径变化。
- 用社媒热度或供应商推品单独证明需求成立。
- 将竞品售价较高解释为当前方案一定有利润。
- 删除 Supply 否决的功能，却不披露用户价值损失。
- 使用模型生成的示例评论充当原始证据。
- 对双源冲突取平均值，而不使用保守值和上报偏差。
- ProductSpec更新后继续使用旧市场Artifact或旧hash。
- 只在聊天中说“证据不足”，没有发送 NEEDS_EVIDENCE。
- partial输出仍使用“需求已确认”或“市场成立”。
- 为满足结论而隐藏反例、偏差或失败来源。

## 9. 评估输出格式

Market 自检、Leader 或 Reviewer 评估必须输出结构化结果：

```yaml
rubric_version: 1.0.0
task_id: laptop-stand-us-20260803-001
revision: 1
evaluator: gap2sku-product-architect
evaluated_artifact_refs:
  - pain-point-set-v1
  - competitor-gap-map-v1
  - feature-hypotheses-v1
gate_results:
  MG01: {status: PASS, evidence_refs: [task-contract-v1]}
  MG02: {status: PASS, evidence_refs: [market-evidence-index-v1]}
  MG03: {status: FAIL, evidence_refs: [], reason: core_pain_missing_original_excerpt}
score:
  status: not_scored
  reason: hard_gate_failed
defects:
  - id: MDEF-001
    severity: major
    criterion: B2
    artifact_ref: pain-point-set-v1
    finding: PP-003没有可回溯的评论原文
    owner: gap2sku-market
    required_action: 补充原文证据或移除该核心痛点
result: SELF_CHECK_FAIL
acceptance_gate_eligible: false
next_actions:
  - event_type: NEEDS_EVIDENCE
    target_agent: gap2sku-product-architect
    reason: unresolved_core_evidence_gap
```

任一门禁失败时，`acceptance_gate_eligible` 必须为 false。若评估者是 Reviewer，应按权限返回 PASS 或 BLOCK，而不是冒充 Market 自检结果。

## 10. Market 提交前十问

1. 每项核心结论能否定位到 evidence_id 和原始来源？
2. 每个核心痛点是否有评论或问答原文？
3. 样本量、listing覆盖、星级分布和时间范围是否明确？
4. 是否把合成、缓存或推断数据写成了真实市场事实？
5. 搜索量、CPC等关键数值是否完成双源校验？
6. 五道筛子是否真实执行，而不是事后补写？
7. 是否检查了好评、先行者竞品、幸存者偏差和反例？
8. 每个功能假设是否仍然是待 Supply 和 Economics 验证的假设？
9. 是否存在我无权给出的供应、利润、销量或最终GO结论？
10. 如果删掉任一证据，受影响的痛点与功能是否可以被系统识别？

任一答案为“否”或“未知”，不得发送 SELF_CHECK_PASS。

## 11. 回归测试用例

Market 契约至少覆盖以下固定测试：

| 用例 | 预期结果 |
| --- | --- |
| 样本充分且双源一致 | 六类Artifact可提交，关键结论完整追溯 |
| 评论样本不足 | 扩样一次后partial，并发送 NEEDS_EVIDENCE |
| 双源偏差超过20% | 使用保守值、降低置信度并发送 CONFIDENCE_CHANGED |
| Top 3集中度超过70% | 发送 EARLY_NO_GO_SIGNAL，不自行终止项目 |
| Supply否决核心功能 | 保留用户价值证据，发送 EVIDENCE_CHALLENGE |
| Reviewer发现追溯断裂 | 创建新版本补证，不覆盖旧Artifact |
| synthetic数据输入 | 全程标记synthetic，不输出真实市场结论 |
| 越权调用利润工具 | 权限拒绝、记录审计、停止该操作 |

每次修改 Market Prompt、Skill、Schema、证据规则或工具网关后，都必须重跑这些用例。
