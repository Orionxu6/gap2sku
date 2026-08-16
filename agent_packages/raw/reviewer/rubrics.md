# rubrics.md - gap2sku-reviewer

> Rubric version: 1.0.0  
> Applies to: `gap2sku-reviewer`  
> Primary evaluators: Reviewer self-check, Leader, AcceptanceGate, Human audit  
> Contract references: `agent.yaml`, `AGENTS.md`, `SOUL.md`

本文档评估 Reviewer 自身的审查质量，而不是重复执行 R-M/R-S/R-E/R-L/R-C/R-G 业务规则。高分不能抵消漏跑规则、抽检不足、错误复用旧 PASS、修改源 Artifact、无依据 BLOCK 或在 UNVERIFIED 存在时放行。

## 1. 结论与权限边界

| 结论 | 责任方 | 含义 |
| --- | --- | --- |
| `SELF_CHECK_PASS` / `SELF_CHECK_FAIL` | Reviewer | Reviewer 对本次评审过程与 Review Artifact 的自检 |
| `REVISE_REVIEW` | Leader/AcceptanceGate | Reviewer 自身需要补跑规则、重做抽检或修复 Finding |
| `REVIEW_INVALID` | AcceptanceGate/Human audit | 当前 Review Report 不可作为决策输入 |
| `REVIEW_ACCEPTED` | AcceptanceGate | Reviewer 的过程、证据和输出满足本 Rubric |
| `RULE_CALIBRATION_REQUIRED` | Human/Rule Owner | 异议或事故显示规则需要调整，但 Reviewer 不能自行改规则 |

Reviewer 对业务方案的 PASS/BLOCK 权限，不等于 Reviewer 自身的审查过程自动合格。

## 2. 评估顺序

1. 锁定被评 Review Report、Product Spec hash、输入快照与规则集版本。
2. 执行 Reviewer 质量硬门禁 RVG01-RVG14。
3. 任一门禁失败时停止评分，输出 Reviewer 自身缺陷与重审范围。
4. 对错误 PASS、无规则 BLOCK、源 Artifact 修改和证据审计造假直接判 `REVIEW_INVALID`。
5. 全部门禁通过后执行 100 分质量评分。
6. 检查误判风险、事件路由、异议状态和完成信号。
7. 输出结构化 Reviewer QA 结果并绑定 Review Report hash。

## 3. 硬性门禁

| ID | 门禁 | 通过条件 | 失败处理 |
| --- | --- | --- | --- |
| RVG01 | 评审快照锁定 | task、revision、Product Spec hash、Artifact Graph、规则集和人工日志截点齐全 | 快照不完整时 `REVISE_REVIEW` |
| RVG02 | 规则集权威且版本明确 | 所有 R-M/R-S/R-E/R-L/R-C/R-G 规则有版本、Owner 和执行记录 | 使用未知/无版本规则阻断时 `REVIEW_INVALID` |
| RVG03 | 输入与 Artifact 完整检查 | 预期 Artifact、Schema、引用、hash、supersedes 和状态均已验证 | 未检查缺失输入时 `REVISE_REVIEW` |
| RVG04 | 确定性全检完成 | 每条确定性规则均执行，执行数等于预期数，无静默跳过 | 漏跑规则或伪造执行结果时 `REVIEW_INVALID` |
| RVG05 | 证据抽检达标 | 抽检比例≥20%、向上取整、三个关键域均覆盖、随机种子可重放 | 比例或覆盖不足时 `REVISE_REVIEW` |
| RVG06 | 伪造升级规则执行 | 发现1例伪造/错配后已扩大到全量审计，确认结果有证据 | 未扩大审计仍 PASS 时 `REVIEW_INVALID` |
| RVG07 | 跨域、否决与人工闸口审计完成 | Market/Supply/Economics/ProductSpec 一致性、否决项和 Human Checkpoint 均独立复核 | 缺失时 `REVISE_REVIEW` |
| RVG08 | Finding 原子且可整改 | 每条 Finding 有规则、版本、事实、证据、责任人、修复条件和复审范围 | 模糊或多责任混写时 `REVISE_REVIEW` |
| RVG09 | 评审分级正确 | PASS、PASS_WITH_CONDITIONS、REVISE、BLOCK 严格符合契约 | UNVERIFIED/STALE/失败存在仍 PASS 时 `REVIEW_INVALID` |
| RVG10 | 独立性与只读边界 | 未修改源 Artifact、未补造证据、未依赖隐藏推理/共识/进度压力 | 修改源文件或伪造证据时 `REVIEW_INVALID` |
| RVG11 | 当前版本绑定 | Review Artifact 与当前 Product Spec hash、revision、规则版本一致，未复用旧 PASS | 错配或复用旧结论时 `REVIEW_INVALID` |
| RVG12 | 事件与责任路由正确 | Finding 到责任 Agent+Leader，修订到 Leader，人类事项直达 Human，完成信号符合 V1 | 路由缺失或发送未注册事件时 `REVISE_REVIEW` |
| RVG13 | 异议与修订循环受控 | BLOCK 只允许一次异议，维持后升级人类；REVISE 最多3轮 | 重复 BLOCK/REVISE 循环时 `REVIEW_INVALID` |
| RVG14 | Reviewer 提交包完整 | 四类必需 Review Artifact 均合法；有异议时 appeal record 存在 | 不完整时不得 SELF_CHECK_PASS |

