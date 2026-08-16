from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    source = Path("/Users/orionxu/gap2sku")
    entries = []
    for path in sorted(p for p in source.iterdir() if p.is_file()):
        entries.append({
            "source_path": str(path), "file_name": path.name,
            "sha256": digest(path), "bytes": path.stat().st_size,
            "copied_into_project": path.name in {p.name for p in Path("sources/agents").glob("*.zip")} or path.name == "学生午睡枕-竞品评论信息-8.11.zip",
        })
    Path("evidence/source-materials.sha256.json").write_text(
        json.dumps({"source_read_only": True, "files": entries}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
