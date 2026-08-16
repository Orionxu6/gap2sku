#!/usr/bin/env bash
# Foreground Workbench entrypoint. Loads local Matrix/API configuration without echoing secrets.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
export PYTHONPATH="${DIR}/src"

if [ -f "${DIR}/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${DIR}/.env.local"
  set +a
fi

PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || { echo "先运行 make bootstrap" >&2; exit 2; }

exec "${PY}" -m gap2sku.workbench \
  --host 0.0.0.0 \
  --port 8080 \
  --db shared/nap_pillow.db
