from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError(f"{path}: unclosed YAML frontmatter") from exc
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter must be an object")
    return data


def _skill_sources(root: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for parent in (root / "skills", root / "contributions/skills"):
        for skill_file in sorted(parent.glob("*/SKILL.md")):
            metadata = _frontmatter(skill_file)
            name = str(metadata.get("name", ""))
            if not name:
                raise ValueError(f"{skill_file}: name is required")
            if name in sources:
                raise ValueError(f"duplicate skill name: {name}")
            sources[name] = skill_file.parent
    return sources


def _assignments(root: Path) -> dict[str, list[str]]:
    assignments: dict[str, list[str]] = {}
    for manifest in sorted((root / "configs/agentteams").glob("worker-*.yaml")):
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{manifest}: invalid Worker manifest")
        worker = str(data.get("metadata", {}).get("name", ""))
        skills = data.get("spec", {}).get("skills", [])
        if not worker or not isinstance(skills, list):
            raise ValueError(f"{manifest}: Worker name and skills are required")
        assignments[worker] = [str(skill) for skill in skills]
    if len(assignments) != 7:
        raise ValueError(f"expected seven Worker manifests, got {len(assignments)}")
    return assignments


def stage(root: Path, output: Path) -> dict[str, Any]:
    sources = _skill_sources(root)
    assignments = _assignments(root)
    required = sorted({skill for skills in assignments.values() for skill in skills})
    missing = [name for name in required if name not in sources]
    if missing:
        raise ValueError(f"missing assigned Worker skills: {missing}")

    output.mkdir(parents=True, exist_ok=True)
    staged: list[dict[str, Any]] = []
    for name in required:
        source = sources[name]
        metadata = _frontmatter(source / "SKILL.md")
        absent = [key for key in ("name", "description", "assign_when") if not metadata.get(key)]
        if absent:
            raise ValueError(f"{source / 'SKILL.md'}: missing required frontmatter {absent}")
        destination = output / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        staged.append({"name": name, "source": str(source.relative_to(root))})

    report = {
        "valid": True,
        "skill_count": len(staged),
        "skills": staged,
        "assignments": assignments,
        "runtime": "qwenpaw",
    }
    report_path = output.parent / "skill-stage-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=".runtime/agentteams/staged-worker-skills")
    args = parser.parse_args()
    report = stage(Path(args.root).resolve(), Path(args.out).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
