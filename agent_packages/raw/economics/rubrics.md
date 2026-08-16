# rubrics.md - gap2sku-economics

> Rubric version: 1.0.0  
> Applies to: `gap2sku-economics`  
> Primary evaluators: Economics self-check, Leader, Reviewer  
> Contract references: `agent.yaml`, `AGENTS.md`, `SOUL.md`

本文档定义 Economics 的成本模型、利润结论、情景分析和商业风险产物达到什么标准才算合格。高分不能抵消成本漏项、输入版本错误、确定性校验失败、过期费率或越权作出最终 GO/NO-GO。

## 1. 结论与权限边界

| 结论 | 责任方 | 含义 |
| --- | --- | --- |
| `SELF_CHECK_PASS` / `SELF_CHECK_FAIL` | Economics | Economics 对本次产物的提交前自检 |
| `REVISE` | Leader | 需要补数、修订口径、重算或建立新版本 |
| `BLOCK` | Reviewer | 当前 revision 存在不能进入后续决策的严重缺陷 |
| `ACCEPTED` | AcceptanceGate | Economics Artifact 满足系统验收条件 |
| `RISK_ALERT` | Economics 发出，Leader 处理 | 毛利、压力情景或现金风险越过边界 |
| `NO_GO_RECOMMENDATION` | Economics 建议，Leader/Human Manager 决策 | 当前经济证据不支持继续投入，但不是最终项目状态 |

Economics 不得将高评分解释为保证盈利、保证销量或已经批准投资。

## 2. 评估顺序

1. 校验 Task Contract、红线、输入版本、事件和五类 Artifact Schema。
2. 执行硬性门禁 EG01-EG14。
3. 任一门禁失败时停止正式计分，输出缺陷、责任方和整改动作。
4. 可修复问题返回 Leader `REVISE`；伪造输入、漏算成本、确定性校验失败或越权承诺可触发 Reviewer `BLOCK`。
5. 全部门禁通过后执行 100 分质量评分。
6. 检查缺项、缺陷等级、假设脆弱性和下游失效范围。
7. 输出结构化评估结果，并绑定 `task_id + revision + artifact_refs + formula_version`。

## 3. 硬性门禁

| ID | 门禁 | 通过条件 | 失败处理 |
| --- | --- | --- | --- |
| EG01 | 任务与红线明确 | 市场、品类、渠道、币种、价格范围、毛利红线、现金约束和输入引用齐全 | 返回 Leader 补充 Task Contract |
| EG02 | 输入来源与版本有效 | Supply、Market、费率、物流、汇率和税费均来自允许来源，版本及生效时间可查 | 未授权或来源不明输入不得使用 |
| EG03 | 成本堆叠无静默缺项 | 所有成本类别均标记 confirmed、estimated、not_applicable 或 missing；不适用有理由 | 漏项或缺失填零时 `BLOCK` |
| EG04 | 输入状态与数据模式真实 | 估算、确认、live、cached、synthetic、mixed 标注与事实一致 | 估算冒充确认或合成冒充 live 时 `BLOCK` |
| EG05 | 价格口径完整 | 标价、促销价、实现售价及折算依据齐全，不能把价格上限视为可接受事实 | 缺少实现售价口径时 `REVISE` |
| EG06 | 确定性校验通过 | 所有派生金额、比例、盈亏平衡、回本、损失和情景结果均通过确定性工具 | 校验失败时 `BLOCK`，禁止模型解释通过 |
| EG07 | 三档情景完整 | 基准、保守、压力情景均完成，压力变量同时生效且定义未被擅改 | 缺失或只改变一个压力变量时 `REVISE` |
| EG08 | 毛利红线正确执行 | 默认/任务红线、25%-30%观察区、<25%建议 NO-GO 和 quoted 成本5%缓冲正确 | 放宽红线或漏加缓冲时 `BLOCK` |
| EG09 | 四项决策输出齐全 | 盈亏平衡单量、回本周期、最坏损失和首单现金占用均可复算 | 缺失时 `REVISE` |
| EG10 | 关键假设审计完整 | 销量、广告、退货、实现售价、汇率、物流、费率均有来源、置信度和失效阈值 | 关键假设缺审计时 `REVISE` |
| EG11 | 时效规则通过 | 报价/CPC/物流不超过30天，汇率不超过7天，政策类有有效生效日期；STALE 未作唯一关键支撑 | 过期单源支撑时 `REVISE` |
| EG12 | 协作和角色边界正确 | 成本问题找 Supply、价格证据经 Leader 找 Market；无供应真实性、市场需求、采购或最终 GO 结论 | 越权结论作废，严重时 `BLOCK` |
| EG13 | 版本和失效范围一致 | 输入、公式、task/revision/hash/supersedes 一致，变化生成新版本并声明下游影响 | 使用旧输入或覆盖旧版本时 `BLOCK` |
| EG14 | 提交包完整 | 五类 Artifact 均存在且 Schema 合法；partial 缺口与禁止结论正确 | 不完整时不得 SELF_CHECK_PASS |

