from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "3.0.0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_dir(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            archive.write(path, path.relative_to(source))


def main() -> None:
    DIST.mkdir(exist_ok=True)
    skills_out = DIST / "skills"
    skills_out.mkdir(exist_ok=True)
    installable_skills: list[tuple[Path, Path]] = []
    for name in ("agent-contract-validation", "evidence-conflict-decision"):
        archive = skills_out / f"{name}.zip"
        zip_dir(ROOT / "contributions/skills" / name, archive)
        installable_skills.append((archive, Path("contributions/packages") / archive.name))

    include_roots = [
        "src", "tests", "scripts", "configs", "agents", "skills", "web", "docs", "examples",
        "data/fixtures/laptop_stand", "data/public_signals", "agent_packages/build",
        "packages", "contributions", "private/source_data",
        "evidence/nap-pillow", "evidence/new-category-public",
        "evidence/new-category-synthetic",
    ]
    include_files = [
        "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "uv.lock",
        "Makefile", ".env.example", ".dockerignore", "Dockerfile", "Dockerfile.review",
        "docker-compose.yml", "railway.json",
        "docs/审核快照部署.md", "scripts/review_snapshot.sh", "scripts/package_review_snapshot.py",
        "evidence/agent-contract-report.json", "evidence/agentteams-runtime-verification.json",
        "evidence/agentteams-mcp-policy.json", "evidence/design-qa.md",
        "evidence/source-materials.sha256.json", "evidence/manifest.json",
    ]
    bundle = DIST / f"gap2sku-v{VERSION}-cloud.zip"
    manifest: dict[str, object] = {
        "version": VERSION, "private_bundle": True,
        "excludes": [".env", "API keys", "shared/*.db", "runtime logs"], "files": {},
    }
    files: list[tuple[Path, Path]] = []
    for value in include_roots:
        root = ROOT / value
        if root.exists():
            files.extend((path, path.relative_to(ROOT)) for path in root.rglob("*") if path.is_file())
    for value in include_files:
        path = ROOT / value
        if path.exists():
            files.append((path, path.relative_to(ROOT)))
    for path in sorted((ROOT / "sources/agents").glob("*.zip")):
        files.append((path, path.relative_to(ROOT)))
    files.extend(installable_skills)
    files = [
        (path, relative) for path, relative in files
        if not any(part in {".venv", "__pycache__", ".git"} for part in relative.parts)
        and path.suffix not in {".pyc", ".pyo"}
    ]
    manifest["files"] = {str(relative): {"sha256": sha(path), "bytes": path.stat().st_size} for path, relative in sorted(set(files), key=lambda item: str(item[1]))}
    manifest_path = DIST / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append((manifest_path, Path("manifest.sha256.json")))
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, relative in sorted(set(files), key=lambda item: str(item[1])):
            if any(part in {".venv", "__pycache__", ".git"} for part in relative.parts):
                continue
            archive.write(path, relative)
    print(bundle)


if __name__ == "__main__":
    main()
