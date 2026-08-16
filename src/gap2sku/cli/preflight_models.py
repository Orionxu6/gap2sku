"""Redacted LLM connectivity preflight for the local AgentTeams install."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

QWEN_COMPATIBLE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def chat_completions_url(provider: str, configured_base: str) -> str:
    base = configured_base.strip().rstrip("/")
    if not base:
        if provider.lower() != "qwen":
            raise ValueError("非 Qwen provider 必须配置 AGENTTEAMS_OPENAI_BASE_URL")
        base = QWEN_COMPATIBLE_BASE
    if base.endswith("/chat/completions"):
        return base
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def run_preflight() -> dict[str, Any]:
    provider = os.environ.get("AGENTTEAMS_LLM_PROVIDER", "openai-compat")
    model = os.environ.get("AGENTTEAMS_DEFAULT_MODEL", "deepseek-v4-flash")
    key = os.environ.get("AGENTTEAMS_LLM_API_KEY", "")
    if not key:
        raise ValueError("AGENTTEAMS_LLM_API_KEY 未配置")
    endpoint = chat_completions_url(
        provider, os.environ.get("AGENTTEAMS_OPENAI_BASE_URL", ""),
    )
    started = datetime.now(timezone.utc)
    response = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Reply exactly: OK"}],
            "temperature": 0,
            # DeepSeek V4 may spend part of this budget on reasoning_content.
            # Two tokens can yield HTTP 200 but no final answer, which is not a
            # usable Agent runtime preflight.
            "max_tokens": 256,
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices", [])
    if not choices or not choices[0].get("message", {}).get("content"):
        raise RuntimeError("模型响应缺少 choices[0].message.content")
    elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    return {
        "verified": True,
        "provider": provider,
        "model": model,
        "endpoint_host": httpx.URL(endpoint).host,
        "http_status": response.status_code,
        "finish_reason": choices[0].get("finish_reason"),
        "latency_ms": elapsed_ms,
        "purpose": "agentteams_text_workers",
        "image_provider_configured": bool(os.environ.get("DASHSCOPE_API_KEY", "")),
        "image_model": os.environ.get("QWEN_IMAGE_MODEL", "qwen-image-2.0"),
        "image_preflight_billed": False,
        "secret_values_recorded": False,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="evidence/model-preflight.json")
    args = parser.parse_args()
    report = run_preflight()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
