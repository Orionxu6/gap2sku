#!/usr/bin/env bash
# collect_evidence: Gather redacted run evidence into evidence/.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || PY="python3"

echo "[evidence] Building evidence manifest..."
"${PY}" -m gap2sku.cli.collect_evidence --dir evidence
echo "[evidence] Done. Review evidence/manifest.json"
