# AgentTeams Manager 创建消息（参照 opspilot-zero-demo 成功模式重写）

> 本消息必须发送到 Element Web 的 `manager` 房间，由 manager 串行创建 5 个业务 Worker，
> 并在创建 Team 时生成一个独立 TeamLeader Worker `gap2sku-product-architect`。
> 发送前把下面所有 `<GAP2SKU_MCP_BASE_URL>` 替换为 Docker Worker 可访问的地址：
> `http://172.18.0.1:18090`
>
> 关键差异（这是之前跑不通的根因）：
> - 所有 Worker 必须使用 **qwenpow（copow / QwenPaw）** 运行时，不能用 openclaw。
> - Worker 由 manager 在本房间内联创建，不依赖宿主机 `package:` 文件。
> - 工具契约直接内联为 HTTP 调用，指向 Gap2SKU MCP 网关。

## 统一工具调用协议

Gap2SKU 使用自建 MCP 网关（已在本机 `0.0.0.0:18090` 启动）。每个角色有独立 endpoint：

```text
POST <GAP2SKU_MCP_BASE_URL>/{role}/mcp
Content-Type: application/json
body: {"tool": "<tool_name>", "args": { ... }}
```

返回：`{"ok": true, "role": "<role>", "tool": "<tool_name>", "result": { ... } }`

角色 endpoint：`/market/mcp` `/supply/mcp` `/economics/mcp` `/review/mcp` `/leader/mcp`

## 复制到 Manager 的完整创建请求

