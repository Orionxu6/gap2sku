#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"

if [ ! -x .venv/bin/python ]; then
  echo "缺少 .venv；先运行 make bootstrap" >&2
  exit 2
fi

make demo-real
make demo-synthetic
make demo-nogo
make demo-core
make demo-replan
make demo-new-category
make demo-new-category-synthetic

echo "[review-snapshot] evidence and SQLite snapshots are ready"
echo "[review-snapshot] start with: GAP2SKU_REVIEW_MODE=1 make workbench"
