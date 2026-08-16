from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "Gap2SKU_审核快照版代码包.zip"


def add_file(archive: zipfile.ZipFile, relative: str) -> None:
    path = ROOT / relative
    if path.exists() and path.is_file():
        archive.write(path, relative)


def add_tree(archive: zipfile.ZipFile, relative: str) -> None:
    root = ROOT / relative
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"} for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"} or path.name.endswith((".db-wal", ".db-shm")):
            continue
        if rel.name == "reviews.normalized.private.jsonl":
            continue
        archive.write(path, rel.as_posix())


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    roots = ["src", "web", "shared", "evidence/nap-pillow", "evidence/new-category-public", "evidence/new-category-synthetic"]
    files = [
        ".dockerignore", "Dockerfile.review", "railway.json", "README.md", "LICENSE",
        "THIRD_PARTY_NOTICES.md", "pyproject.toml", "uv.lock", "Makefile", ".env.example",
        "docs/审核快照部署.md", "scripts/review_snapshot.sh",
        "evidence/agent-contract-report.json", "evidence/agentteams-runtime-verification.json",
        "evidence/agentteams-mcp-policy.json", "evidence/design-qa.md", "evidence/manifest.json",
        "evidence/source-materials.sha256.json", "evidence/demo-core-run.json", "evidence/demo-replan-plan.json",
    ]
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for root in roots:
            add_tree(archive, root)
        for relative in files:
            add_file(archive, relative)
        manifest = {
            "package": "Gap2SKU_审核快照版代码包",
            "mode": "read-only review snapshot",
            "excludes": [".env.local", "API keys", "private raw source data", "runtime logs", "SQLite WAL/SHM"],
            "sha256": {},
        }
        for info in archive.infolist():
            if info.filename == "package-manifest.json":
                continue
            data = archive.read(info)
            manifest["sha256"][info.filename] = hashlib.sha256(data).hexdigest()
        archive.writestr("package-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
