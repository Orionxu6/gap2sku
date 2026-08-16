from __future__ import annotations

from typing import Any

from ..schemas.product import (
    ComplianceAssessment,
    ProductConceptSet,
    ProductStoryBundle,
    RFQPack,
    SampleSpec,
    TestMatrix,
)


class ProductStoryService:
    ALLOWED_VIEWS = {"internal", "supplier", "judge"}

    @classmethod
    def build(
        cls, *, project_id: str, recommendation: str, data_mode: str,
        concepts: ProductConceptSet, sample_spec: SampleSpec, rfq: RFQPack,
        compliance: ComplianceAssessment, tests: TestMatrix,
        economics: dict[str, Any], evidence: dict[str, Any], review: dict[str, Any],
        title: str = "学生午睡枕 · 决策故事",
        subtitle: str = "从用户缺陷到可打样方案的证据闭环",
        render_assets: dict[str, str] | None = None,
    ) -> ProductStoryBundle:
        selected = next(c for c in concepts.concepts if c.concept_id == concepts.selected_concept_id)
        refs = [concepts.concept_set_id, sample_spec.sample_spec_id, rfq.rfq_id,
                compliance.assessment_id, tests.matrix_id]
        return ProductStoryBundle(
            bundle_id=f"story-{project_id}-v1", project_id=project_id, version=1,
            recommendation=recommendation, data_mode=data_mode,
            title=title, subtitle=subtitle,
            hero_render_ref=selected.render_manifest_refs[0] if selected.render_manifest_refs else None,
            sections={
                "overview": {"selected_concept": selected.model_dump(mode="json"), "spec_hash": sample_spec.spec_hash},
                "evidence": evidence,
                "concepts": concepts.model_dump(mode="json"),
                "sample_spec": sample_spec.model_dump(mode="json"),
                "supplier_rfq": rfq.model_dump(mode="json"),
                "economics": economics,
                "compliance": compliance.model_dump(mode="json"),
                "tests": tests.model_dump(mode="json"),
                "review": review,
                "render_assets": render_assets or {},
            }, artifact_refs=refs,
        )

    @classmethod
    def for_view(cls, bundle: ProductStoryBundle, view: str) -> dict[str, Any]:
        if view not in cls.ALLOWED_VIEWS:
            raise ValueError(f"unknown story view: {view}")
        payload = bundle.model_dump(mode="json")
        if view == "supplier":
            payload["sections"].pop("economics", None)
            payload["sections"].pop("review", None)
            payload["subtitle"] = "脱敏打样与询价说明"
        elif view == "judge":
            allowed = {"overview", "evidence", "concepts", "sample_spec", "compliance", "review"}
            payload["sections"] = {key: value for key, value in payload["sections"].items() if key in allowed}
            payload["subtitle"] = "AgentTeam 冲突解决与决策审计"
        payload["view"] = view
        return payload
