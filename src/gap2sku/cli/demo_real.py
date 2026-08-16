from __future__ import annotations

import argparse
import json

from ..nap_pillow import NapPillowPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the nap-pillow decision loop")
    parser.add_argument("--source", default="private/raw_reviews")
    parser.add_argument("--db", default="shared/nap_pillow.db")
    parser.add_argument("--output", default="evidence/nap-pillow")
    parser.add_argument("--synthetic-supply", action="store_true")
    args = parser.parse_args()
    result = NapPillowPipeline(
        args.source, args.db, args.output, synthetic_supply=args.synthetic_supply
    ).run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
