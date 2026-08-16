# Gap2SKU v3.0

Gap2SKU 是品类无关的“新品立项到打样决策防火墙”。它不替代 Accio 等上游研究/找品工具，而是把用户构思、市场证据、供应事实、成本、合规和样品验证组织成可审计的 `Decision-to-Sample Pack`。

## 审核入口

- [审核快照 Demo](https://gap2sku-review-production.up.railway.app)：公网只读回放，可查看三个已生成项目、7/7 Handoff、Artifact、冲突卡和 REVISE/GO/NO-GO 分支。
- [GitHub 仓库](https://github.com/Orionxu6/gap2sku)：完整可复现项目代码与部署配置。

审核快照不调用本机 DeepSeek/Qwen API、Matrix 或 Docker；评委输入不会触发新运行，所有展示内容来自已生成且版本化的快照。

平台支持三种入口：发现新品机会、验证已有概念、升级现有 SKU。午睡枕只是数据最完整的演示项目，通用领域模型使用 `CategoryProfile`、`ResearchPlan`、`SampleSpecTemplate` 和 `CompliancePolicyPack`，不依赖枕头专属字段。

最终结论有三类业务状态：

- `GO`：确定性门禁通过，仍需人工绑定 `spec_hash + policy_version` 审批。
- `REVISE`：方向值得继续，但必须补报价、BOM、测试、材料或合规证据。
- `NO-GO`：例如关键耐久/安全测试在修订后重复失败，应停止当前方案。

`BLOCKED` 仅表示系统、任务、数据或审批未就绪，不是业务 NO-GO。聊天消息也不是业务状态事实；只有结构化事件、Artifact、规则与审批可以推进状态。

## 当前可验证结果

- 午睡枕真实路径：389 条定向采样评论、38 个 Artifact、3 个概念，缺真实 RFQ/BOM/耐久/材料检测，确定性结论为 `REVISE`。
- 午睡枕合成路径：供应、成本、测试均持续标记 `SYNTHETIC`，用于演示 `GO + Human Approval`。
- 重复耐久失败：第 3 轮关键耐久失败得到 `NO-GO`。
- 笔记本支架 Golden Regression：16 个 Artifact、Reviewer `PASS`；成本变更局部重规划时 Market 调用为 0。
- 第二品类（成人桌边耳机与线材挂架）公开信号路径：3 条带 URL、时间和 hash 的供应线索、24 个 Artifact、3 个概念、3 张品类专属冲突卡；公开展示价不进入验证利润，结论 `REVISE`。
- 第二品类全合成回归：25 个 Artifact、3 张已解决的合成冲突卡、绑定规格与政策的合成人工批准，结论 `GO`；所有报价、成本、测试与图片持续标记 `SYNTHETIC`。
- 工程门禁：`ruff`、全量 strict `mypy`、全量测试和 85% 以上覆盖率。

## 无 API Key 的本地演示

```bash
make bootstrap
make check
make demo-real
make demo-synthetic
make demo-nogo
make demo-core
make demo-replan
make demo-new-category
make demo-new-category-synthetic
make local-up
```

打开 [Decision Room](http://127.0.0.1:8080/)；最终方案在 [Product Story](http://127.0.0.1:8080/story)；完整入口说明在 [网页使用指南](http://127.0.0.1:8080/guide)。Decision Room 顶部项目按钮可切换午睡枕真实证据、桌边耳机挂架公开信号和桌边耳机挂架合成回归；员工协作流、目标约束、冲突、结论、Artifact 和 Product Story 会作为同一个版本化项目一起切换。

日常使用不需要登录：Decision Room 是主入口，Product Story 是成果入口。只有需要核对 Matrix 原始房间消息、Worker 在线状态或排障时才打开 `http://127.0.0.1:18088/` 的 AgentTeams / Element 后台。用户名是本地 Matrix 管理员账号；密码是 `make configure-api` 时设置的本地管理员密码，不是任何 API Key。更详细的启动、切换和排障步骤见 [使用入口与登录说明](docs/使用入口与登录说明.md)。

MCP 健康检查位于 `http://127.0.0.1:18090/health`。七个角色使用互相隔离的官方 Streamable HTTP MCP：`/mcp/{market|prototype|supply|economics|compliance|review|leader}/mcp`；旧 `/{role}/mcp` 仅作兼容层。

## 最后一步：真实本地 AgentTeams

完成离线链和页面检查后再配置密钥。配置脚本会明确要求两套彼此独立的凭据：DeepSeek Key 供七名 AgentTeams 文本 Worker 推理、聊天、工具调用和结构化交接；DashScope Key 只供 Gap2SKU `image.generate` 使用 `qwen-image-2.0` 生成概念图。Prototype Designer 本身仍由 DeepSeek 推理，再通过 MCP 调用 Qwen 生图。脚本使用不可见输入，写入权限为 600 的 `.env.local`，不会把密钥写入仓库或证据文件。

```bash
make configure-api
make model-preflight
make local-up
make agentteams-install
make agentteams-apply
make agentteams-verify
make demo-agentteams
make local-status
```

本地运行固定兼容 AgentTeams `v1.2.2`：LLM 供应商使用 `openai-compat`，默认文本模型为 `deepseek-v4-flash`，Base URL 为 `https://api.deepseek.com/v1`；Manager 与七名 Worker 的运行时名称仍是 QwenPaw（旧名 CoPaw），这只是 Agent 引擎名称，不表示文本模型是千问。记忆搜索保持关闭，Gap2SKU 自己的 SQLite FTS5 检索可离线复现。`model-preflight` 只记录 provider、model、响应状态和耗时，不记录密钥，也不会为了预检而产生付费图片；安装脚本会自动再次检查文本模型。`agentteams-apply` 会编译七个严格 Agent 契约、上传十个 Skill、创建 Team 与 Human Observer并建立 Matrix 身份映射。`demo-agentteams` 默认最多等待 20 分钟，且必须等本轮开始时间之后七名 Worker 都提交以 `evt-agentteams-` 标识的 REAL 结构化 Handoff 才能 PASS；历史回放、旧运行和仅发送聊天消息都不会成功。

Qwen 生图通过官方 DashScope 多模态生成接口按需调用 `qwen-image-2.0`。返回图片会立即下载到本地、计算 SHA-256，并与 `RenderPromptRecord`、`SampleSpec hash`、模型和版本一起登记；在线失败会显式产生 `MODEL_DEGRADED` 并使用带 `SYNTHETIC_CONCEPT` 标识的离线回退图，而不会把概念图冒充 CAD、样品或安全证据。当前仓库已验证离线回退与 manifest 链路；在用户单独授权发送派生提示词并承担费用前，不声明 DashScope 在线生图已实测。

在上述命令真正通过前，本 README 不声明“AgentTeams 端到端已跑通”。

## 七名 Agent 的职责

| Agent | 主要产出 | 不得越权 |
|---|---|---|
| Product Architect / Leader | 任务编排、三概念取舍、冲突卡、最终 Decision-to-Sample Pack | 不创造专业事实，不绕过规则 |
| Market | 评论/竞品/价格/趋势、痛点与机会地图 | 不把评论写成供应能力 |
| Prototype Designer | 三个概念、SampleSpec 草案、效果图和标注板 | 概念图不是 CAD 或安全证据 |
| Supply | 制造边界、供应商漏斗、RFQ、报价和打样计划 | 无真实回函时必须 MISSING |
| Economics | BOM、费用、利润与敏感性 | 无真实报价时不得写“已验证利润” |
| Compliance & Safety | 分类、材料、测试、标签、包装和宣称矩阵 | 检索知识不能自动升级为结论 |
| Reviewer | 痛点覆盖、证据、制造、利润、合规、测试和图规一致性 | 只读，不得改产品方案 |

## Product Story

同一 `ProductStoryBundle` 生成内部完整版、供应商 RFQ 脱敏版和评委演示版。HTML 是唯一内容源，通过打印样式导出 PDF；不再维护易分叉的 DOCX。概念图持续显示 `SYNTHETIC_CONCEPT`，最终页面只引用与当前 `SampleSpec hash` 一致的版本。

## 主要证据

- `evidence/nap-pillow/run.json`：真实 Decision Brief 与 Decision-to-Sample Pack。
- `evidence/nap-pillow/import-report.json`：四个工作簿的分布、错位迁移、重复和来源覆盖。
- `evidence/nap-pillow/no-go-run.json`：重复关键耐久失败分支。
- `evidence/nap-pillow/artifact-graph.json`：引用关系和版本节点。
- `evidence/agent-contract-report.json`：七个 Agent 的契约一致性报告。
- `evidence/agentteams-runtime-verification.json`：本地七 Worker、Team、Observer 和 Handoff 验收（运行后产生）。
- `evidence/new-category-public/run.json`：第二品类公开供应信号 `REVISE` 路径（24 个 Artifact）。
- `evidence/new-category-synthetic/run.json`：第二品类全合成 `GO` 回归路径（25 个 Artifact）。
- `evidence/design-qa.md`：前端视觉与交互验收。

## 1688 牛顿与外部供应商

Supply 的 `supplier.discover` 只返回 `PUBLIC_LISTING_SIGNAL`；`rfq.import_response` 只有在供应商回复与当前 `RFQ + SampleSpec hash + 原始文件 SHA-256` 一致时才生成 `SupplierQuoteSet`。公开列表价、平台推荐价和供应商自述都不能直接成为验证成本或制造能力。1688 牛顿的建议接法、当前证据边界和脱敏导出格式见 [docs/ALIBABA_NEWTON_INTEGRATION.md](docs/ALIBABA_NEWTON_INTEGRATION.md)。

## 数据与安全边界

- 原始工作簿保持不可变并以 SHA-256 登记；389 条评论不进入公开贡献包。
- 登录态平台只使用授权 API/MCP、用户导出或明确授权的数据，不绕过登录与反爬。
- `KnowledgeCitation` 与业务 `EvidenceRecord` 分离；检索文本不能授权供应、成本、合规或 GO。
- 系统不会自动联系供应商、下单、付款、提交认证或发布商品。
- `.env.local`、密钥、本地数据库和未经脱敏的数据均不得提交。

Cloud Studio 先在解压目录执行 `make configure-api`，再运行 `bash scripts/cloud_doctor.sh` 与 `bash scripts/cloud_deploy.sh`。部署脚本会先安装锁定依赖、停止旧服务再生成数据库，随后自动解析 Linux Docker host gateway，以 `0.0.0.0` 启动 Workbench/MCP，应用七个 Worker 并运行新的 REAL 协作。只有逐项验证器确认本轮 run_id 的 7/7 Handoff、LIVE Matrix、七角色 MCP、真实/合成/NO-GO/第二品类/局部重规划全部通过，才会写出 `evidence/cloud-studio-e2e.json`。完整步骤见 [安装与 Cloud Studio 部署](docs/INSTALL.md)。

本地执行 `make package-v3 && make verify-bundle` 会生成 `dist/gap2sku-v3.0.0-cloud.zip`。总包同时内嵌两个可独立安装的开放贡献包：`contributions/packages/agent-contract-validation.zip` 与 `contributions/packages/evidence-conflict-decision.zip`；本地副本位于 `dist/skills/`。总包不包含 `.env.local`、API Key 或运行数据库。

## License

Apache-2.0。第三方组件见 `THIRD_PARTY_NOTICES.md`。
