# Gap2SKU v3.0 安装与 Cloud Studio 部署

## 本地日常启动

要求：Python 3.10+、`uv`、Docker、至少 4 CPU / 8 GiB RAM。AgentTeams 固定兼容 `v1.2.2`。

```bash
cd /Users/orionxu/Documents/gap2sku
make bootstrap
make configure-api
make model-preflight
make agentteams-install
make local-up
make agentteams-apply
make demo-agentteams
make local-status
```

入口：

- Decision Room：`http://127.0.0.1:8080/`
- Product Story：`http://127.0.0.1:8080/story`
- 使用指南：`http://127.0.0.1:8080/guide`
- Element 后台日志：`http://127.0.0.1:18088/`

Decision Room、Product Story 和使用指南不需要登录。Element 只在排障或会话失效时登录，用户名默认 `admin`；密码是 `make configure-api` 时设置的本地 Matrix 管理员密码，不是 API Key。

## API Key 边界

- `AGENTTEAMS_LLM_API_KEY`：DeepSeek，供七名文本 Worker 推理、工具调用和结构化 Handoff。
- `DASHSCOPE_API_KEY`：只供 Prototype Designer 的 `image.generate` 调用 Qwen Image。

建议始终运行 `make configure-api`，由不可见输入生成权限为 600 的 `.env.local`。不要把密钥写进 `.env.example`、聊天、日志或 Cloud ZIP。

## Cloud Studio

先上传并解压 `dist/gap2sku-v3.0.0-cloud.zip`，然后进入解压目录：

```bash
make configure-api
bash scripts/cloud_doctor.sh
bash scripts/cloud_deploy.sh
```

`cloud_deploy.sh` 的固定流程是：

1. 检查 Docker、CPU、内存、磁盘、端口和网络。
2. 通过 `uv.lock` 安装依赖；PyPI 失败时尝试目录 `wheelhouse/` 中的 Linux wheels。
3. 执行模型 preflight，且不记录密钥。
4. 停止旧 Workbench/MCP，生成午睡枕真实 `REVISE`、合成 `GO`、耐久 `NO-GO`、第二品类 `REVISE/GO` 和笔记本支架局部重规划证据。
5. 安装或校验 AgentTeams `v1.2.2`，自动解析 Linux Docker host gateway。
6. 以 `0.0.0.0` 启动 Workbench/MCP，应用七个 Worker、十个 Skill、Team 与 Observer。
7. 运行一次新的七员工 REAL 协作；只接受本次 run_id 的七个结构化 Handoff。
8. 逐项验证 Workbench LIVE/Matrix、MCP、Team Room、七 Worker、各业务分支和局部重规划。
9. 只有全部通过才写出 `evidence/cloud-studio-e2e.json`。

`cloud-studio-e2e.json` 不是无条件写入的“成功声明”。生成器会读取实际运行证据、检查时间下界和 run_id，并保存所有输入文件的 SHA-256；任一门禁失败都会以非零状态退出。

## 网络受限环境

- Python：把与 `uv.lock` 匹配的 Linux wheels 放入 `wheelhouse/`，部署脚本会在 PyPI 失败后使用离线模式。
- AgentTeams：仍需能访问官方安装脚本和 `higress-registry.cn-hangzhou.cr.aliyuncs.com` 镜像；若不可达，应在有网络的 Linux 环境预拉取并导出镜像，不能静默改用未固定版本。
- DeepSeek：真实七员工验收必须连通配置的官方 API；网络失败只能形成明确的 BLOCKED/DEGRADED，不能用回放冒充 REAL。

## 完成标准

本地 `make check`、`make verify-evidence` 和 `make verify-bundle` 不能替代 Cloud Studio 验收。只有云端生成并复核 `evidence/cloud-studio-e2e.json`，才能声明 Cloud Studio AgentTeams 端到端跑通。
