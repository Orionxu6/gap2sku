from __future__ import annotations

import json
import os

from ..contracts.loader import ContractLoader


def main() -> None:
    env = dict(os.environ)
    env.setdefault("GAP2SKU_AGENT_CONTRACT_LOADER", "strict")
    env.setdefault("MODEL_PROVIDER", "qwen")
    env.setdefault("LEADER_MODEL_NAME", "qwen-plus")
    env.setdefault("MARKET_MODEL_NAME", "qwen-plus")
    env.setdefault("SUPPLY_MODEL_NAME", "qwen-plus")
    env.setdefault("ECONOMICS_MODEL_NAME", "qwen-plus")
    env.setdefault("REVIEWER_MODEL_NAME", "qwen-plus")
    env.setdefault("PROTOTYPE_MODEL_NAME", "qwen-plus")
    env.setdefault("COMPLIANCE_MODEL_NAME", "qwen-plus")
    env.setdefault("DEMO_SEED", "20260812")
    report = ContractLoader("agent_packages/raw").compile(env)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
