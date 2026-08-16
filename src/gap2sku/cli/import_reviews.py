from __future__ import annotations

import argparse
import json

from ..evidence.reviews import ReviewWorkbookImporter, write_import_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Import nap-pillow XLSX reviews with provenance")
    parser.add_argument("--source", default="private/raw_reviews")
    parser.add_argument("--output", default="private/normalized")
    args = parser.parse_args()
    result = ReviewWorkbookImporter(args.source).import_all()
    write_import_result(result, args.output)
    print(json.dumps(result.report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