硬门禁失败不能通过提高其他评分项分数补偿。

## 4. 100 分质量评分

### A. 范围锁定与独立性 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| A1 | 快照锁定 | 3 | Task、Spec、Artifact Graph、规则和人工日志截点一致 |
| A2 | 权限边界 | 3 | 只读源 Artifact，只写 Review Artifact，无代改或补证 |
| A3 | 独立判断 | 2 | 不使用共识、隐藏推理、时间压力或历史 PASS 代替证据 |
| A4 | 审查范围 | 2 | 明确哪些属于规则审查，哪些仅为 Info 级偏好 |

### B. 规则执行质量 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| B1 | 规则覆盖 | 5 | expected_rule_count 与 executed_rule_count 一致 |
| B2 | 规则版本 | 3 | 每条结果绑定 rule_id、version、输入和执行器 |
| B3 | 确定性结果 | 5 | Schema、引用、版本、红线和复算由确定性工具完成 |
| B4 | 未验证处理 | 3 | 工具不可用时正确标记 UNVERIFIED 并限制结论上限 |
| B5 | 规则冲突 | 2 | 版本冲突被披露和升级，不临时创造个人规则 |
| B6 | 执行可重放 | 2 | 输入快照、参数和日志足以复现全部规则结果 |

### C. 证据抽检质量 - 20 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| C1 | 抽检比例 | 4 | 样本数达到总体20%并正确向上取整 |
| C2 | 分层覆盖 | 4 | Market、Supply、Economics 三域至少各有样本 |
| C3 | 可重放抽样 | 3 | 记录总体、分层方法、随机种子和样本ID |
| C4 | 原始回溯 | 4 | 样本可回溯原文/原记录，hash 与标注一致 |
| C5 | 真实性判断 | 3 | 能识别断章取义、张冠李戴和验证等级夸大 |
| C6 | 扩大全检 | 2 | 发现伪造后自动扩大并记录覆盖与结论 |

### D. 跨域一致性、否决与人工闸口 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| D1 | Market到功能 | 3 | 痛点、证据、FeatureDecision 与 Product Spec 一致 |
| D2 | 功能到供应 | 3 | 规格、工艺、主备、成本版本和风险一致 |
| D3 | 供应到经济 | 3 | Supply成本、包装档与Economics输入版本一致 |
| D4 | 否决复核 | 3 | 认证、FTO、权限、禁售和Supply A类否决独立复核 |
| D5 | 人工闸口 | 3 | 强制暂停日志、决定内容、适用范围和解除条件完整 |

### E. Finding 质量 - 15 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| E1 | 原子性 | 3 | 一条Finding只描述一个规则失败和一个主要责任方 |
| E2 | 事实与证据 | 3 | 事实具体，Artifact和原始证据引用可查 |
| E3 | 严重级别 | 3 | Info/Warning/Revise/Block 与规则后果一致 |
| E4 | 修复条件 | 3 | 动作、完成标准和责任人可执行，不使用模糊建议 |
| E5 | 影响范围 | 3 | 复审范围和下游失效 Artifact 明确 |

### F. 结论、异议与循环控制 - 10 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| F1 | 结论分类 | 3 | 总结论由规则结果确定，无主观升级或降级 |
| F2 | 条件通过 | 2 | 只含人类条件，责任人、截止和解除标准齐全 |
| F3 | BLOCK 异议 | 2 | 一次、附新证据、独立复审并记录结果 |
| F4 | 误判诚实性 | 1 | 被推翻时记录根因，不隐藏 false positive |
| F5 | 修订上限 | 2 | 第3轮或证据不可得时及时升级 Human Manager |

### G. 可观测性与可重放 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| G1 | 指标完整 | 2 | 规则、抽检、Finding、时效、异议、耗时和成本可查询 |
| G2 | 审计日志 | 2 | 规则执行、证据访问、事件、状态和版本变化完整 |
| G3 | 可重放 | 1 | 固定快照、规则版本和随机种子可复现结果 |

