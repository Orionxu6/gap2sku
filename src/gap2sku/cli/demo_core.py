"""demo-core CLI — deterministic offline pipeline (spec 25)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..pipeline import DomainCorePipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="data/fixtures/laptop_stand")
    parser.add_argument("--out", default="evidence/demo-core-run.json")
    args = parser.parse_args()

    pipeline = DomainCorePipeline(Path(args.fixture))
    result = pipeline.run()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"[demo-core] project: {result['project_id']}")
    print(f"[demo-core] artifacts: {result['artifact_count']}")
    print(f"[demo-core] spec: {result['spec']['spec_id']}")
    print(f"[demo-core] review decision: {result['review']['decision']}")
    print(f"[demo-core] elapsed: {result['elapsed_ms']}ms")
    print(f"[demo-core] output: {args.out}")


if __name__ == "__main__":
    main()
