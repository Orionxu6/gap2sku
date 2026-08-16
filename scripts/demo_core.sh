#!/usr/bin/env bash
# demo-core: Deterministic Domain Core path (no AgentTeams dependency).
# Runs the full Laptop Stand pipeline offline against synthetic fixture.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
PY="${DIR}/.venv/bin/python"
[ -x "${PY}" ] || PY="python3"

echo "[demo-core] Running Gap2SKU Domain Core offline pipeline..."
"${PY}" -m gap2sku.cli.demo_core --fixture data/fixtures/laptop_stand --out evidence/demo-core-run.json
echo "[demo-core] V1 spec + reviewer result written to evidence/demo-core-run.json"
echo "[demo-core] Done."
