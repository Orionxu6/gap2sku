from __future__ import annotations

import argparse
import json
from pathlib import Path

from gap2sku.new_category import NewCategoryPipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--db")
    parser.add_argument("--out")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    mode = "synthetic" if args.synthetic else "public"
    db_path = Path(args.db or f"shared/desk_headphone_hanger_{mode}.db")
    output_dir = Path(args.out or f"evidence/new-category-{mode}")
    if args.fresh:
        for suffix in ("", "-wal", "-shm"):
            db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)
    result = NewCategoryPipeline(
        synthetic=args.synthetic,
        db_path=db_path,
        output_dir=output_dir,
    ).run()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
