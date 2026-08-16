from __future__ import annotations

import argparse

from ..mcp_official import create_mcp_server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18090)
    args = parser.parse_args()
    create_mcp_server(host=args.host, port=args.port).run(transport="streamable-http")


if __name__ == "__main__":
    main()