硬门禁失败不能通过提高其他评分项分数补偿。

## 4. 100 分质量评分

### A. 任务范围与输入治理 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| A1 | 任务范围 | 3 | 市场、品类、渠道、币种、价格和商业约束清晰一致 |
| A2 | 输入版本 | 3 | 每个输入带来源 Artifact、版本、生效时间和 supersedes |
| A3 | 数据状态 | 2 | confirmed/estimated/not_applicable/missing 与 data_mode 正确 |
| A4 | 单位和口径 | 2 | 币种、税费、数量、贸易条款和固定/变动/比例分类一致 |

### B. 成本完整性 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| B1 | 采购与模具 | 3 | 出厂价、数量梯度、模具、打样和摊销完整 |
| B2 | 物流、关税与入库 | 4 | 头程、关税、清关、入库配置、入库运输和旺季附加完整 |
| B3 | 平台与仓储 | 4 | 佣金、配送费、包装档、仓储和库存双向风险完整 |
| B4 | 退货、广告与促销 | 4 | 退货损耗、单均广告、优惠券和活动费口径完整 |
| B5 | 合规与其他 | 3 | 认证、检测、保险、FTO、汇率缓冲、支付汇损和冷启动费用完整 |
| B6 | 缺项控制 | 2 | 所有类别有状态，缺失和不适用均正确披露 |

### C. 计算与公式正确性 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| C1 | 实现售价 | 3 | 标价、促销和销售调整折算公式正确 |
| C2 | 单元经济 | 5 | 变动成本、固定成本、贡献毛利和毛利率计算正确 |
| C3 | 盈亏平衡与回本 | 4 | 正贡献前提、首单投入和现金流口径正确 |
| C4 | 最坏损失与现金占用 | 4 | 清货损失、不可回收成本、库存与在途资金完整 |
| C5 | 确定性验证 | 4 | 全部派生值与公式版本通过工具复核，可重放 |

### D. 情景与风险分析 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| D1 | 基准情景 | 3 | 使用当前最佳证据，无选择性乐观输入 |
| D2 | 保守情景 | 3 | 双源低销量、高CPC、高退货和最大汇率缓冲正确 |
| D3 | 压力情景 | 4 | 售价-10%、成本+10%、退货翻倍和旺季费同时生效 |
| D4 | 脆弱性 | 3 | 能识别最小变化导致红线失效的变量和阈值 |
| D5 | 风险量化 | 2 | 风险有金额、概率/范围、责任人、触发和缓解动作 |

### E. 假设与证据质量 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| E1 | 销量假设 | 3 | 双源、保守值、冷启动转化和偏差处理完整 |
| E2 | 广告假设 | 3 | CPC时效、单均广告成本和阶段差异完整 |
| E3 | 退货与实现售价 | 3 | 退货取高值，促销频率正确折算实现售价 |
| E4 | 费率与外部输入 | 3 | 平台、物流、汇率、税费均有有效时间和来源 |
| E5 | 失效条件 | 3 | 每个关键假设有阈值、置信度和下游失效范围 |

### F. AgentTeams 协作与版本传播 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| F1 | Supply 协作 | 2 | 成本澄清包含字段、口径、版本和利润影响 |
| F2 | Market 协作 | 2 | 价格证据请求经 Leader 路由，问题具体可执行 |
| F3 | Leader/Reviewer 协作 | 2 | 风险、修订、补证和交接使用正确事件 |
| F4 | 增量重算 | 2 | 输入变化只重算受影响内容并生成新版本 |
| F5 | Partial 处理 | 2 | 缺口、假设、禁止结论、影响和 NEEDS_EVIDENCE 完整 |

### G. 商业决策可用性 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| G1 | 一页决策摘要 | 2 | 利润分类、红线、四项风险数字和关键条件一页可读 |
| G2 | 可选动作 | 2 | 维持、降本、调价、删功能、换渠道或建议NO-GO的交换条件明确 |
| G3 | 人工决策 | 1 | 需要 Human Manager 决定的金额、阈值和截止条件清晰 |

