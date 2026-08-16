#!/usr/bin/env bash
# Install project deps, prepare fixture and agent packages.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
export PYTHONPATH="${DIR}/src"

VENV="${DIR}/.venv"
PY="${VENV}/bin/python"

echo "[bootstrap] Syncing locked dependencies with uv"
uv sync --frozen --all-extras

echo "[bootstrap] Generating synthetic fixture"
"${PY}" -m gap2sku.fixtures.generate --out data/fixtures/laptop_stand --seed 42

echo "[bootstrap] Validating and compiling agent packages"
"${PY}" -m gap2sku.cli.contracts

echo "[bootstrap] Done. Next: make doctor && make test"
