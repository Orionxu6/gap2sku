# Gap2SKU v3.0 实施报告

## 已实现

- TaskStore：状态、owner 守卫、依赖、幂等、revision、事件日志。
- ArtifactStore：payload 修复与兼容迁移、独立 refs/policy/schema/hash/data mode、不可变版本与引用硬失败。
- Artifact Graph：节点/边引用完整性、BFS 影响传播、旧版局部重规划回归。
- Governance：DecisionPolicy、ConflictCard、OptionCard、ReviewReport、DecisionBrief、ApprovalRecord、AcceptanceGate、FailureLoopback。
- 数据：四个 XLSX 共 389 条；记录 SHA-256、工作簿、Sheet、行号、来源与等级；65 行西诺思错列迁移、7 条精确重复标记。
- Agent 契约：五包规范化、缺失 Schema、Leader 文件名修复、模型/Skill/工具/预算/事件 fail-startup 校验。
- MCP：官方 SDK Streamable HTTP + 旧角色 JSON 兼容层。
- Workbench：项目/DAG、Evidence、Conflict/Option、Reviewer/Decision、Trace/Metrics 五个页面。
- RAG：SQLite FTS5 + 中文 substring fallback；KnowledgeCitation 与 EvidenceRecord 分离。
- 开放贡献：两个已通过 quick_validate 的 Skill。
- Cloud：uv.lock、Docker、Compose、doctor、bundle/manifest/verify。

## 本地验证结果（2026-08-12）

- `make check`：56 passed；coverage 88.63%；ruff/mypy 通过。
- `make demo-real`：389 Evidence、17 Artifact、4 Conflict、Reviewer REVISE、Decision REVISE、4 个补证 revision 任务。
- `make demo-synthetic`：GO/PASS，但全链明确标记 SYNTHETIC。
- `make demo-core`：16 Artifact、Reviewer PASS。
- `make demo-replan`：preserved 5，stale/recompute 11，Market calls 0。
- 五个 Agent 契约：valid，agent_count=5。

## 未在本机验证

- Cloud Studio 真实 AgentTeams v1.2.2 集群、Worker Ready/Active、Team Room 加入和 QwenPaw Skill 热加载。
- DashScope/Qwen 在线调用；本地闭环是确定性 Domain Core，不需要密钥。
- 真实 RFQ/BOM/打样/耐久/材料检测；因此真实案例禁止 GO。

## 已知非阻断警告

- pytest 有若干遗留 SQLite 连接 ResourceWarning；测试进程退出时由运行时回收，生产长驻进程持有连接。
- MCP 1.29.0 触发 pydantic-settings 的 forward-reference warning；官方 Streamable HTTP App 与工具注册 smoke test 已通过。