### H. 效率与可观测性 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| H1 | 工具与预算 | 2 | 调用在白名单和预算内，降级与重试符合契约 |
| H2 | 指标完整 | 2 | 完整度、估算率、时效、验证率、耗时与成本可查询 |
| H3 | 可重放 | 1 | 输入快照、公式版本、参数和规则足以复现结果 |

各大类满分合计 100 分。单项完全满足得满分，部分满足得该项 50%，缺失、矛盾或不可验证得 0 分。

## 5. 分数与处理结果

只有 EG01-EG14 全部通过后才计算总分。

| 总分 | 质量结论 | 处理方式 |
| ---: | --- | --- |
| 90-100 | 优秀 | Economics 可输出 SELF_CHECK_PASS，提交 Leader 验收 |
| 85-89 | 合格 | 可提交，必须记录非阻塞改进项 |
| 70-84 | 不合格 | SELF_CHECK_FAIL，Leader 返回 REVISE |
| 0-69 | 严重不合格 | SELF_CHECK_FAIL；补数、修订口径或重新建模 |

进入 AcceptanceGate 的最低条件：

- EG01-EG14 全部通过。
- 总分不低于85。
- 没有未关闭的 critical 或 major 缺陷。
- 当前输出不是 partial。
- 所有 Artifact、输入版本和公式版本一致。
- 确定性校验通过率为100%。

## 6. Artifact 验收清单

### 6.1 unit-economics

- 标价、促销价与实现售价。
- 总单位变动成本和固定成本。
- 贡献毛利、毛利率和红线结果。
- 盈亏平衡单量和回本周期。
- 最坏情况损失和首单现金占用。
- 公式版本、确定性校验引用、输入引用、置信度和数据模式。

### 6.2 cost-stack

- 每个成本项的数值、币种、单位和分类。
- confirmed/estimated/not_applicable/missing 状态。
- 来源、版本、生效日期和 supersedes。
- 固定、单位变动或比例成本。
- 包装档、数量和贸易条款。
- 缺失项、不适用理由和估算依据。

### 6.3 sensitivity-analysis

- 基准、保守、压力情景完整输入与输出。
- 单变量敏感性和红线穿越点。
- 最脆弱假设及其最小失效变化。
- 每个情景的确定性校验引用。
- 情景对 ProductSpec、备货与 Review 的影响。

### 6.4 pricing-viability-report

- 价格口径与实现售价假设。
- Market 竞品价格和促销证据引用。
- profitable、conditionally_profitable、revise 或 no_go_recommendation。
- 生存条件、限制和反证。
- 降本、调价、删功能、换渠道等选项与交换条件。

### 6.5 economics-risk-register

- 关键假设、风险、概率或范围及金额影响。
- 失效阈值和下游失效范围。
- 缓解选项、责任人和触发条件。
- 需要 Human Manager 决定的金额与截止条件。
- 当前未关闭的输入缺口和置信度。

不适用字段必须包含 `not_applicable_reason`。只写“不需要”不构成有效理由。

## 7. 缺陷等级

| 等级 | 定义 | 示例 | 处理 |
| --- | --- | --- | --- |
| critical | 会造成错误投资、虚假利润、数据造假或越权承诺 | 漏算平台费；篡改报价；确定性校验失败仍提交；保证盈利；擅自批准低毛利 | Reviewer BLOCK，相关 Artifact 作废 |
| major | 足以改变利润分类、现金风险或 ProductSpec | 使用过期报价；缺压力情景；漏5%缓冲；公式/输入版本不一致 | Leader REVISE，新版本复核 |
| minor | 不改变主要分类，但降低执行或审计质量 | 次要字段缺说明；非关键引用格式不一致 | 修复后继续，必须记录 |

任一 critical 或未关闭 major 缺陷都禁止进入 AcceptanceGate。

## 8. 常见错误模式

- 只计算工厂成本、运费和平台佣金，漏掉仓储、退货、广告、促销或合规。
- 缺失成本直接填0，没有标记 missing。
- 用标价计算利润，不折算优惠券和促销后的实现售价。
- 新品期直接套用成熟 listing 的 ACoS。
- 退货率只取较低的行业均值，忽略 Market 退货信号。
- Supply 成本只有 quoted 级，却没有增加5%缓冲。
- 平台费率没有生效日期，仍标记 confirmed。
- 用超过30天的 CPC、物流或报价作为唯一关键输入。
- 只做基准情景，或压力情景只改变一个变量。
- LLM 自己算毛利，没有确定性工具验证。
- 贡献毛利为负时仍计算无意义的正盈亏平衡单量。
- 只报告毛利率，不报告最坏损失和现金占用。
- 把价格上限当成用户愿付价格。
- 因为痛点强烈而放宽毛利红线。
- Economics 自行修改 Supply 报价或 Market 数据。
- 将 no_go_recommendation 写成最终项目 NO-GO。
- 成本变化后覆盖旧结果，没有新建版本和声明失效范围。
- partial 输出仍写“已盈利”或“毛利已确认”。
- 把单个项目的售价、利润或毛利写入长期 Memory。

