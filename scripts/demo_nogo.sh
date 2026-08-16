#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"
PYTHONPATH=src .venv/bin/python -m gap2sku.cli.demo_nogo
PYTHONPATH=src .venv/bin/python -c 'import json; p=json.load(open("evidence/nap-pillow/no-go-run.json")); assert p["business_state"]=="NO-GO" and p["decision_brief"]["no_go_reasons"]'
