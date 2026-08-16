#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
test -f dist/gap2sku-v3.0.0-cloud.zip || bash scripts/package_v3.sh
.venv/bin/python scripts/verify_bundle.py dist/gap2sku-v3.0.0-cloud.zip
rm -f /tmp/gap2sku-bundle-smoke.db /tmp/gap2sku-bundle-smoke.db-shm /tmp/gap2sku-bundle-smoke.db-wal
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.demo_real --source private/raw_reviews --db /tmp/gap2sku-bundle-smoke.db --output /tmp/gap2sku-bundle-smoke >/tmp/gap2sku-bundle-smoke.json
.venv/bin/python -c 'import json; p=json.load(open("/tmp/gap2sku-bundle-smoke.json")); assert p["recommendation"]=="REVISE" and p["evidence_count"]==389'
rm -f /tmp/gap2sku-new-public.db /tmp/gap2sku-new-public.db-shm /tmp/gap2sku-new-public.db-wal
rm -f /tmp/gap2sku-new-synthetic.db /tmp/gap2sku-new-synthetic.db-shm /tmp/gap2sku-new-synthetic.db-wal
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.demo_new_category --db /tmp/gap2sku-new-public.db --out /tmp/gap2sku-new-public >/tmp/gap2sku-new-public.json
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.demo_new_category --synthetic --db /tmp/gap2sku-new-synthetic.db --out /tmp/gap2sku-new-synthetic >/tmp/gap2sku-new-synthetic.json
.venv/bin/python -c 'import json; a=json.load(open("/tmp/gap2sku-new-public.json")); b=json.load(open("/tmp/gap2sku-new-synthetic.json")); assert a["recommendation"]=="REVISE" and not a["public_signals_used_as_quote"]; assert b["recommendation"]=="GO" and b["approval_ref"]'
echo "[verify-bundle] PASS"
