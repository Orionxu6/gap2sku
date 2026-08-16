"""demo-agentteams CLI — sends a real Matrix task or records an explicit blocker."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from gap2sku.collaboration.matrix import MatrixObserver


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="evidence/demo-v1-run.txt")
    parser.add_argument("--blocked", action="store_true")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    task_msg = Path("at/run_demo_task_message.md")
    sent_event = ""
    sent_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if args.send:
        if not args.run_id:
            raise SystemExit("--run-id is required with --send")
        role_map = json.loads(os.environ.get("MATRIX_ROLE_MAP_JSON", "{}"))
        observer = MatrixObserver(
            os.environ["MATRIX_HOMESERVER"], os.environ["MATRIX_OBSERVER_ACCESS_TOKEN"],
            os.environ["MATRIX_ROOM_ID"], "nap-pillow-cn-20260811-001",
            role_by_matrix_id=role_map,
            observer_user_id=os.environ.get("MATRIX_OBSERVER_USER_ID", "@gap2sku-observer:local"),
        )
        body = task_msg.read_text(encoding="utf-8").split("```text\n", 1)[1].split("\n```", 1)[0]
        body = body.replace("{{RUNTIME_RUN_ID}}", args.run_id)
        sent_event = observer.send_text(body, f"gap2sku-{args.run_id}").message_id
    with out.open("a") as f:
        f.write("\n=== AgentTeams runtime task ===\n")
        f.write(f"task msg exists: {task_msg.exists()}\n")
        f.write(f"runtime_blocked: {args.blocked}\n")
        f.write(f"matrix_task_sent: {bool(sent_event)}\n")
        f.write(f"matrix_event_id: {sent_event}\n")
        f.write(f"sent_at: {sent_at}\n")
        f.write(f"runtime_run_id: {args.run_id}\n")
        f.write("chat_is_business_state: false\n")
    print(json.dumps({
        "runtime_evidence": args.out,
        "matrix_task_sent": bool(sent_event),
        "matrix_event_id": sent_event,
        "sent_at": sent_at,
        "runtime_run_id": args.run_id,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
