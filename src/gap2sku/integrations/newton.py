"""Safe, offline ingestion boundary for user-authorized 1688 Newton exports.

No login automation or unofficial API is implemented. An export remains a
supplier-discovery signal unless an explicit RFQ response is imported through
the stricter quote path.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..schemas.product import PublicSupplierSignal, PublicSupplierSignalSet


class NewtonExportError(ValueError):
    pass


SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "cookie",
    "cookies",
    "password",
    "authorization",
}


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in SENSITIVE_KEYS or _contains_sensitive_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


class NewtonExportAdapter:
    """Convert a sanitized Newton/1688 user export into non-quote signals."""

    @staticmethod
    def ingest(path: str | Path, project_id: str) -> PublicSupplierSignalSet:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise NewtonExportError("export must be an object with an items array")
        if _contains_sensitive_key(payload):
            raise NewtonExportError("export contains credentials or session material")
        exported_at = str(payload.get("exported_at", ""))
        if not exported_at:
            raise NewtonExportError("exported_at is required")
        file_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        signals = []
        for index, item in enumerate(payload["items"], start=1):
            if not isinstance(item, dict):
                raise NewtonExportError(f"items[{index - 1}] must be an object")
            url = str(item.get("source_url", ""))
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise NewtonExportError(f"items[{index - 1}].source_url must be HTTP(S)")
            facts = item.get("observed_facts", {})
            if not isinstance(facts, dict):
                raise NewtonExportError(f"items[{index - 1}].observed_facts must be an object")
            signals.append(
                PublicSupplierSignal(
                    signal_id=str(item.get("signal_id") or f"newton-export-{index:03d}"),
                    supplier_name=str(item.get("supplier_name", "unknown supplier")),
                    source_url=url,
                    captured_at=exported_at,
                    source_hash=f"sha256:{file_hash}",
                    observed_facts=facts,
                    verification_level="AUTHORIZED_PLATFORM_EXPORT",
                    limitations=[
                        "用户授权导出不等于供应商对锁定规格的报价",
                        "供应商身份、工艺、样品与量产一致性仍需独立验证",
                        "必须通过 RFQ import 绑定 SampleSpec hash 后才能进入成本验证",
                    ],
                )
            )
        return PublicSupplierSignalSet(
            signal_set_id=f"newton-export-{file_hash[:16]}",
            project_id=project_id,
            signals=signals,
        )
