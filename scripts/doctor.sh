#!/usr/bin/env bash
# Phase 0: read-only environment audit.
# Checks Docker, AgentTeams, resources, ports, deps, model key existence.
# Never prints secret values.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${DIR}/evidence"
mkdir -p "${EVIDENCE_DIR}"
if [ -f "${DIR}/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${DIR}/.env.local"
  set +a
fi

ENV_FILE="${DIR}/evidence/environment.txt"
: > "${ENV_FILE}"

log() { echo "[doctor] $*" | tee -a "${ENV_FILE}"; }
pass() { echo "[doctor] PASS  $1" | tee -a "${ENV_FILE}"; }
fail() { echo "[doctor] FAIL  $1" | tee -a "${ENV_FILE}"; }
warn() { echo "[doctor] WARN  $1" | tee -a "${ENV_FILE}"; }

log "=== Gap2SKU Phase 0 Environment Audit ==="
log "Generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log ""

# --- OS / CPU / RAM ---
log "--- OS / Resources ---"
log "uname: $(uname -a)"
log "cpu_count: $(nproc 2>/dev/null || echo unknown)"
if command -v free >/dev/null 2>&1; then
  log "memory: $(free -h | awk '/^Mem:/{print $2" total, "$7" available"}')"
fi

# --- Python ---
log ""
log "--- Python ---"
if command -v python3 >/dev/null 2>&1; then
  log "python3: $(python3 --version 2>&1)"
  pass "python3 available"
else
  fail "python3 not found"
fi

# --- Docker ---
log ""
log "--- Docker ---"
if command -v docker >/dev/null 2>&1; then
  log "docker: $(docker --version 2>&1)"
  if docker info >/dev/null 2>&1; then
    pass "docker daemon reachable"
  else
    warn "docker installed but daemon not reachable"
  fi
else
  warn "docker not found (required for AgentTeams)"
fi

# --- AgentTeams ---
log ""
log "--- AgentTeams ---"
if docker ps --filter name=agentteams-manager --format '{{.Names}}' 2>/dev/null | grep -q '^agentteams-manager$'; then
  runtime_version="$(docker exec agentteams-manager sh -lc 'printf "%s" "${AGENTTEAMS_VERSION:-}"' 2>/dev/null)"
  log "manager runtime version: ${runtime_version:-unknown}"
  [ "${runtime_version}" = "v1.2.2" ] && pass "AgentTeams Manager v1.2.2 running" || fail "AgentTeams Manager version mismatch"
else
  warn "AgentTeams Manager container not installed or not running"
fi
log "AGENTTEAMS_TAG: ${AGENTTEAMS_TAG:-v1.2.2}"
if [ "${AGENTTEAMS_TAG:-v1.2.2}" = "v1.2.2" ]; then pass "AgentTeams version pinned to v1.2.2"; else fail "AgentTeams must be v1.2.2"; fi

# --- Python deps ---
log ""
log "--- Python Dependencies ---"
PY="${DIR}/.venv/bin/python"
if [ ! -x "${PY}" ]; then PY="python3"; fi
for pkg in pydantic mcp httpx starlette uvicorn pytest openpyxl yaml; do
  ver=$(${PY} -c "import ${pkg}; print(getattr(${pkg},'__version__','ok'))" 2>/dev/null)
  if [ -n "${ver}" ]; then
    log "${pkg}: ${ver}"
  else
    warn "${pkg}: not installed (run: make bootstrap)"
  fi
done

# --- Model key (existence only, never print value) ---
log ""
log "--- Model Key (existence check only) ---"
if [ -n "${AGENTTEAMS_LLM_API_KEY:-${MODEL_API_KEY:-${OPENAI_API_KEY:-${DASHSCOPE_API_KEY:-}}}}" ]; then
  pass "a model API key env var is set (value redacted)"
else
  warn "no model API key env var detected (set MODEL_API_KEY / OPENAI_API_KEY / DASHSCOPE_API_KEY)"
fi

# --- Ports ---
log ""
log "--- Ports ---"
for port in 18080 18088 18090 8080; do
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port}"; then
      warn "port ${port} already in use"
    else
      pass "port ${port} free"
    fi
  fi
  if command -v lsof >/dev/null 2>&1; then
    if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      warn "port ${port} already in use"
    else
      pass "port ${port} free"
    fi
  fi
done

log ""
log "--- Disk / Network preflight ---"
if command -v df >/dev/null 2>&1; then log "disk_available: $(df -h "${DIR}" | awk 'NR==2{print $4}')"; fi
if command -v curl >/dev/null 2>&1; then
  curl -fsSI --max-time 8 https://pypi.org/simple/ >/dev/null 2>&1 && pass "PyPI reachable" || warn "PyPI unreachable; dependency install requires network"
  registry_code="$(curl -sSI --max-time 8 -o /dev/null -w '%{http_code}' https://registry-1.docker.io/v2/ 2>/dev/null)"
  if [ "${registry_code}" = "200" ] || [ "${registry_code}" = "401" ]; then
    pass "Docker registry reachable"
  else
    warn "Docker registry unreachable (HTTP ${registry_code:-000})"
  fi
fi

# --- Result ---
log ""
log "=== Audit complete ==="
echo ""
echo "[doctor] Evidence written to ${ENV_FILE}"
echo "[doctor] Review results above. API key absence is expected until the final local AgentTeams step."
