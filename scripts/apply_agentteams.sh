#!/usr/bin/env bash
# Compile seven strict Agent packages and apply Worker/Team CRs to local AgentTeams v1.2.2.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
RUNTIME="${DIR}/.runtime/agentteams"
APPLY="${RUNTIME}/agentteams-apply-v1.2.2.sh"
EXPECTED_APPLY_SHA="aaf5987828865de75f8c90bf83a762e7e8d4e195bc5a067a445d32281ecda8d9"
mkdir -p "${RUNTIME}"

PRESET_MCP_BASE_URL="${GAP2SKU_MCP_BASE_URL:-}"
if [ -f "${DIR}/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${DIR}/.env.local"
  set +a
fi

export MODEL_NAME="${MODEL_NAME:-qwen-plus}"
export LEADER_MODEL_NAME="${LEADER_MODEL_NAME:-${MODEL_NAME}}"
export MARKET_MODEL_NAME="${MARKET_MODEL_NAME:-${MODEL_NAME}}"
export SUPPLY_MODEL_NAME="${SUPPLY_MODEL_NAME:-${MODEL_NAME}}"
export ECONOMICS_MODEL_NAME="${ECONOMICS_MODEL_NAME:-${MODEL_NAME}}"
export REVIEWER_MODEL_NAME="${REVIEWER_MODEL_NAME:-${MODEL_NAME}}"
export PROTOTYPE_MODEL_NAME="${PROTOTYPE_MODEL_NAME:-${MODEL_NAME}}"
export COMPLIANCE_MODEL_NAME="${COMPLIANCE_MODEL_NAME:-${MODEL_NAME}}"
export GAP2SKU_MCP_BASE_URL="${PRESET_MCP_BASE_URL:-${GAP2SKU_MCP_BASE_URL:-http://host.docker.internal:18090}}"
export GAP2SKU_AGENT_CONTRACT_LOADER=strict
export DEMO_SEED="${DEMO_SEED:-20260812}"

docker ps --filter name=agentteams-manager --format '{{.Names}}' | grep -q '^agentteams-manager$' || {
  echo "[apply] AgentTeams Manager 未运行。先执行 make agentteams-install。" >&2
  exit 2
}
curl -fsS http://127.0.0.1:18090/health >/dev/null || {
  echo "[apply] Gap2SKU MCP 未运行。先执行 make local-up。" >&2
  exit 2
}

"${DIR}/.venv/bin/python" -m gap2sku.cli.contracts >/dev/null
"${DIR}/.venv/bin/python" -m gap2sku.cli.render_agentteams --out "${RUNTIME}"
"${DIR}/.venv/bin/python" -m gap2sku.cli.stage_agentteams_skills \
  --out "${RUNTIME}/staged-worker-skills" >/dev/null

if [ ! -f "${APPLY}" ]; then
  curl --http1.1 -fsSL \
    "https://raw.githubusercontent.com/agentscope-ai/AgentTeams/v1.2.2/install/agentteams-apply.sh" \
    -o "${APPLY}"
fi
actual_sha="$(shasum -a 256 "${APPLY}" | awk '{print $1}')"
[ "${actual_sha}" = "${EXPECTED_APPLY_SHA}" ] || {
  echo "[apply] 官方 apply 脚本 hash 不匹配；拒绝执行。" >&2
  exit 3
}
chmod 700 "${APPLY}"

docker exec agentteams-manager mkdir -p /tmp/import
for package in "${DIR}"/packages/*.zip; do
  docker cp "${package}" "agentteams-manager:/tmp/import/$(basename "${package}")"
done
docker exec agentteams-manager sh -lc 'mkdir -p "$HOME/worker-skills" /tmp/gap2sku-worker-skills'
docker cp "${RUNTIME}/staged-worker-skills/." agentteams-manager:/tmp/gap2sku-worker-skills/
docker exec agentteams-manager sh -lc 'cp -R /tmp/gap2sku-worker-skills/. "$HOME/worker-skills/"'

for config in "${RUNTIME}"/worker-*.yaml; do
  echo "[apply] Worker $(basename "${config}")"
  "${APPLY}" -f "${config}"
done

while IFS=$'\t' read -r worker skill; do
  [ -n "${worker}" ] && [ -n "${skill}" ] || continue
  pushed=0
  for attempt in 1 2 3 4 5; do
    if docker exec agentteams-manager bash \
      /opt/agentteams/agent/skills/worker-management/scripts/push-worker-skills.sh \
      --worker "${worker}" --add-skill "${skill}" --no-notify; then
      pushed=1
      break
    fi
    sleep 2
  done
  [ "${pushed}" -eq 1 ] || { echo "[apply] Skill ${skill} -> ${worker} failed" >&2; exit 4; }
done < <("${DIR}/.venv/bin/python" -c '
import json
report = json.load(open(".runtime/agentteams/skill-stage-report.json", encoding="utf-8"))
for worker, skills in sorted(report["assignments"].items()):
    for skill in skills:
        print(f"{worker}\t{skill}")
')

echo "[apply] QwenPaw role-scoped MCP exact allowlists"
"${DIR}/.venv/bin/python" -m gap2sku.cli.configure_worker_mcp

echo "[apply] Team team.yaml"
"${APPLY}" -f "${RUNTIME}/team.yaml"
if docker exec agentteams-manager agt get humans gap2sku-observer -o json >/dev/null 2>&1; then
  echo "[apply] Human Observer gap2sku-observer already exists; preserving Matrix identity"
else
  echo "[apply] Human Observer human-observer.yaml"
  "${APPLY}" -f "${RUNTIME}/human-observer.yaml"
fi
"${DIR}/.venv/bin/python" -m gap2sku.cli.connect_matrix --env "${DIR}/.env.local" --wait-seconds 180
"${DIR}/.venv/bin/python" -m gap2sku.cli.verify_agentteams
echo "[apply] 七个 QwenPaw Worker、十个 Skill 定义、Team 与 Observer 已提交并接入 Matrix。"
