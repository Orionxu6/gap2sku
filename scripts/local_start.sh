#!/usr/bin/env bash
# Start Gap2SKU Workbench + MCP locally. AgentTeams remains a separate pinned Docker runtime.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
RUNTIME="${DIR}/.runtime"
mkdir -p "${RUNTIME}"
export PYTHONPATH="${DIR}/src"
if [ -f "${DIR}/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${DIR}/.env.local"
  set +a
fi
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || { echo "先运行 make bootstrap" >&2; exit 2; }
[ -f "${DIR}/shared/nap_pillow.db" ] && [ -f "${DIR}/evidence/nap-pillow/run.json" ] || bash "${DIR}/scripts/demo_real.sh" >/dev/null
BIND_HOST="${GAP2SKU_BIND_HOST:-127.0.0.1}"

start_service() {
  name="$1"; endpoint="$2"; shift 2
  pidfile="${RUNTIME}/${name}.pid"
  if curl -fsS "${endpoint}" >/dev/null 2>&1; then
    echo "[local] ${name} 已在 ${endpoint} 提供服务"
    return
  fi
  if [ -f "${pidfile}" ] && kill -0 "$(cat "${pidfile}")" 2>/dev/null; then
    echo "[local] ${name} 已运行 pid=$(cat "${pidfile}")"
    return
  fi
  nohup "$@" >"${RUNTIME}/${name}.log" 2>&1 &
  echo $! > "${pidfile}"
  echo "[local] 启动 ${name} pid=$!"
}

start_service mcp http://127.0.0.1:18090/health "${PY}" -m gap2sku.mcp_server --host "${BIND_HOST}" --port 18090 --db shared/nap_pillow.db
start_service workbench http://127.0.0.1:8080/api/status "${PY}" -m gap2sku.workbench --host "${BIND_HOST}" --port 8080 --db shared/nap_pillow.db

for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS http://127.0.0.1:18090/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8080/api/status >/dev/null 2>&1; then
    echo "[local] READY  Workbench http://127.0.0.1:8080  MCP http://127.0.0.1:18090"
    exit 0
  fi
  sleep 1
done
echo "[local] 启动超时；查看 ${RUNTIME}/workbench.log 和 ${RUNTIME}/mcp.log" >&2
exit 3
