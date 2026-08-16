from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class Metrics:
    @staticmethod
    def from_trace(path: str | Path) -> dict[str, Any]:
        trace_path = Path(path)
        rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()] if trace_path.exists() else []
        status = Counter(row.get("result_status", "UNKNOWN") for row in rows)
        tools = Counter(row.get("tool_name", "") for row in rows)
        return {
            "trace_events": len(rows), "status_counts": dict(sorted(status.items())),
            "tool_calls": dict(sorted(tools.items())),
            "total_latency_ms": sum(int(row.get("latency_ms", 0) or 0) for row in rows),
            "review_events": sum(bool(row.get("review_decision")) for row in rows),
        }
