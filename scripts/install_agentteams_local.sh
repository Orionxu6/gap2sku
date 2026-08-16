#!/usr/bin/env bash
# Install the pinned official AgentTeams v1.2.2 local Docker runtime.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="${DIR}/.runtime/agentteams"
INSTALLER="${RUNTIME}/agentteams-install-v1.2.2.sh"
EXPECTED_SHA="8ef28c5bf239a0af2d6b57b946ecee977bf39e6c874cd786b85c7bd094668f9d"
ENV_FILE="${DIR}/.env.local"
[ -f "${ENV_FILE}" ] || { echo "先运行 make configure-api" >&2; exit 2; }
set -a
# shellcheck disable=SC1091
source "${ENV_FILE}"
set +a
[ -n "${AGENTTEAMS_LLM_API_KEY:-}" ] || { echo "AGENTTEAMS_LLM_API_KEY 未配置" >&2; exit 2; }
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || { echo "缺少 .venv；先运行 make bootstrap" >&2; exit 2; }
echo "[preflight] 正在验证模型凭据与 ${AGENTTEAMS_DEFAULT_MODEL:-qwen-plus} 连通性（不会记录密钥）..."
PYTHONPATH="${DIR}/src" "${PY}" -m gap2sku.cli.preflight_models
docker info >/dev/null
mkdir -p "${RUNTIME}"
if [ ! -f "${INSTALLER}" ]; then
  curl -fsSL "https://raw.githubusercontent.com/agentscope-ai/AgentTeams/v1.2.2/install/agentteams-install.sh" -o "${INSTALLER}"
fi
actual_sha="$(shasum -a 256 "${INSTALLER}" | awk '{print $1}')"
[ "${actual_sha}" = "${EXPECTED_SHA}" ] || { echo "官方安装脚本 hash 不匹配；拒绝执行。" >&2; exit 3; }
chmod 700 "${INSTALLER}"

export AGENTTEAMS_NON_INTERACTIVE=1
export AGENTTEAMS_VERSION=v1.2.2
export AGENTTEAMS_LOCAL_ONLY=1
export AGENTTEAMS_LANGUAGE="${AGENTTEAMS_LANGUAGE:-zh}"
export AGENTTEAMS_LLM_PROVIDER="${AGENTTEAMS_LLM_PROVIDER:-openai-compat}"
export AGENTTEAMS_DEFAULT_MODEL="${AGENTTEAMS_DEFAULT_MODEL:-deepseek-v4-flash}"
export AGENTTEAMS_OPENAI_BASE_URL="${AGENTTEAMS_OPENAI_BASE_URL:-https://api.deepseek.com/v1}"
export AGENTTEAMS_MODEL_CONTEXT_WINDOW="${AGENTTEAMS_MODEL_CONTEXT_WINDOW:-1000000}"
export AGENTTEAMS_MODEL_MAX_TOKENS="${AGENTTEAMS_MODEL_MAX_TOKENS:-384000}"
export AGENTTEAMS_MODEL_REASONING="${AGENTTEAMS_MODEL_REASONING:-true}"
export AGENTTEAMS_MODEL_VISION="${AGENTTEAMS_MODEL_VISION:-false}"
export AGENTTEAMS_EMBEDDING_MODEL="${AGENTTEAMS_EMBEDDING_MODEL:-}"
export AGENTTEAMS_MANAGER_RUNTIME="${AGENTTEAMS_MANAGER_RUNTIME:-copaw}"
export AGENTTEAMS_DEFAULT_WORKER_RUNTIME="${AGENTTEAMS_DEFAULT_WORKER_RUNTIME:-qwenpaw}"
export AGENTTEAMS_ENV_FILE="${RUNTIME}/agentteams-manager.env"
export AGENTTEAMS_WORKSPACE_DIR="${RUNTIME}/manager-workspace"
export AGENTTEAMS_DASHBOARD=0
export AGENTTEAMS_PORT_GATEWAY=18080
export AGENTTEAMS_PORT_ELEMENT_WEB=18088
"${INSTALLER}" manager

docker ps --filter name=agentteams --format '{{.Names}}\t{{.Status}}'
echo "AgentTeams v1.2.2 已安装；下一步运行 make agentteams-apply。"
