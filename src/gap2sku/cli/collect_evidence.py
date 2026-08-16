"""collect_evidence CLI — build evidence manifest (spec 28)."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="evidence")
    args = parser.parse_args()
    edir = Path(args.dir)
    # Collect all files EXCEPT manifest.json itself (we're about to write it).
    files = sorted([p for p in edir.rglob("*") if p.is_file() and p.name != ".gitkeep" and p.name != "manifest.json"])
    entries: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": entries,
    }
    for f in files:
        entries.append({
            "path": str(f.relative_to(edir)),
            "sha256": _sha256(f),
            "size_bytes": f.stat().st_size,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    (edir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[evidence] manifest: {len(files)} files, {sum(int(item['size_bytes']) for item in entries)} bytes")


if __name__ == "__main__":
    main()