### H. 公平性与评审效率 - 5 分

| ID | 评分项 | 分值 | 满分标准 |
| --- | --- | ---: | --- |
| H1 | 错误PASS/错误BLOCK平衡 | 2 | 明确两类误判成本，不以“越严越好”为目标 |
| H2 | 非规则意见控制 | 1 | 文案和偏好仅为Info，不制造无效返工 |
| H3 | 增量复审 | 2 | 新revision只扩展必要范围，同时重跑所有受影响规则与抽检 |

各大类满分合计 100 分。单项完全满足得满分，部分满足得该项 50%，缺失、矛盾或不可验证得 0 分。

## 5. 分数与处理结果

只有 RVG01-RVG14 全部通过后才计算总分。

| 总分 | Reviewer质量结论 | 处理方式 |
| ---: | --- | --- |
| 95-100 | 优秀 | Review Artifact 可进入 AcceptanceGate |
| 90-94 | 合格 | 可进入 AcceptanceGate，记录非阻塞校准项 |
| 80-89 | 不合格 | `REVISE_REVIEW`，补跑或修复 Reviewer 输出 |
| 0-79 | 严重不合格 | `REVIEW_INVALID`，当前 Review Report 不可用于决策 |

进入 AcceptanceGate 的 Reviewer 质量最低条件：

- RVG01-RVG14 全部通过。
- 总分不低于90。
- 没有未关闭的 critical 或 major Reviewer 缺陷。
- Review Report 不是 partial/unverified。
- 当前 Review Report 与 Product Spec hash 一致。

## 6. Artifact 验收清单

### 6.1 review-report

- PASS/PASS_WITH_CONDITIONS/REVISE/BLOCK 结论。
- task、revision、Product Spec ref/hash。
- 规则集版本与执行摘要。
- Finding 与条件引用。
- 证据抽检摘要。
- 否决项与 Human Checkpoint 审计摘要。
- UNVERIFIED 项和评审时间。

### 6.2 review-findings

- finding_id、rule_id 和 rule_version。
- 严重级别与规则结果。
- 事实、Artifact、证据和版本。
- 责任 Agent 与修复动作。
- 完成条件、复审范围和下游失效范围。

### 6.3 rule-results

- 各命名空间规则版本。
- 预期和实际执行数量。
- 每条规则的输入、执行器、结果和证据。
- 确定性验证引用。
- UNVERIFIED 规则及原因。
- 执行日志引用。

### 6.4 review-summary

- 当前结论和最重要依据。
- 阻断/修订原因或人类条件。
- 责任 Agent 和下一步。
- 需要 Human Manager 决定的事项。
- 已知限制和完成信号状态。

### 6.5 review-appeal-record（发生异议时）

- appeal_id 与被挑战 Finding。
- 异议论点和新增证据引用。
- 独立复审范围。
- overturned/maintained/partially_adjusted。
- 误判根因或维持依据。
- 人类升级状态。

不适用字段必须包含 `not_applicable_reason`。只写“不需要”不构成有效理由。

## 7. 缺陷等级

| 等级 | 定义 | 示例 | 处理 |
| --- | --- | --- | --- |
| critical | Reviewer 自身会放出重大风险、伪造审查或越权修改 | UNVERIFIED仍PASS；漏跑规则伪装完成；修改源Artifact；复用旧PASS；无规则BLOCK | `REVIEW_INVALID`，当前评审作废 |
| major | 足以改变评审结论或导致责任方无法整改 | 抽检不足；漏否决项；Finding无证据；异议未独立复审 | `REVISE_REVIEW`，新Review版本复核 |
| minor | 不改变主要结论，但降低审计或执行质量 | Info字段缺说明；非关键引用格式不一致 | 修复后继续，必须记录 |

任一 critical 或未关闭 major 缺陷都禁止进入 AcceptanceGate。

## 8. 常见错误模式

- 看到 Leader 推荐和多个 Agent 一致就降低审查强度。
- 读取其他 Agent 的推理过程并把它当证据。
- 未锁定 Product Spec hash，评审过程中输入变化仍继续。
- 只检查最终文档，不检查 Artifact Graph 和原始证据。
- 规则集没有版本，靠 Reviewer 临场经验阻断。
- 用抽检代替 Schema、版本、红线等确定性全检。
- 证据抽检比例不足20%，或只抽 Market 不抽 Supply/Economics。
- 没有记录随机种子，无法复现抽样。
- 发现一例伪造后仍维持抽检范围。
- 把 quoted、cached 或 synthetic 误写成确认事实却未发现。
- 把 Warning 或文案偏好升级为 REVISE/BLOCK。
- PASS_WITH_CONDITIONS 中混入实际规则失败。
- UNVERIFIED 项存在仍输出 PASS。
- Finding 使用“建议优化”“可能有问题”，没有事实和完成条件。
- 一条 Finding 同时要求多个 Agent 修复多个问题。
- Reviewer 直接修改 Product Spec 或 Economics 数字。
- 对新 revision 沿用旧 PASS 和旧抽样。
- BLOCK 异议维持后再次阻断，而不是升级人类。
- 修订超过3轮仍机械退回。
- 向 Leader 发送其未订阅的 Reviewer HANDOFF。
- 将当前 Finding 或未裁决伪造指控写入长期 Memory。

