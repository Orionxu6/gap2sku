#!/usr/bin/env bash
# Secure local dual-provider configuration. Secret input is never echoed or printed.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${DIR}/.env.local"

echo '=== 1/3 AgentTeams 文本员工（DeepSeek / OpenAI 兼容 API）==='
printf 'DeepSeek 模型 [deepseek-v4-flash]: '
read -r text_model
text_model="${text_model:-deepseek-v4-flash}"
case "${text_model}" in
  deepseek-v4-flash|deepseek-v4-pro) ;;
  sk-*|*API*KEY*|*api*key*)
    echo '检测到模型栏中疑似粘贴了 API Key；已拒绝保存。模型应为 deepseek-v4-flash。' >&2
    exit 2
    ;;
  *)
    echo '当前本地 AgentTeams 只接受 deepseek-v4-flash 或 deepseek-v4-pro。' >&2
    exit 2
    ;;
esac
printf 'DeepSeek Base URL [https://api.deepseek.com/v1]: '
read -r text_base_url
text_base_url="${text_base_url:-https://api.deepseek.com/v1}"
case "${text_base_url%/}" in
  https://api.deepseek.com|https://api.deepseek.com/v1) ;;
  *)
    echo 'DeepSeek Base URL 必须为 https://api.deepseek.com/v1。' >&2
    exit 2
    ;;
esac
printf 'DeepSeek API Key（供七名 Agent 推理、聊天、工具调用；输入不可见）: '
read -r -s text_api_key
printf '\n'
[ -n "${text_api_key}" ] || { echo "DeepSeek API Key 不能为空" >&2; exit 2; }

echo '=== 2/3 Prototype Designer 在线生图（Qwen Image / DashScope）==='
printf '启用在线 Qwen 生图？[Y/n]: '
read -r image_enabled
image_enabled="${image_enabled:-Y}"
image_api_key=""
image_model="qwen-image-2.0"
case "${image_enabled}" in
  n|N|no|NO)
    echo '在线生图已关闭；系统将使用固定离线图，并持续标记 SYNTHETIC_CONCEPT。'
    ;;
  *)
    printf 'Qwen 生图模型 [qwen-image-2.0]: '
    read -r image_model
    image_model="${image_model:-qwen-image-2.0}"
    case "${image_model}" in
      qwen-image-2.0|qwen-image-2.0-pro) ;;
      sk-*|*API*KEY*|*api*key*)
        echo '检测到生图模型栏中疑似粘贴了 API Key；已拒绝保存。' >&2
        exit 2
        ;;
      *)
        echo '当前生图适配器只接受 qwen-image-2.0 或 qwen-image-2.0-pro。' >&2
        exit 2
        ;;
    esac
    printf 'DashScope API Key（只供 image.generate；输入不可见）: '
    read -r -s image_api_key
    printf '\n'
    [ -n "${image_api_key}" ] || { echo "启用在线生图时 DashScope API Key 不能为空" >&2; exit 2; }
    [ "${image_api_key}" != "${text_api_key}" ] || {
      echo 'DeepSeek 与 DashScope 必须使用各自独立的 API Key；两项输入不能相同。' >&2
      exit 2
    }
    ;;
esac

echo '=== 3/3 本地 AgentTeams/Matrix 管理凭据 ==='
printf '本地 Matrix 管理员密码（至少 8 位，输入不可见）: '
read -r -s admin_password
printf '\n'
[ "${#admin_password}" -ge 8 ] || { echo "管理员密码至少 8 位" >&2; exit 2; }

umask 077
write_env() {
  printf '%s=' "$1"
  printf '%q' "$2"
  printf '\n'
}
{
  write_env MODEL_PROVIDER openai-compat
  write_env MODEL_NAME "${text_model}"
  write_env LEADER_MODEL_NAME "${text_model}"
  write_env MARKET_MODEL_NAME "${text_model}"
  write_env SUPPLY_MODEL_NAME "${text_model}"
  write_env ECONOMICS_MODEL_NAME "${text_model}"
  write_env REVIEWER_MODEL_NAME "${text_model}"
  write_env PROTOTYPE_MODEL_NAME "${text_model}"
  write_env COMPLIANCE_MODEL_NAME "${text_model}"
  write_env AGENTTEAMS_LLM_PROVIDER openai-compat
  write_env AGENTTEAMS_DEFAULT_MODEL "${text_model}"
  write_env AGENTTEAMS_LLM_API_KEY "${text_api_key}"
  write_env AGENTTEAMS_OPENAI_BASE_URL "${text_base_url}"
  write_env AGENTTEAMS_MODEL_CONTEXT_WINDOW 1000000
  write_env AGENTTEAMS_MODEL_MAX_TOKENS 384000
  write_env AGENTTEAMS_MODEL_REASONING true
  write_env AGENTTEAMS_MODEL_VISION false
  write_env AGENTTEAMS_EMBEDDING_MODEL ""
  write_env DASHSCOPE_API_KEY "${image_api_key}"
  write_env AGENTTEAMS_ADMIN_USER admin
  write_env AGENTTEAMS_ADMIN_PASSWORD "${admin_password}"
  write_env AGENTTEAMS_VERSION v1.2.2
  write_env AGENTTEAMS_LANGUAGE zh
  write_env AGENTTEAMS_MANAGER_RUNTIME copaw
  write_env AGENTTEAMS_DEFAULT_WORKER_RUNTIME qwenpaw
  write_env GAP2SKU_MCP_BASE_URL http://host.docker.internal:18090
  write_env ELEMENT_WEB_URL http://127.0.0.1:18088
  write_env MATRIX_HOMESERVER http://127.0.0.1:18080
  write_env MATRIX_ROOM_ID ""
  write_env MATRIX_OBSERVER_ACCESS_TOKEN ""
  write_env MATRIX_OBSERVER_USER_ID ""
  write_env MATRIX_ROLE_MAP_JSON "{}"
  write_env QWEN_IMAGE_ENDPOINT ""
  write_env QWEN_IMAGE_MODEL "${image_model}"
} > "${TARGET}"
chmod 600 "${TARGET}"
echo "配置已安全写入 ${TARGET}（权限 600，Git 已忽略）。"
echo "文本 Agent: openai-compat / ${text_model} / ${text_base_url}"
if [ -n "${image_api_key}" ]; then
  echo "在线生图: qwen / ${image_model}（独立 DashScope Key，已隐藏）"
else
  echo "在线生图: disabled（使用 SYNTHETIC_CONCEPT 离线回退图）"
fi
echo "密钥值未打印，也不会写入证据文件。"
