#!/usr/bin/env bash
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
fail=0
echo "[cloud-doctor] required minimum: 4 CPU / 8 GiB RAM / 15 GiB free"

for command_name in docker uv curl unzip; do
  if command -v "${command_name}" >/dev/null 2>&1; then
    echo "[cloud-doctor] PASS command ${command_name}"
  else
    echo "[cloud-doctor] FAIL command ${command_name} missing"
    fail=1
  fi
done

cpu_count="$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 0)"
if [ "${cpu_count}" -ge 4 ] 2>/dev/null; then echo "[cloud-doctor] PASS CPU ${cpu_count}"; else echo "[cloud-doctor] FAIL CPU ${cpu_count}"; fail=1; fi
if [ -r /proc/meminfo ]; then
  mem_kib="$(awk '/MemTotal/{print $2}' /proc/meminfo)"
else
  mem_kib="$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 ))"
fi
if [ "${mem_kib}" -ge 8388608 ] 2>/dev/null; then echo "[cloud-doctor] PASS memory >= 8 GiB"; else echo "[cloud-doctor] FAIL memory < 8 GiB"; fail=1; fi
free_kib="$(df -Pk . | awk 'NR==2{print $4}')"
if [ "${free_kib}" -ge 15728640 ] 2>/dev/null; then echo "[cloud-doctor] PASS disk >= 15 GiB free"; else echo "[cloud-doctor] FAIL disk < 15 GiB free"; fail=1; fi

for port in 18080 18088 18090 8080; do
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[cloud-doctor] INFO port ${port} already in use"
  elif command -v ss >/dev/null 2>&1 && ss -ltn | awk '{print $4}' | grep -Eq "[:.]${port}$"; then
    echo "[cloud-doctor] INFO port ${port} already in use"
  else
    echo "[cloud-doctor] PASS port ${port} available"
  fi
done

if command -v docker >/dev/null 2>&1; then
  docker info >/dev/null 2>&1 && echo "[cloud-doctor] PASS Docker daemon" || { echo "[cloud-doctor] FAIL Docker daemon"; fail=1; }
  docker compose config >/dev/null 2>&1 && echo "[cloud-doctor] PASS docker compose config" || { echo "[cloud-doctor] FAIL compose config"; fail=1; }
  if docker ps --filter name=agentteams-manager --format '{{.Names}}' | grep -q '^agentteams-manager$'; then
    manager_image="$(docker inspect -f '{{.Config.Image}}' agentteams-manager 2>/dev/null || true)"
    case "${manager_image}" in
      *:v1.2.2) echo "[cloud-doctor] PASS AgentTeams Manager v1.2.2" ;;
      *) echo "[cloud-doctor] FAIL running AgentTeams image is not v1.2.2"; fail=1 ;;
    esac
  else
    echo "[cloud-doctor] INFO AgentTeams not installed yet; cloud_deploy will install v1.2.2"
  fi
fi
for url in https://pypi.org/simple/ https://raw.githubusercontent.com/agentscope-ai/AgentTeams/v1.2.2/install/agentteams-install.sh https://higress-registry.cn-hangzhou.cr.aliyuncs.com/v2/; do
  curl -I -L --connect-timeout 5 --max-time 10 -sS "${url}" >/dev/null 2>&1 \
    && echo "[cloud-doctor] PASS network ${url}" \
    || echo "[cloud-doctor] WARN network unavailable ${url}; prepare Linux wheelhouse/image mirror"
done

AGENTTEAMS_TAG="${AGENTTEAMS_TAG:-v1.2.2}" bash scripts/doctor.sh || fail=1
if [ -f .env.local ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi
if [ -n "${AGENTTEAMS_LLM_API_KEY:-}" ]; then echo "[cloud-doctor] PASS DeepSeek credential present (redacted)"; else echo "[cloud-doctor] WARN DeepSeek credential absent; real AgentTeams cannot run"; fi
if [ -n "${DASHSCOPE_API_KEY:-}" ]; then echo "[cloud-doctor] PASS DashScope credential present (redacted)"; else echo "[cloud-doctor] WARN DashScope absent; image.generate uses SYNTHETIC replay"; fi
if [ -n "${AGENTTEAMS_LLM_API_KEY:-}" ] || [ -n "${DASHSCOPE_API_KEY:-}" ]; then
  if [ -x .venv/bin/python ]; then
    PYTHONPATH=src .venv/bin/python -m gap2sku.cli.preflight_models || fail=1
  else
    echo "[cloud-doctor] INFO model preflight deferred until uv sync creates .venv"
  fi
fi
exit "${fail}"
