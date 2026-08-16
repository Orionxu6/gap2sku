#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for name in workbench mcp; do
  pidfile="${DIR}/.runtime/${name}.pid"
  stopped=0
  if [ -f "${pidfile}" ]; then
    pid="$(cat "${pidfile}")"
    if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
      command="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
      if [[ "${command}" == *"gap2sku.${name}"* ]] || { [ "${name}" = "mcp" ] && [[ "${command}" == *"gap2sku.mcp_server"* ]]; }; then
        kill "${pid}"
        stopped=1
      fi
    fi
    : > "${pidfile}"
  fi
  port=8080
  module="gap2sku.workbench"
  if [ "${name}" = "mcp" ]; then port=18090; module="gap2sku.mcp_server"; fi
  listener="$(lsof -nP -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [ -n "${listener}" ] && kill -0 "${listener}" 2>/dev/null; then
    command="$(ps -p "${listener}" -o command= 2>/dev/null || true)"
    if [[ "${command}" == *"${module}"* ]]; then
      kill "${listener}"
      stopped=1
    fi
  fi
  if [ "${stopped}" -eq 1 ]; then echo "[local] 已停止 ${name}"; fi
done
