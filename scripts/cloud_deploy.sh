#!/usr/bin/env bash
# Reproducible Cloud Studio sequence. No supplier contact, order or payment occurs.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
CLOUD_RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

bash scripts/cloud_doctor.sh

if ! uv sync --frozen --all-extras; then
  if [ -d "${DIR}/wheelhouse" ] && find "${DIR}/wheelhouse" -name '*.whl' -print -quit | grep -q .; then
    echo "[cloud-deploy] PyPI sync failed; retrying from Linux wheelhouse"
    UV_NO_INDEX=1 UV_FIND_LINKS="${DIR}/wheelhouse" uv sync --frozen --all-extras --offline
  else
    echo "[cloud-deploy] dependency sync failed and no Linux wheelhouse is available" >&2
    exit 2
  fi
fi

[ -f "${DIR}/.env.local" ] || {
  echo "[cloud-deploy] missing .env.local; run make configure-api in this Cloud Studio terminal" >&2
  exit 2
}
make model-preflight

if ! find private/raw_reviews -name '*.xlsx' -print -quit 2>/dev/null | grep -q .; then
  mkdir -p private/raw_reviews
  unzip -n private/source_data/学生午睡枕-竞品评论信息-8.11.zip -d private/raw_reviews
fi

# Never replace a SQLite file while an older Workbench/MCP process still owns it.
make local-down
make check
make demo-real
make demo-synthetic
make demo-nogo
make demo-core
make demo-new-category
make demo-new-category-synthetic
make demo-replan

if ! docker ps --filter name=agentteams-manager --format '{{.Names}}' | grep -q '^agentteams-manager$'; then
  make agentteams-install
fi

# Docker Desktop resolves host.docker.internal; native Linux usually needs the
# actual bridge gateway. Preserve this exported value when agentteams-apply
# loads the remaining secrets from .env.local.
if docker exec agentteams-manager getent hosts host.docker.internal >/dev/null 2>&1; then
  MCP_HOST="host.docker.internal"
else
  MCP_HOST="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{println .Gateway}}{{end}}' agentteams-manager | awk 'NF{print; exit}')"
  [ -n "${MCP_HOST}" ] || { echo "[cloud-deploy] cannot resolve Docker host gateway" >&2; exit 3; }
fi
export GAP2SKU_MCP_BASE_URL="http://${MCP_HOST}:18090"
export GAP2SKU_BIND_HOST="0.0.0.0"

make local-up
make agentteams-apply
make agentteams-verify
make demo-agentteams
make local-status

PYTHONPATH=src .venv/bin/python -m gap2sku.cli.cloud_e2e \
  --root "${DIR}" \
  --started-at "${CLOUD_RUN_STARTED_AT}" \
  --out evidence/cloud-studio-e2e.json
make evidence
make verify-evidence

echo "[cloud-deploy] PASS: Cloud Studio evidence written to evidence/cloud-studio-e2e.json"
echo "[cloud-deploy] Decision Room :8080  Element :18088  MCP :18090"
