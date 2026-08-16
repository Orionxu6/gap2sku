from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Protocol

import httpx

from ..schemas.product import RenderManifest, RenderPromptRecord


class ImageGenerationError(RuntimeError):
    pass


class ImageProvider(Protocol):
    def generate(self, record: RenderPromptRecord) -> RenderManifest: ...


class OfflineImageProvider:
    """Deterministic demo provider. The output is visibly replay/synthetic."""

    def __init__(self, asset_dir: str | Path = "web/assets/concepts") -> None:
        self.asset_dir = Path(asset_dir)

    def generate(self, record: RenderPromptRecord) -> RenderManifest:
        file_name = f"{record.concept_ref}.png"
        path = self.asset_dir / file_name
        if not path.is_file():
            raise ImageGenerationError(f"offline render missing: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return RenderManifest(
            render_id=f"render-{record.concept_ref}-v1", prompt_ref=record.prompt_id,
            provider="offline-replay", model="fixed-asset-v1", seed=record.seed,
            asset_uri=f"/static/assets/concepts/{file_name}", asset_hash=f"sha256:{digest}",
            sample_spec_hash=record.sample_spec_hash, data_mode="SYNTHETIC",
        )


class QwenImageProvider:
    """DashScope-native Qwen-Image adapter with immediate local persistence."""

    DEFAULT_ENDPOINT = (
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/"
        "multimodal-generation/generation"
    )

    def __init__(
        self, endpoint: str | None = None, api_key: str | None = None,
        output_dir: str | Path = "web/assets/generated",
    ) -> None:
        self.endpoint: str = endpoint or os.environ.get("QWEN_IMAGE_ENDPOINT") or self.DEFAULT_ENDPOINT
        self.api_key: str = api_key or os.environ.get("DASHSCOPE_API_KEY") or ""
        self.output_dir = Path(output_dir)
        if not self.api_key:
            raise ImageGenerationError("DASHSCOPE_API_KEY is required")

    @staticmethod
    def _image_url(payload: dict[str, object]) -> str:
        output = payload.get("output")
        if not isinstance(output, dict):
            return ""
        choices = output.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and isinstance(item.get("image"), str):
                            return str(item["image"])
        results = output.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict):
            value = results[0].get("url")
            return str(value) if isinstance(value, str) else ""
        return ""

    def generate(self, record: RenderPromptRecord) -> RenderManifest:
        model = os.environ.get("QWEN_IMAGE_MODEL") or record.model or "qwen-image-2.0"
        try:
            response = httpx.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "input": {"messages": [{"role": "user", "content": [{"text": record.prompt}]}]},
                    "parameters": {
                        "seed": record.seed,
                        "negative_prompt": record.negative_prompt,
                        "prompt_extend": False,
                    },
                },
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ImageGenerationError("Qwen response was not a JSON object")
            remote_url = self._image_url(payload)
            if not remote_url:
                raise ImageGenerationError("Qwen response did not contain an image URL")
            downloaded = httpx.get(remote_url, timeout=60, follow_redirects=True)
            downloaded.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            raise ImageGenerationError(f"Qwen image request failed: {type(exc).__name__}") from exc
        content_type = downloaded.headers.get("content-type", "").lower()
        if not content_type.startswith("image/") or not downloaded.content:
            raise ImageGenerationError("Qwen image download did not return image bytes")
        if len(downloaded.content) > 25 * 1024 * 1024:
            raise ImageGenerationError("Qwen image exceeds the 25 MiB local limit")
        digest = hashlib.sha256(downloaded.content).hexdigest()
        safe_prompt_id = re.sub(r"[^A-Za-z0-9._-]+", "-", record.prompt_id).strip("-") or "render"
        suffix = ".jpg" if "jpeg" in content_type else ".webp" if "webp" in content_type else ".png"
        file_name = f"{safe_prompt_id}-{digest[:12]}{suffix}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / file_name
        path.write_bytes(downloaded.content)
        return RenderManifest(
            render_id=f"render-{record.concept_ref}-v1", prompt_ref=record.prompt_id,
            provider="qwen", model=model, seed=record.seed,
            asset_uri=f"/static/assets/generated/{file_name}",
            asset_hash=f"sha256:{digest}", sample_spec_hash=record.sample_spec_hash,
            data_mode="SYNTHETIC",
        )
