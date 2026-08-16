from __future__ import annotations

from pathlib import Path

from gap2sku.cli.stage_agentteams_skills import stage


def test_stage_all_assigned_agentteams_skills(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    report = stage(root, tmp_path / "worker-skills")
    assert report["valid"] is True
    assert report["runtime"] == "qwenpaw"
    assert report["skill_count"] == 10
    assert len(report["assignments"]) == 7
    for item in report["skills"]:
        assert (tmp_path / "worker-skills" / item["name"] / "SKILL.md").is_file()
