"""verify_evidence CLI — verify evidence manifest, hashes, artifact refs (spec 28)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="evidence")
    args = parser.parse_args()
    edir = Path(args.dir)
    manifest_path = edir / "manifest.json"
    if not manifest_path.exists():
        print("[verify] FAIL: evidence/manifest.json not found")
        return 1
    manifest = json.loads(manifest_path.read_text())
    errors = 0
    for entry in manifest.get("files", []):
        f = edir / entry["path"]
        if not f.exists():
            print(f"[verify] FAIL: missing {entry['path']}")
            errors += 1
            continue
        actual = _sha256(f)
        if actual != entry["sha256"]:
            print(f"[verify] FAIL: hash mismatch {entry['path']}")
            errors += 1
    # Check core evidence files exist
    required = ["manifest.json", "environment.txt"]
    for r in required:
        if not (edir / r).exists():
            print(f"[verify] WARN: recommended file {r} not found")
    if errors:
        print(f"[verify] {errors} error(s)")
        return 1
    print(f"[verify] {len(manifest.get('files', []))} files verified OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
