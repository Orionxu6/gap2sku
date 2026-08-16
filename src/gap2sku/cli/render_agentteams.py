from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

VARIABLE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def render(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    missing = sorted({key for key in VARIABLE.findall(text) if not os.environ.get(key)})
    if missing:
        raise SystemExit(f"{source}: missing environment variables {missing}")
    text = VARIABLE.sub(lambda match: os.environ[match.group(1)], text)
    package_base_url = os.environ.get("GAP2SKU_MCP_BASE_URL", "").rstrip("/")
    text = re.sub(
        r"package:\s*file://\./packages/([^\s]+)",
        lambda match: f"package: {package_base_url}/agent-packages/{match.group(1)}",
        text,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="configs/agentteams")
    parser.add_argument("--out", default=".runtime/agentteams")
    args = parser.parse_args()
    source, output = Path(args.source), Path(args.out)
    for path in sorted(source.glob("*.yaml")):
        if path.name.endswith(".example.yaml"):
            continue
        render(path, output / path.name)


if __name__ == "__main__":
    main()
