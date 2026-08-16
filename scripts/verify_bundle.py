from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


def main(path: str) -> None:
    bundle = Path(path)
    with zipfile.ZipFile(bundle) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"corrupt ZIP member: {bad}")
        names = set(archive.namelist())
        if any(name == ".env" or name.endswith("/.env") or name.endswith(".db") for name in names):
            raise SystemExit("bundle contains secret env or local database")
        manifest = json.loads(archive.read("manifest.sha256.json"))
        for name, metadata in manifest["files"].items():
            if name not in names:
                raise SystemExit(f"manifest member missing: {name}")
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            if digest != metadata["sha256"]:
                raise SystemExit(f"hash mismatch: {name}")
        required = {
            "pyproject.toml", "uv.lock", "scripts/cloud_doctor.sh", "scripts/cloud_deploy.sh",
            "src/gap2sku/cli/cloud_e2e.py",
            "configs/agentteams/team.yaml",
            "private/source_data/学生午睡枕-竞品评论信息-8.11.zip",
            "data/public_signals/desk_headphone_hanger.json",
            "web/assets/concepts/new-category/concept-a-headphone-hanger.png",
            "web/guide.html", "web/guide.css",
            "docs/使用入口与登录说明.md",
            "evidence/new-category-public/run.json",
            "evidence/new-category-synthetic/run.json",
            "packages/prototype.zip", "packages/compliance.zip",
            "contributions/packages/agent-contract-validation.zip",
            "contributions/packages/evidence-conflict-decision.zip",
        }
        missing = required - names
        if missing:
            raise SystemExit(f"required members missing: {sorted(missing)}")
    print(json.dumps({"valid": True, "bundle": str(bundle), "files": len(names)}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
