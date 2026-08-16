from __future__ import annotations

import pytest

from gap2sku.cli.preflight_models import QWEN_COMPATIBLE_BASE, chat_completions_url


def test_qwen_empty_base_uses_official_compatible_endpoint() -> None:
    assert chat_completions_url("qwen", "") == f"{QWEN_COMPATIBLE_BASE}/chat/completions"


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        ("https://example.invalid", "https://example.invalid/v1/chat/completions"),
        ("https://example.invalid/v1", "https://example.invalid/v1/chat/completions"),
        ("https://example.invalid/v1/chat/completions", "https://example.invalid/v1/chat/completions"),
    ],
)
def test_configured_base_is_normalized(base: str, expected: str) -> None:
    assert chat_completions_url("custom", base) == expected


def test_non_qwen_requires_base_url() -> None:
    with pytest.raises(ValueError, match="必须配置"):
        chat_completions_url("custom", "")