```text
请为 Gap2SKU Demo 创建 5 个业务 Worker 和 1 个 Team。创建 Team 时，必须由 manager 创建一个独立 Worker 作为 TeamLeader。以下内容是完整创建脚本，请严格按顺序执行，不要并行创建。

全局创建约束：
1. 所有 Worker 必须使用 qwenpow（copow；安装器或界面中也可能显示为 QwenPaw）运行时创建，并使用 AgentTeams 当前配置的真实 LLM。
2. 必须逐个创建 Worker，禁止并行创建多个 Worker。
3. 业务 Worker 创建顺序必须是：market -> supply -> economics -> reviewer，最后 product-architect 作为 TeamLeader。
4. 每创建完成一个 Worker 后，必须确认该 Worker 创建成功且可以正常运行，再创建下一个 Worker。
5. 创建 gap2sku-definition Team 时，必须创建一个新的独立 Worker 作为 TeamLeader，名称必须是 gap2sku-product-architect。
6. 禁止把 market、supply、economics 或 reviewer 直接指定为 leader。
7. 必须等 4 个业务 Worker 全部创建完成并确认正常运行后，才允许创建 gap2sku-definition Team。
8. Worker 初始化可能拉起容器运行时并写入依赖；并行创建会造成高 I/O 消耗，低规格机器可能因此阻塞，所以不要为了提速而并行执行。
9. 4 个业务 Worker 的 AgentSpec、Skill、工具契约都在本消息中内联，不依赖 Worker 读取宿主机目录中的文件。
10. 所有工具数据都通过 Gap2SKU MCP 网关获取，基础地址为 <GAP2SKU_MCP_BASE_URL>。

统一工具调用协议：
POST <GAP2SKU_MCP_BASE_URL>/{role}/mcp  body: {"tool":"<name>","args":{...}}

============================================================
Step 1. 创建 Worker: gap2sku-market
============================================================

请创建一个名为 gap2sku-market 的 Worker，作为 Gap2SKU 的 Market Evidence Agent。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 通过 MCP 网关主动查询证据，不要要求用户补齐评论、竞品或痛点数据。

AgentSpec:
name: gap2sku-market
mission: 证明用户痛点真实、频繁、值得解决。输出 EvidenceSet + PainPointSet + FeatureHypotheses。
skills:
- market-evidence-mining: 归并评论、竞品与痛点，形成有证据支撑的特征假设。
tool contracts:
- fixtures.list_snapshots: POST <GAP2SKU_MCP_BASE_URL>/market/mcp body {"tool":"fixtures.list_snapshots","args":{}}
- evidence.search_reviews: POST <GAP2SKU_MCP_BASE_URL>/market/mcp body {"tool":"evidence.search_reviews","args":{"keyword":null}}
- evidence.get_competitor_records: POST <GAP2SKU_MCP_BASE_URL>/market/mcp body {"tool":"evidence.get_competitor_records","args":{}}
- state.get_constraints: POST <GAP2SKU_MCP_BASE_URL>/market/mcp body {"tool":"state.get_constraints","args":{}}
- artifact.validate_local: POST <GAP2SKU_MCP_BASE_URL>/market/mcp body {"tool":"artifact.validate_local","args":{}}
rules:
- 每个痛点必须有 evidence_ids。
- 频率必须有分子、分母、方法。
- synthetic 数据必须标注，不得表述为真实 Amazon 数据。
- 不得推断供应能力或成本。
- 数据缺失返回 BLOCKED。

完成 gap2sku-market 创建后，请确认它创建成功且可正常运行，再继续 Step 2。

============================================================
Step 2. 创建 Worker: gap2sku-supply
============================================================

请创建一个名为 gap2sku-supply 的 Worker，作为 Gap2SKU 的 Supply Capability Agent。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。

AgentSpec:
name: gap2sku-supply
mission: 证明 Feature 在采购约束下可实现。输出 SupplierCapabilitySet + SupplierAssessment。
skills:
- supplier-capability-assessment: 评估供应商能力并产出供应商评估。
tool contracts:
- fixtures.list_snapshots: POST <GAP2SKU_MCP_BASE_URL>/supply/mcp body {"tool":"fixtures.list_snapshots","args":{}}
- evidence.get_supplier_records: POST <GAP2SKU_MCP_BASE_URL>/supply/mcp body {"tool":"evidence.get_supplier_records","args":{}}
- state.get_constraints: POST <GAP2SKU_MCP_BASE_URL>/supply/mcp body {"tool":"state.get_constraints","args":{}}
- artifact.get_feature_hypotheses: POST <GAP2SKU_MCP_BASE_URL>/supply/mcp body {"tool":"artifact.get_feature_hypotheses","args":{}}
- artifact.validate_local: POST <GAP2SKU_MCP_BASE_URL>/supply/mcp body {"tool":"artifact.validate_local","args":{}}
rules:
- platform_visible 不得写成 human_confirmed。
- 冲突信息保留双方，标 CONFLICT，不得任选一个当事实。
- 不得声称市场需求强弱。

完成 gap2sku-supply 创建后，请确认它创建成功且可正常运行，再继续 Step 3。

============================================================
Step 3. 创建 Worker: gap2sku-economics
============================================================

请创建一个名为 gap2sku-economics 的 Worker，作为 Gap2SKU 的 Unit Economics Agent。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 金额计算必须调用 economics.calculate / economics.verify 工具，LLM 不得自行算钱。

AgentSpec:
name: gap2sku-economics
mission: 用确定性 Decimal 代码验证单位经济。LLM 不算成本/毛利/约束。
skills:
- unit-economics-evaluation: 用确定性代码评估单位经济。
tool contracts:
- state.get_constraints: POST <GAP2SKU_MCP_BASE_URL>/economics/mcp body {"tool":"state.get_constraints","args":{}}
- economics.calculate: POST <GAP2SKU_MCP_BASE_URL>/economics/mcp body {"tool":"economics.calculate","args":{"retail_price":"39.99","factory_cost":"8.00","moq":300}}
- economics.verify: POST <GAP2SKU_MCP_BASE_URL>/economics/mcp body {"tool":"economics.verify","args":{}}
- artifact.validate_local: POST <GAP2SKU_MCP_BASE_URL>/economics/mcp body {"tool":"artifact.validate_local","args":{}}
rules:
- 金额用 Decimal，JSON 为十进制字符串。
- 缺失输入返回 BLOCKED，不用 LLM 补齐。
- calculation_trace 必须非空。
- 硬约束返回机器可读 PASS/FAIL。

完成 gap2sku-economics 创建后，请确认它创建成功且可正常运行，再继续 Step 4。

============================================================
Step 4. 创建 Worker: gap2sku-reviewer
============================================================

请创建一个名为 gap2sku-reviewer 的 Worker，作为 Gap2SKU 的独立 Reviewer Agent。

创建要求：
- 运行时必须使用 qwenpow（copow；也可能显示为 QwenPaw）。
- 使用 AgentTeams 当前配置的真实 LLM。
- 不读取宿主机文件路径，以下内容就是完整 AgentSpec。
- 只返回 PASS / REVISE / BLOCK + Rule ID + Spec Hash，只读不写。

AgentSpec:
name: gap2sku-reviewer
mission: 独立质疑证据、约束、一致性。只返回 PASS/REVISE/BLOCK + Rule ID + Spec Hash。
skills:
- evidence-review-gate: 运行 R001-R012 评审门禁。
tool contracts:
- review.run_rules: POST <GAP2SKU_MCP_BASE_URL>/review/mcp body {"tool":"review.run_rules","args":{}}
- graph.get_subgraph: POST <GAP2SKU_MCP_BASE_URL>/review/mcp body {"tool":"graph.get_subgraph","args":{"feature_id":null}}
rules:
- LLM 不得覆盖确定性 BLOCK。
- 不得编辑 Spec 或写项目状态。
- 缺 Rule ID 或 Spec Hash 时 Leader 不得接受。
- 不得输出新的无证据 Feature。

完成 gap2sku-reviewer 创建后，请确认 4 个业务 Worker 都创建成功且可正常运行，再继续 Step 5。

============================================================
Step 5. 创建 Team: gap2sku-definition
============================================================

在确认以下 4 个业务 Worker 都创建成功且可正常运行后，再创建 Team：
1. gap2sku-market
2. gap2sku-supply
3. gap2sku-economics
4. gap2sku-reviewer

请创建一个名为 gap2sku-definition 的 Team，包含以上 4 个业务 Worker。

Team 创建要求：
- 创建 Team 时，必须创建一个新的独立 Worker 作为 TeamLeader，名称必须是 gap2sku-product-architect。
- 禁止把 market、supply、economics 或 reviewer 直接指定为 leader。
- 4 个业务 Worker 只作为被 TeamLeader 调度的专业角色参与 Team，不承担 TeamLeader 身份。

gap2sku-product-architect（TeamLeader）AgentSpec：
name: gap2sku-product-architect
mission: 拆解、取舍、验收、版本化 Product Spec。不绕过确定性 gate 和硬约束。
skills:
- product-spec-synthesis: 综合各方产物合成产品规格。
- impact-aware-replanning: 变更约束时做选择性重规划。
tool contracts:
- state.create_run: POST <GAP2SKU_MCP_BASE_URL>/leader/mcp body {"tool":"state.create_run","args":{"project_id":"laptop-stand-us-20260803-001"}}
- state.get_project: POST <GAP2SKU_MCP_BASE_URL>/leader/mcp body {"tool":"state.get_project","args":{}}
- state.get_constraints: POST <GAP2SKU_MCP_BASE_URL>/leader/mcp body {"tool":"state.get_constraints","args":{}}
- context.build_bundle: POST <GAP2SKU_MCP_BASE_URL>/leader/mcp body {"tool":"context.build_bundle","args":{}}
- graph.get_subgraph: POST <GAP2SKU_MCP_BASE_URL>/leader/mcp body {"tool":"graph.get_subgraph","args":{"feature_id":null}}
rules:
- 只有 Leader 可提交项目级 Artifact (ProductSpec, FeatureDecision)。
- Worker SUCCESS != Leader ACCEPT；必须校验 schema + artifact refs。
- 修订创建新 Task ID，不覆盖已接受任务。
- LLM 不算钱；用 economics.calculate 工具。

团队运行规则：
- 收到 Laptop Stand 定义任务后，TeamLeader 调度：
  1. market 归并评论，输出痛点 + Feature 假设。
  2. supply 评估供应商能力，输出 SupplierAssessment。
  3. economics 用确定性代码计算单位经济。
  4. product-architect 综合 Spec V1 + FeatureDecisions。
  5. reviewer 运行 R001-R012，输出 ReviewResult。
- 低风险动作可自动；发布 Spec 需 Human Approval。
- 每次只处理一个项目；处理完成后输出 Spec + Review + Artifact Graph。

请同时创建或确认该 Team 对应的 Matrix Team 房间，并在创建完成后告诉我房间名称或入口，以及需要 @ 的 team_leader_name。

全部创建完成后，输出创建结果摘要，包含：
- 5 个 Worker 创建状态和运行时类型。
- Team 创建时生成的独立 TeamLeader Worker 名称和运行时类型，必须单独列出 gap2sku-product-architect。
- gap2sku-definition Team 的创建状态。
- TeamLeader 指定结果，必须显示 gap2sku-product-architect 是 TeamLeader。
- Matrix 会话列表中名称以 Team 开头、对应 gap2sku-definition 的 Team 房间名称或入口。
- 需要在 Team 房间中 @ 的 team_leader_name。
- 提醒用户后续任务必须进入 Team 房间后，通过 @<team_leader_name> 的消息发送，不要发送给 manager。
```
