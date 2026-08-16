from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

WORKERS = (
    "gap2sku-product-architect", "gap2sku-market", "gap2sku-prototype-designer",
    "gap2sku-supply", "gap2sku-economics", "gap2sku-compliance", "gap2sku-reviewer",
)


def _agt(kind: str, name: str) -> dict[str, Any]:
    collection = {"worker": "workers", "team": "teams", "human": "humans"}.get(kind)
    if collection is None:
        raise ValueError(f"unsupported AgentTeams resource kind: {kind}")
    result = subprocess.run(
        [
            "docker", "exec", "agentteams-manager", "agt", "get",
            collection, name, "-o", "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"agt get {collection} {name} failed")
    start = result.stdout.find("{")
    if start < 0:
        raise RuntimeError(f"agt get {collection} {name} did not return JSON")
    data = json.loads(result.stdout[start:])
    if not isinstance(data, dict):
        raise RuntimeError(f"agt get {collection} {name} returned invalid JSON")
    return data


def _nested(data: dict[str, Any], *keys: str) -> str:
    value: Any = data
    remaining = keys
    # AgentTeams v1.2.2 CLI flattens spec/status fields while older releases
    # returned the complete resource envelope.  Accept both representations.
    if remaining and remaining[0] in {"spec", "status"} and remaining[0] not in data:
        remaining = remaining[1:]
    for key in remaining:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return str(value or "")


def _wait_resources(seconds: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    deadline = time.monotonic() + seconds
    last_error = "resources not ready"
    while time.monotonic() < deadline:
        try:
            team = _agt("team", "gap2sku-definition")
            human = _agt("human", "gap2sku-observer")
            room_id = _nested(team, "status", "teamRoomID")
            matrix_user = _nested(human, "status", "matrixUserID")
            role_by_matrix_id: dict[str, str] = {}
            for worker in WORKERS:
                resource = _agt("worker", worker)
                worker_matrix_id = _nested(resource, "status", "matrixUserID")
                if worker_matrix_id:
                    role_by_matrix_id[worker_matrix_id] = worker
            if room_id and matrix_user and len(role_by_matrix_id) == len(WORKERS):
                return team, human, role_by_matrix_id
            last_error = "Team room, Human, or Worker Matrix identities are still pending"
        except (RuntimeError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(last_error)


def _update_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    pending = dict(updates)
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in pending:
            output.append(f"{key}={shlex.quote(pending.pop(key))}")
        else:
            output.append(line)
    output.extend(f"{key}={shlex.quote(value)}" for key, value in pending.items())
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    path.chmod(0o600)


def connect(env_path: Path, wait_seconds: int) -> dict[str, Any]:
    homeserver = os.environ.get("MATRIX_HOMESERVER", "http://127.0.0.1:18080").rstrip("/")
    team, human, role_by_matrix_id = _wait_resources(wait_seconds)
    room_id = _nested(team, "status", "teamRoomID")
    human_matrix_user = _nested(human, "status", "matrixUserID")
    password = _nested(human, "status", "initialPassword")
    login_user = human_matrix_user
    credential_source = "human_initial_password"
    if not password:
        login_user = os.environ.get("AGENTTEAMS_ADMIN_USER", "")
        password = os.environ.get("AGENTTEAMS_ADMIN_PASSWORD", "")
        credential_source = "configured_matrix_admin"
    if not login_user or not password:
        raise RuntimeError("Matrix reader credentials are unavailable")
    with httpx.Client(timeout=15) as client:
        login = client.post(
            f"{homeserver}/_matrix/client/v3/login",
            json={
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": login_user},
                "password": password,
            },
        )
        login.raise_for_status()
        access_token = str(login.json().get("access_token", ""))
        reader_user = str(login.json().get("user_id", ""))
        if not access_token:
            raise RuntimeError("Matrix login returned no access token")
        members = client.get(
            f"{homeserver}/_matrix/client/v3/rooms/{quote(room_id, safe='')}/joined_members",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        members.raise_for_status()
        joined = members.json().get("joined", {})
        if human_matrix_user not in joined:
            raise RuntimeError("AgentTeams Human Observer is not joined to the Team Room")
        if reader_user not in joined:
            raise RuntimeError("Matrix reader is not joined to the Team Room")

    _update_env(
        env_path,
        {
            "MATRIX_HOMESERVER": homeserver,
            "MATRIX_ROOM_ID": room_id,
            "MATRIX_OBSERVER_ACCESS_TOKEN": access_token,
            "MATRIX_OBSERVER_USER_ID": reader_user,
            "MATRIX_ROLE_MAP_JSON": json.dumps(role_by_matrix_id, separators=(",", ":"), sort_keys=True),
        },
    )
    report = {
        "connected": True,
        "homeserver": homeserver,
        "room_id": room_id,
        "observer_human_user": human_matrix_user,
        "matrix_reader_user": reader_user,
        "credential_source": credential_source,
        "worker_matrix_users": role_by_matrix_id,
        "access_token": "REDACTED",
    }
    Path("evidence/agentteams-matrix-connection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env.local")
    parser.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args()
    report = connect(Path(args.env), args.wait_seconds)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
