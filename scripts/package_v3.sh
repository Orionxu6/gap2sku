#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.contracts >/dev/null
.venv/bin/python scripts/package_v3.py
