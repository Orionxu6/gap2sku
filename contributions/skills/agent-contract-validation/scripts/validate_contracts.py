#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo / "src"))
    from gap2sku.contracts.loader import ContractLoader

    env = dict(os.environ)
    defaults = {
        "GAP2SKU_AGENT_CONTRACT_LOADER": "strict", "MODEL_PROVIDER": "qwen",
        "LEADER_MODEL_NAME": "qwen-plus", "MARKET_MODEL_NAME": "qwen-plus",
        "SUPPLY_MODEL_NAME": "qwen-plus", "ECONOMICS_MODEL_NAME": "qwen-plus",
        "REVIEWER_MODEL_NAME": "qwen-plus", "DEMO_SEED": "20260812",
        "PROTOTYPE_MODEL_NAME": "qwen-plus", "COMPLIANCE_MODEL_NAME": "qwen-plus",
    }
    for key, value in defaults.items():
        env.setdefault(key, value)
    report = ContractLoader(repo / "agent_packages/raw", repo / "agent_packages/build").compile(env)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("valid") and report.get("agent_count") == 7 else 1


if __name__ == "__main__":
    raise SystemExit(main())