## 9. 评估输出格式

Economics 自检、Leader 或 Reviewer 评估必须输出结构化结果：

```yaml
rubric_version: 1.0.0
task_id: laptop-stand-us-20260803-001
revision: 1
formula_version: economics-formula-v1
evaluator: gap2sku-product-architect
evaluated_artifact_refs:
  - unit-economics-v1
  - cost-stack-v1
  - sensitivity-analysis-v1
  - pricing-viability-report-v1
  - economics-risk-register-v1
gate_results:
  EG01: {status: PASS, evidence_refs: [task-contract-v1]}
  EG03: {status: PASS, evidence_refs: [cost-stack-v1]}
  EG06: {status: FAIL, evidence_refs: [economics-verification-v1], reason: contribution_margin_mismatch}
score:
  status: not_scored
  reason: hard_gate_failed
defects:
  - id: EDEF-001
    severity: critical
    criterion: C5
    artifact_ref: unit-economics-v1
    finding: 贡献毛利与确定性工具结果不一致
    owner: gap2sku-economics
    required_action: 锁定输入快照并按公式版本重新计算
result: SELF_CHECK_FAIL
acceptance_gate_eligible: false
next_actions:
  - event_type: REVISION_REQUIRED
    target_agent: gap2sku-product-architect
    reason: deterministic_verification_failed
```

任一门禁失败时，`acceptance_gate_eligible` 必须为 false。若评估者是 Reviewer，应按权限返回 PASS 或 BLOCK，而不是冒充 Economics 自检结果。

## 10. Economics 提交前十二问

1. 每个成本类别是否都有明确状态，是否存在未说明的0值？
2. 每个金额是否能定位到来源、版本、币种、单位和生效时间？
3. 标价是否已经折算为真实可实现售价？
4. 估算值是否包含依据、区间、置信度和失效阈值？
5. Supply 成本若只有 quoted 级，是否增加了5%缓冲？
6. 新品广告是否按单均成本，而不是成熟 ACoS 建模？
7. 基准、保守和压力情景是否全部完成且定义未被擅改？
8. 所有金额、比例和情景是否通过确定性工具？
9. 盈亏平衡、回本、最坏损失和现金占用是否齐全？
10. 毛利红线和观察区是否按 Task Contract 与人类权限执行？
11. 输入变化是否生成新版本并声明下游失效范围？
12. 是否存在我无权给出的市场、供应、采购、保证盈利或最终 GO/NO-GO 结论？

任一答案为“否”或“未知”，不得发送 SELF_CHECK_PASS。

## 11. 回归测试用例

Economics 契约至少覆盖以下固定测试：

| 用例 | 预期结果 |
| --- | --- |
| 成本完整且保守情景过线 | 五类 Artifact 可提交，分类为 profitable |
| 已知成本项缺失 | 标记 missing、partial 并发送 NEEDS_EVIDENCE |
| Supply 报价超过30天 | 发送 COST_CLARIFICATION_REQUEST，不作无条件盈利判断 |
| Supply 成本仅 quoted | 自动增加5%缓冲并降低置信度 |
| CPC 双源偏差超过20% | 使用保守输入并发送 CONFIDENCE_CHANGED |
| 基准过线但压力失效 | 分类 conditionally_profitable 并发出 RISK_ALERT |
| 基准毛利低于25% | 输出 no_go_recommendation，由 Leader/Human 决策 |
| 确定性结果与模型输出不一致 | BLOCK 提交并创建修订任务 |
| 成本或费率更新 | 新建版本，只重算受影响内容并声明下游失效 |
| 贡献毛利为负 | 盈亏平衡标记不可达，不输出伪正数 |
| synthetic 数据输入 | 全程标记 synthetic，不输出真实商业盈利结论 |
| 越权修改供应报价或最终GO | 权限拒绝、记录审计、停止该操作 |

每次修改 Economics Prompt、Skill、Schema、公式、红线、费率工具或情景定义后，都必须重跑这些用例。
