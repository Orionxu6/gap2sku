#!/usr/bin/env bash
# verify_evidence: Verify evidence manifest, hashes, tests, artifact refs.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || PY="python3"

echo "[verify] Running evidence verifier..."
"${PY}" -m gap2sku.cli.verify_evidence --dir evidence
RESULT=$?
if [ ${RESULT} -eq 0 ]; then
  echo "[verify] PASS — evidence package complete and consistent."
else
  echo "[verify] FAIL ($RESULT) — see errors above."
fi
exit ${RESULT}
