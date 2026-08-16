#!/usr/bin/env bash
# demo-replan: Submit $8.00 -> $6.50 ChangeEvent and generate V2.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || PY="python3"

EVIDENCE="${DIR}/evidence/demo-v2-replan-run.txt"
mkdir -p "${DIR}/evidence"
: > "${EVIDENCE}"

echo "[demo-replan] Submitting ChangeEvent factory_cost_max: 8.00 -> 6.50" | tee -a "${EVIDENCE}"
"${PY}" -m gap2sku.cli.demo_replan --old 8.00 --new 6.50 --out evidence/demo-replan-plan.json 2>&1 | tee -a "${EVIDENCE}"
echo "[demo-replan] ImpactPlan + Spec V2 written to evidence/" | tee -a "${EVIDENCE}"
