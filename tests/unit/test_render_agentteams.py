from pathlib import Path

from gap2sku.cli.render_agentteams import render


def test_render_rewrites_local_package_for_worker_container(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "worker.yaml"
    destination = tmp_path / "rendered.yaml"
    source.write_text(
        "spec:\n  model: ${MODEL_NAME}\n  package: file://./packages/market.zip\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MODEL_NAME", "deepseek-v4-flash")
    monkeypatch.setenv("GAP2SKU_MCP_BASE_URL", "http://host.docker.internal:18090")

    render(source, destination)

    rendered = destination.read_text(encoding="utf-8")
    assert "model: deepseek-v4-flash" in rendered
    assert (
        "package: http://host.docker.internal:18090/agent-packages/market.zip"
        in rendered
    )
