#!/usr/bin/env bash
# demo-agentteams: Run first Spec V1 via AgentTeams/Matrix/TeamHarness.
# This command never reports success without a real AgentTeams runtime.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
export PYTHONPATH="${DIR}/src"
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || PY="python3"

EVIDENCE="${DIR}/evidence/demo-v1-run.txt"
mkdir -p "${DIR}/evidence"
: > "${EVIDENCE}"

if ! docker ps --filter name=agentteams-manager --format '{{.Names}}' 2>/dev/null | grep -q '^agentteams-manager$'; then
  echo "[demo-agentteams] BLOCKED: agentteams-manager container not running" | tee -a "${EVIDENCE}"
  "${PY}" -m gap2sku.cli.demo_agentteams --out "${EVIDENCE}" --blocked
  exit 2
fi

[ -f "${DIR}/.env.local" ] || { echo "[demo-agentteams] BLOCKED: .env.local missing" >&2; exit 2; }
set -a
# shellcheck disable=SC1091
source "${DIR}/.env.local"
set +a
[ -n "${MATRIX_OBSERVER_ACCESS_TOKEN:-}" ] || { echo "[demo-agentteams] BLOCKED: Matrix Observer not connected" >&2; exit 2; }
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="gap2sku-live-$(date -u +%Y%m%dT%H%M%SZ)-$$"
"${PY}" -m gap2sku.cli.demo_agentteams --out "${EVIDENCE}" --send --run-id "${RUN_ID}" 2>&1 | tee -a "${EVIDENCE}"
echo "[demo-agentteams] REAL advisory task sent; waiting for seven structured handoffs." | tee -a "${EVIDENCE}"
"${PY}" -m gap2sku.cli.verify_agentteams \
  --wait-events "${AGENTTEAMS_DEMO_WAIT_SECONDS:-1200}" \
  --after "${STARTED_AT}" \
  --run-id "${RUN_ID}" 2>&1 | tee -a "${EVIDENCE}"
echo "[demo-agentteams] PASS: seven runtime identities submitted structured evidence-bearing handoffs." | tee -a "${EVIDENCE}"
