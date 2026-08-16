#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
mkdir -p evidence/nap-pillow-synthetic shared
rm -f shared/nap_pillow_synthetic.db shared/nap_pillow_synthetic.db-shm shared/nap_pillow_synthetic.db-wal evidence/nap-pillow-synthetic/trace.jsonl
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.demo_real --source private/raw_reviews --db shared/nap_pillow_synthetic.db --output evidence/nap-pillow-synthetic --synthetic-supply
PYTHONPATH=src .venv/bin/python -c 'import json; p=json.load(open("evidence/nap-pillow-synthetic/run.json")); assert p["recommendation"]=="GO" and p["data_mode"]=="SYNTHETIC"'
