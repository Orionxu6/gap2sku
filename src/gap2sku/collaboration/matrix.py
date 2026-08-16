from __future__ import annotations

import re
from typing import Any

import httpx

from .models import MatrixMessageRecord

ROLE_BY_MATRIX_ID = {
    "leader": "gap2sku-product-architect",
    "market": "gap2sku-market",
    "prototype": "gap2sku-prototype-designer",
    "supply": "gap2sku-supply",
    "economics": "gap2sku-economics",
    "compliance": "gap2sku-compliance",
    "reviewer": "gap2sku-reviewer",
}
ROLE_ALIAS = {
    "leader": "gap2sku-product-architect",
    "market": "gap2sku-market",
    "prototype": "gap2sku-prototype-designer",
    "supply": "gap2sku-supply",
    "economics": "gap2sku-economics",
    "compliance": "gap2sku-compliance",
    "reviewer": "gap2sku-reviewer",
}


class MatrixObserver:
    """Matrix Client-Server bridge for the scoped Human Observer account."""

    def __init__(
        self, homeserver: str, access_token: str, room_id: str, project_id: str,
        role_by_matrix_id: dict[str, str] | None = None, observer_user_id: str = "@gap2sku-observer:local",
    ) -> None:
        self.homeserver = homeserver.rstrip("/")
        self.access_token = access_token
        self.room_id = room_id
        self.project_id = project_id
        self.role_by_matrix_id = role_by_matrix_id or {}
        self.observer_user_id = observer_user_id

    def messages(self, *, from_token: str | None = None, limit: int = 50) -> tuple[list[MatrixMessageRecord], str | None]:
        params: dict[str, Any] = {"dir": "b", "limit": min(limit, 200)}
        if from_token:
            params["from"] = from_token
        response = httpx.get(
            f"{self.homeserver}/_matrix/client/v3/rooms/{self.room_id}/messages",
            params=params, headers={"Authorization": f"Bearer {self.access_token}"}, timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        records: list[MatrixMessageRecord] = []
        for event in payload.get("chunk", []):
            if event.get("type") != "m.room.message":
                continue
            sender = str(event.get("sender", ""))
            localpart = sender.split(":", 1)[0].lstrip("@").lower()
            role = self.role_by_matrix_id.get(sender) or next(
                (value for key, value in ROLE_BY_MATRIX_ID.items() if key in localpart),
                "human-manager",
            )
            records.append(MatrixMessageRecord(
                message_id=str(event.get("event_id", "")), room_id=self.room_id,
                project_id=self.project_id, sender_id=sender, sender_role=role,
                body=str(event.get("content", {}).get("body", "")),
                origin_server_ts=int(event.get("origin_server_ts", 0)), raw_event=event,
            ))
        return records, payload.get("end")

    def send_text(self, body: str, transaction_id: str) -> MatrixMessageRecord:
        """Send a human message through Matrix and return its auditable record."""
        matrix_id_by_role = {role: matrix_id for matrix_id, role in self.role_by_matrix_id.items()}
        mentioned_roles = {
            ROLE_ALIAS[alias.lower()]
            for alias in re.findall(r"@([A-Za-z][A-Za-z0-9_-]*)", body)
            if alias.lower() in ROLE_ALIAS
        }
        user_ids = [matrix_id_by_role[role] for role in sorted(mentioned_roles) if role in matrix_id_by_role]
        content: dict[str, Any] = {"msgtype": "m.text", "body": body}
        if user_ids:
            content["m.mentions"] = {"user_ids": user_ids}
        response = httpx.put(
            f"{self.homeserver}/_matrix/client/v3/rooms/{self.room_id}/send/m.room.message/{transaction_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=content, timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return MatrixMessageRecord(
            message_id=str(payload["event_id"]), room_id=self.room_id,
            project_id=self.project_id, sender_id=self.observer_user_id,
            sender_role="human-manager", body=body, origin_server_ts=0,
            data_mode="REAL", raw_event={
                "source": "matrix-client-api", "sent": True, "mentioned_user_ids": user_ids,
            },
        )
