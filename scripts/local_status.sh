#!/usr/bin/env bash
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for entry in "workbench|http://127.0.0.1:8080/api/status" "mcp|http://127.0.0.1:18090/health"; do
  name="${entry%%|*}"
  endpoint="${entry#*|}"
  pidfile="${DIR}/.runtime/${name}.pid"
  if [ -f "${pidfile}" ] && [ -n "$(cat "${pidfile}")" ] && kill -0 "$(cat "${pidfile}")" 2>/dev/null; then
    echo "[status] PASS ${name} pid=$(cat "${pidfile}")"
  elif curl -fsS "${endpoint}" >/dev/null 2>&1; then
    echo "[status] PASS ${name} endpoint=${endpoint} (external/untracked process)"
  else
    echo "[status] FAIL ${name} 未运行"
  fi
done
curl -fsS http://127.0.0.1:8080/api/status >/dev/null 2>&1 && echo "[status] PASS Workbench API" || echo "[status] FAIL Workbench API"
curl -fsS http://127.0.0.1:18090/health >/dev/null 2>&1 && echo "[status] PASS MCP API" || echo "[status] FAIL MCP API"
if docker info >/dev/null 2>&1; then
  docker ps --filter name=agentteams --format '[status] {{.Names}} {{.Status}}'
  if docker ps --filter name=agentteams-manager --format '{{.Names}}' | grep -q '^agentteams-manager$'; then
    PY="${DIR}/.venv/bin/python"
    if [ -x "${PY}" ] && PYTHONPATH="${DIR}/src" "${PY}" -m gap2sku.cli.verify_agentteams --no-write >/dev/null 2>&1; then
      echo "[status] PASS AgentTeams 7 Workers / Team / Observer"
    else
      echo "[status] FAIL AgentTeams runtime resources incomplete"
    fi
  fi
else
  echo "[status] WARN Docker daemon 不可达"
fi
