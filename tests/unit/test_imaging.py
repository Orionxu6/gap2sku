from __future__ import annotations

import hashlib

import httpx
import pytest

from gap2sku.imaging.providers import ImageGenerationError, QwenImageProvider
from gap2sku.schemas.product import RenderPromptRecord


def _record() -> RenderPromptRecord:
    return RenderPromptRecord(
        prompt_id="prompt-concept-a-v2", project_id="p", concept_ref="concept-a",
        sample_spec_hash="sha256:spec", provider="qwen", model="qwen-image-2.0", seed=7,
        prompt="产品设计渲染", negative_prompt="品牌、认证标志", input_refs=["sample-v2"],
    )


def test_qwen_provider_uses_native_messages_and_persists_image(monkeypatch, tmp_path) -> None:
    image_bytes = b"\x89PNG\r\n\x1a\nrender"
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs["json"])
        return httpx.Response(
            200,
            json={"output": {"choices": [{"message": {"content": [{"image": "https://img/x"}]}}]}},
            request=httpx.Request("POST", url),
        )

    def fake_get(url, **kwargs):
        return httpx.Response(
            200, content=image_bytes, headers={"content-type": "image/png"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    manifest = QwenImageProvider(api_key="redacted-test", output_dir=tmp_path).generate(_record())
    assert captured["input"]["messages"][0]["content"][0]["text"] == "产品设计渲染"
    assert captured["parameters"]["prompt_extend"] is False
    assert manifest.provider == "qwen"
    assert manifest.label == "SYNTHETIC_CONCEPT"
    assert manifest.asset_hash == f"sha256:{hashlib.sha256(image_bytes).hexdigest()}"
    assert (tmp_path / manifest.asset_uri.rsplit("/", 1)[-1]).read_bytes() == image_bytes


def test_qwen_provider_rejects_non_image_download(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        httpx, "post",
        lambda url, **kwargs: httpx.Response(
            200, json={"output": {"results": [{"url": "https://img/x"}]}},
            request=httpx.Request("POST", url),
        ),
    )
    monkeypatch.setattr(
        httpx, "get",
        lambda url, **kwargs: httpx.Response(
            200, text="not an image", headers={"content-type": "text/plain"},
            request=httpx.Request("GET", url),
        ),
    )
    with pytest.raises(ImageGenerationError, match="image bytes"):
        QwenImageProvider(api_key="redacted-test", output_dir=tmp_path).generate(_record())
