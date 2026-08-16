from __future__ import annotations

from typing import Any

from gap2sku.collaboration.matrix import MatrixObserver


class Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"event_id": "$event"}


def test_send_text_emits_real_matrix_mentions(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_put(url: str, **kwargs: Any) -> Response:
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("gap2sku.collaboration.matrix.httpx.put", fake_put)
    observer = MatrixObserver(
        "http://127.0.0.1:18080", "secret", "!room:local", "project",
        role_by_matrix_id={"@leader:local": "gap2sku-product-architect"},
        observer_user_id="@observer:local",
    )
    record = observer.send_text("@Leader 请创建 revision", "txn")
    assert captured["json"]["m.mentions"] == {"user_ids": ["@leader:local"]}
    assert record.sender_id == "@observer:local"
    assert record.raw_event["mentioned_user_ids"] == ["@leader:local"]
