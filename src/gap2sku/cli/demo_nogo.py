"""Deterministic repeated-critical-test-failure NO-GO demonstration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gap2sku.governance.decision import DecisionEngine
from gap2sku.governance.models import DecisionPolicy, EvidenceState, ReviewReport


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence/nap-pillow/no-go-run.json")
    args = parser.parse_args()
    review = ReviewReport(
        review_id="review-durability-r003",
        task_id="nap-pillow-durability-r003",
        revision=3,
        product_spec_ref="nap-product-spec-v3",
        product_spec_hash="sha256:durability-failure-demo-v3",
        policy_version="policy-v3.0.0",
        review_result="REVISE",
        findings=[],
        unverified_checks=[],
    )
    brief = DecisionEngine.evaluate(
        project_id="nap-pillow-cn-20260811-001",
        policy=DecisionPolicy(),
        review=review,
        supplier_quote=EvidenceState.CONFIRMED,
        bom=EvidenceState.CONFIRMED,
        durability_test=EvidenceState.CONFIRMED,
        material_test=EvidenceState.CONFIRMED,
        conflict_refs=["nap-conflict-mechanism-v3"],
        option_refs=["nap-option-mechanism-v3"],
        data_mode="REAL",
        repeated_critical_test_failure=True,
    )
    payload = {
        "scenario": "REPEATED_CRITICAL_DURABILITY_FAILURE",
        "revision": 3,
        "business_state": "NO-GO",
        "chat_is_business_state": False,
        "decision_brief": brief.model_dump(mode="json"),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