## 9. 评估输出格式

Reviewer 自检、Leader 或 AcceptanceGate 对 Review Artifact 的质量检查必须输出：

```yaml
reviewer_rubric_version: 1.0.0
root_task_id: laptop-stand-us-20260803-001
review_task_id: laptop-stand-us-20260803-001-review-01
revision: 1
product_spec_hash: sha256-placeholder
review_report_ref: review-report-v1
evaluator: acceptance-gate
gate_results:
  RVG01: {status: PASS, evidence_refs: [review-snapshot-v1]}
  RVG04: {status: PASS, evidence_refs: [rule-results-v1]}
  RVG05: {status: FAIL, evidence_refs: [sample-audit-v1], reason: sample_ratio_0_15}
score:
  status: not_scored
  reason: hard_gate_failed
defects:
  - id: RQDEF-001
    severity: major
    criterion: C1
    artifact_ref: review-report-v1
    finding: 证据抽检比例仅15%，低于20%门槛
    owner: gap2sku-reviewer
    required_action: 按相同总体重新执行分层抽样并生成新Review版本
result: REVISE_REVIEW
review_accepted: false
next_actions:
  - action: create_new_review_revision
    owner: gap2sku-product-architect
```

任一硬门禁失败时，`review_accepted` 必须为 false。Reviewer 不能自称 `REVIEW_ACCEPTED`。

## 10. Reviewer 提交前十二问

1. 当前 Task、revision、Product Spec hash、Artifact Graph 和规则版本是否已锁定？
2. 每条预期确定性规则是否真实执行并有日志？
3. 是否存在 UNVERIFIED、STALE 或缺失引用却仍准备 PASS？
4. 抽检比例是否达到20%，三个关键域是否都覆盖？
5. 抽样总体、方法、种子和样本ID是否可重放？
6. 发现伪造或错配时是否扩大到全量审计？
7. 否决项和强制 Human Checkpoint 是否独立复核？
8. 每条 Finding 是否原子、具体、有证据并能被责任 Agent 验收？
9. PASS_WITH_CONDITIONS 是否只包含明确的人类条件？
10. 是否修改、补造或重新解释了责任 Agent 的源 Artifact？
11. 新 revision 是否错误复用了旧 PASS、旧抽样或旧 hash？
12. 完成、失败、异议和人类升级是否走了对方实际接收的协议？

任一答案为“否”或“未知”，不得输出 Reviewer SELF_CHECK_PASS。

## 11. 回归测试用例

Reviewer 契约至少覆盖以下固定测试：

| 用例 | 预期结果 |
| --- | --- |
| 全规则与证据通过 | 四类 Review Artifact 提交，结论 PASS |
| 仅有明确人类商业条件 | PASS_WITH_CONDITIONS，AcceptanceGate 不直接放行 |
| 可修复引用断裂 | 原子 Finding + REVISION_REQUIRED |
| 强制认证不可核验 | COMPLIANCE_FLAG + BLOCK 或人类升级 |
| 抽检比例15% | Reviewer QA失败，不允许提交有效Review |
| 抽检发现一例伪造 | 扩大到全量证据审计 |
| 确定性工具不可用 | 标记UNVERIFIED，禁止PASS |
| 规则版本缺失 | RISK_ALERT，不用个人经验阻断 |
| Human Checkpoint被跳过 | REVISE并升级Human Manager |
| 第3轮仍失败 | 停止机械REVISE，输出立场摘要并升级人类 |
| BLOCK异议被推翻 | 记录overturned和误判根因，不隐藏历史 |
| BLOCK异议维持 | 不二次BLOCK，升级Human Manager |
| Product Spec hash变化 | 旧PASS失效，重新全检与抽检 |
| Reviewer尝试修改源Artifact | 权限拒绝、记录审计、评审停止 |
| synthetic证据冒充live | 发现数据模式违规，不允许PASS |

每次修改 Reviewer Prompt、Skill、Rule Set、抽检策略、Artifact Graph、Appeal 或 AcceptanceGate 后，都必须重跑这些用例。
