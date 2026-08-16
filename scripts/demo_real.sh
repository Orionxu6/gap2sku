#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
mkdir -p evidence/nap-pillow shared
rm -f shared/nap_pillow.db shared/nap_pillow.db-shm shared/nap_pillow.db-wal evidence/nap-pillow/trace.jsonl
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.demo_real --source private/raw_reviews --db shared/nap_pillow.db --output evidence/nap-pillow
PYTHONPATH=src .venv/bin/python -c 'import json; p=json.load(open("evidence/nap-pillow/run.json")); assert p["recommendation"]=="REVISE" and p["evidence_count"]==389 and p["data_mode"]=="REAL"'
