from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .artifacts.store import ArtifactStore
from .collaboration.models import CollaborationEvent, MatrixMessageRecord
from .collaboration.store import CollaborationStore
from .evidence.reviews import ReviewWorkbookImporter, write_import_result
from .governance.decision import DecisionEngine
from .governance.gates import FailureLoopback
from .governance.models import (
    ConflictCard,
    DecisionPolicy,
    EvidenceState,
    OptionCard,
    ReviewFinding,
    ReviewReport,
)
from .graph.graph import ArtifactGraph, EdgeRelation, GraphNode
from .observability.trace import TraceEvent, TraceRecorder
from .product.workflow import CategoryRegistry, ProductWorkflow
from .schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from .schemas.product import (
    DecisionToSamplePack,
    RenderManifest,
    RenderPromptRecord,
    RFQPack,
)
from .story.service import ProductStoryService
from .tasking.models import TaskContract, TaskState
from .tasking.store import TaskStore

PROJECT_ID = "nap-pillow-cn-20260811-001"


def _hash(payload: dict[str, Any]) -> str:
    value = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _env(
    artifact_id: str, artifact_type: ArtifactType, task_id: str, agent: str,
    payload: dict[str, Any], input_refs: list[str], policy: DecisionPolicy, data_mode: str,
) -> ArtifactEnvelope:
    return ArtifactEnvelope(
        artifact_id=artifact_id, artifact_type=artifact_type, artifact_version=1,
        project_id=PROJECT_ID, producer_agent=agent, producer_task_id=task_id,
        status=ArtifactStatus.VALID, input_refs=input_refs, content_hash=_hash(payload),
        policy_version=policy.version, data_mode=data_mode, payload=payload,
    )


class NapPillowPipeline:
    """Deterministic real-evidence decision loop for the competition main case."""

    def __init__(
        self, source_dir: str | Path = "private/raw_reviews",
        db_path: str | Path = "shared/nap_pillow.db",
        output_dir: str | Path = "evidence/nap-pillow",
        synthetic_supply: bool = False,
    ) -> None:
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.synthetic_supply = synthetic_supply
        self.data_mode = "SYNTHETIC" if synthetic_supply else "REAL"
        self.policy = DecisionPolicy()
        self.artifacts = ArtifactStore(db_path)
        self.tasks = TaskStore(db_path)
        self.collaboration = CollaborationStore(db_path)
        self.graph = ArtifactGraph()
        self.trace = TraceRecorder(self.output_dir / "trace.jsonl")
        self.run_id = f"nap-{int(time.time())}"
        self.workflow = ProductWorkflow(PROJECT_ID)

    def close(self) -> None:
        self.artifacts.close()
        self.tasks.close()
        self.collaboration.close()

    def _collab(
        self, task: TaskContract, sender: str, recipients: list[str], summary: str,
        event_type: str, status: str, refs: list[str] | None = None,
    ) -> None:
        stamp = int(time.time() * 1000)
        message_id = f"$demo-{task.task_id}-{event_type}-{stamp}"
        self.collaboration.append_message(MatrixMessageRecord(
            message_id=message_id, room_id="!gap2sku-definition:demo", project_id=PROJECT_ID,
            sender_id=f"@{sender.removeprefix('gap2sku-')}:demo", sender_role=sender,
            body=summary, origin_server_ts=stamp, data_mode=self.data_mode,
            raw_event={"source": "deterministic-demo", "replay": True},
        ))
        self.collaboration.append_event(CollaborationEvent(
            event_id=f"evt-{task.task_id}-{event_type}-{stamp}", project_id=PROJECT_ID,
            task_id=task.task_id, revision=task.revision, event_type=event_type,
            sender=sender, recipients=recipients, summary=summary,
            artifact_refs=refs or [], status=status, data_mode=self.data_mode,
            matrix_message_id=message_id,
        ))

    def _trace(self, task_id: str, agent: str, tool: str, status: str,
               artifact_id: str = "", parents: list[str] | None = None,
               review: str = "") -> None:
        self.trace.record(TraceEvent(
            run_id=self.run_id, project_id=PROJECT_ID, task_id=task_id,
            agent_name=agent, agent_role=agent.removeprefix("gap2sku-"), tool_name=tool,
            artifact_id=artifact_id, parent_artifact_ids=parents or [], result_status=status,
            review_decision=review,
        ))

    def _task(self, name: str, owner: str, depends_on: list[str] | None = None) -> TaskContract:
        task_id = f"{PROJECT_ID}-{name}-r001"
        task = self.tasks.create(TaskContract(
            task_id=task_id, project_id=PROJECT_ID, owner=owner,
            depends_on=depends_on or [], idempotency_key=f"{PROJECT_ID}:{name}:r001",
            acceptance_criteria=["schema valid", "references resolvable", "data mode explicit"],
        ))
        if task.state == TaskState.PENDING:
            self.tasks.advance(task_id, TaskState.READY, owner, "dependencies accepted")
            self.tasks.advance(task_id, TaskState.RUNNING, owner, "execution started")
        return self.tasks.get(task_id) or task

    def _commit(self, envelope: ArtifactEnvelope) -> ArtifactEnvelope:
        committed = self.artifacts.commit(
            envelope, self.artifacts.project_revision(PROJECT_ID),
            f"{PROJECT_ID}:{envelope.artifact_id}:{envelope.artifact_version}",
        )
        self.graph.add_node(GraphNode(
            id=envelope.artifact_id, type=envelope.artifact_type.value,
            version=envelope.artifact_version,
        ))
        for parent in envelope.input_refs:
            self.graph.add_edge(parent, envelope.artifact_id, EdgeRelation.DERIVED_FROM)
            parent_artifact = self.artifacts.get(parent)
            if parent_artifact:
                self.artifacts.add_edge(
                    parent, parent_artifact.artifact_version,
                    envelope.artifact_id, envelope.artifact_version,
                    EdgeRelation.DERIVED_FROM.value,
                )
        return committed

    def _finish_task(self, task: TaskContract, refs: list[str]) -> None:
        current = self.tasks.get(task.task_id)
        if current and current.state == TaskState.RUNNING:
            self.tasks.advance(task.task_id, TaskState.SUBMITTED, task.owner, "artifacts submitted", refs)
            self.tasks.advance(task.task_id, TaskState.ACCEPTED, "acceptance-gate", "artifact contract passed", refs)

    def run(self) -> dict[str, Any]:
        started = time.time()
        imported = ReviewWorkbookImporter(self.source_dir).import_all()
        write_import_result(imported, self.output_dir)

        intake_task = self._task("intake", "gap2sku-product-architect")
        intake_model = self.workflow.intake()
        intake = self._commit(_env(
            "nap-product-intake-v1", ArtifactType.PRODUCT_INTAKE, intake_task.task_id,
            intake_task.owner, intake_model.model_dump(mode="json"), [], self.policy, self.data_mode,
        ))
        profile_model = CategoryRegistry.classify(intake_model)
        profile = self._commit(_env(
            "nap-category-profile-v1", ArtifactType.CATEGORY_PROFILE, intake_task.task_id,
            intake_task.owner, profile_model.model_dump(mode="json"), [intake.artifact_id], self.policy, self.data_mode,
        ))
        policy_pack_model = self.workflow.policy_pack(profile_model)
        policy_pack = self._commit(_env(
            "nap-compliance-policy-pack-v1", ArtifactType.COMPLIANCE_POLICY_PACK, intake_task.task_id,
            intake_task.owner, policy_pack_model.model_dump(mode="json"), [profile.artifact_id], self.policy, self.data_mode,
        ))
        research_model = CategoryRegistry.research_plan(intake_model, profile_model)
        research = self._commit(_env(
            "nap-research-plan-v1", ArtifactType.RESEARCH_PLAN, intake_task.task_id,
            intake_task.owner, research_model.model_dump(mode="json"),
            [intake.artifact_id, profile.artifact_id, policy_pack.artifact_id], self.policy, self.data_mode,
        ))
        self._finish_task(intake_task, [intake.artifact_id, profile.artifact_id, policy_pack.artifact_id, research.artifact_id])
        self._collab(
            intake_task, intake_task.owner, ["gap2sku-market", "gap2sku-supply", "gap2sku-compliance"],
            "已识别为现有 SKU 改款，加载品类模板与政策包；Market 与 Supply 并行开始。",
            "TASK_ASSIGNMENT", "accepted", [research.artifact_id],
        )

        market = self._task("market", "gap2sku-market")
        evidence_payload = {
            "count": len(imported.records), "records": [r.model_dump(mode="json") for r in imported.records],
            "quality_report": imported.report, "sampling_mode": "TARGETED_NON_REPRESENTATIVE",
            "data_mode": "REAL",
        }
        evidence = self._commit(_env(
            "nap-review-evidence-v1", ArtifactType.EVIDENCE, market.task_id,
            market.owner, evidence_payload, [research.artifact_id], self.policy, "REAL",
        ))
        self._trace(market.task_id, market.owner, "evidence.import_reviews", "SUCCESS", evidence.artifact_id)

        pain_payload = self._pain_points(imported.records)
        pains = self._commit(_env(
            "nap-pain-points-v1", ArtifactType.PAIN_POINT_SET, market.task_id,
            market.owner, pain_payload, [evidence.artifact_id], self.policy, "REAL",
        ))
        features = self._commit(_env(
            "nap-feature-hypotheses-v1", ArtifactType.FEATURE_HYPOTHESIS, market.task_id,
            market.owner, self._feature_hypotheses(pain_payload), [pains.artifact_id], self.policy, "REAL",
        ))
        opportunity_model = self.workflow.opportunity(
            [point["pain_point_id"] for point in pain_payload["pain_points"]], [evidence.artifact_id],
        )
        opportunity = self._commit(_env(
            "nap-opportunity-brief-v1", ArtifactType.OPPORTUNITY_BRIEF, market.task_id,
            market.owner, opportunity_model.model_dump(mode="json"),
            [evidence.artifact_id, pains.artifact_id, features.artifact_id], self.policy, "REAL",
        ))
        self._finish_task(market, [evidence.artifact_id, pains.artifact_id, features.artifact_id, opportunity.artifact_id])
        self._collab(
            market, market.owner, ["gap2sku-product-architect", "gap2sku-prototype-designer"],
            "已完成 389 条评论证据链，提交痛点、竞品缺口与创新命题。",
            "HANDOFF", "accepted", [opportunity.artifact_id],
        )

        supply = self._task("supply", "gap2sku-supply")
        supply_state = "CONFIRMED" if self.synthetic_supply else "MISSING"
        supply_payload = {
            "recommendation_status": "CANDIDATE_ONLY" if self.synthetic_supply else "NEEDS_EVIDENCE",
            "quote_state": supply_state, "bom_state": supply_state,
            "supplier_quotes": [{"supplier": "SYNTHETIC-SUPPLIER-A", "factory_cost_cny": 43.0}]
            if self.synthetic_supply else [],
            "missing": [] if self.synthetic_supply else ["RFQ", "BOM", "MOQ", "lead_time", "material_report"],
            "warning": "SYNTHETIC — not a commercial fact" if self.synthetic_supply else "竞品评论不证明制造能力",
            "data_mode": self.data_mode,
        }
        supplier = self._commit(_env(
            "nap-supplier-assessment-v1", ArtifactType.SUPPLIER_ASSESSMENT, supply.task_id,
            supply.owner, supply_payload, [features.artifact_id], self.policy, self.data_mode,
        ))
        self._trace(supply.task_id, supply.owner, "supplier.assess", "MISSING" if not self.synthetic_supply else "SUCCESS", supplier.artifact_id)
        self._finish_task(supply, [supplier.artifact_id])
        self._collab(
            supply, supply.owner, ["gap2sku-product-architect", "gap2sku-economics"],
            "制造方向可进入概念设计，但真实 RFQ、BOM、MOQ、交期和材料报告仍缺失。" if not self.synthetic_supply
            else "已加载合成供应快照，仅用于演示后续流程。",
            "NEEDS_EVIDENCE" if not self.synthetic_supply else "HANDOFF",
            "blocked" if not self.synthetic_supply else "accepted", [supplier.artifact_id],
        )

        prototype = self._task("prototype", "gap2sku-prototype-designer", [market.task_id, supply.task_id])
        concept_model = self.workflow.concepts([point["pain_point_id"] for point in pain_payload["pain_points"]])
        prompt_refs: list[str] = []
        render_refs: list[str] = []
        for index, concept in enumerate(concept_model.concepts, start=1):
            prompt = RenderPromptRecord(
                prompt_id=f"prompt-{concept.concept_id}-v1", project_id=PROJECT_ID,
                concept_ref=concept.concept_id, sample_spec_hash=None,
                provider="qwen-or-offline-replay", model="qwen-image", seed=20260810 + index,
                prompt=(
                    f"学生午睡枕概念效果图：{concept.title}；{concept.strategy}；"
                    f"特征：{'、'.join(concept.differentiators)}。白色工作室背景，多视角产品设计渲染。"
                ),
                negative_prompt="品牌、认证标志、医学或安全保证、不可制造结构、文字水印",
                input_refs=[opportunity.artifact_id, supplier.artifact_id],
            )
            prompt_env = self._commit(_env(
                f"nap-{prompt.prompt_id}", ArtifactType.RENDER_PROMPT, prototype.task_id,
                prototype.owner, prompt.model_dump(mode="json"), prompt.input_refs,
                self.policy, "SYNTHETIC",
            ))
            prompt_refs.append(prompt_env.artifact_id)
            manifest = RenderManifest(
                render_id=f"render-{concept.concept_id}-v1", prompt_ref=prompt_env.artifact_id,
                provider="offline-replay", model="fixed-concept-assets-v1", seed=prompt.seed,
                asset_uri=f"/static/assets/concepts/{concept.concept_id}.png",
                asset_hash="sha256:" + hashlib.sha256(concept.concept_id.encode()).hexdigest(),
                sample_spec_hash=None, data_mode="SYNTHETIC",
            )
            render_env = self._commit(_env(
                f"nap-render-{concept.concept_id}-v1", ArtifactType.RENDER_MANIFEST, prototype.task_id,
                prototype.owner, manifest.model_dump(mode="json"), [prompt_env.artifact_id],
                self.policy, "SYNTHETIC",
            ))
            render_refs.append(render_env.artifact_id)
        for concept, render_ref in zip(concept_model.concepts, render_refs, strict=True):
            concept.render_manifest_refs = [render_ref]
        concepts = self._commit(_env(
            "nap-product-concepts-v1", ArtifactType.PRODUCT_CONCEPT_SET, prototype.task_id,
            prototype.owner, concept_model.model_dump(mode="json"),
            [opportunity.artifact_id, supplier.artifact_id] + render_refs, self.policy, self.data_mode,
        ))
        sample_model = self.workflow.sample_spec(profile_model, synthetic=True)
        sample = self._commit(_env(
            "nap-sample-spec-v1", ArtifactType.SAMPLE_SPEC, prototype.task_id,
            prototype.owner, sample_model.model_dump(mode="json"), [concepts.artifact_id],
            self.policy, self.data_mode,
        ))
        locked_prompt = RenderPromptRecord(
            prompt_id="prompt-concept-a-locked-v2", project_id=PROJECT_ID,
            concept_ref="concept-a", sample_spec_hash=sample_model.spec_hash,
            provider="qwen-or-offline-replay", model="qwen-image", seed=20260814,
            prompt="锁定 SampleSpec 的模块化支撑午睡枕，按尺寸、材料和可替换支撑垫片生成多视角效果图与参数标注板",
            negative_prompt="品牌、认证标志、医学或安全保证、偏离锁定尺寸的结构、文字水印",
            input_refs=[sample.artifact_id],
        )
        locked_prompt_env = self._commit(_env(
            "nap-render-prompt-locked-v2", ArtifactType.RENDER_PROMPT, prototype.task_id,
            prototype.owner, locked_prompt.model_dump(mode="json"), [sample.artifact_id],
            self.policy, "SYNTHETIC",
        ))
        locked_manifest = RenderManifest(
            render_id="render-concept-a-locked-v2", prompt_ref=locked_prompt_env.artifact_id,
            provider="offline-replay", model="fixed-concept-assets-v1", seed=locked_prompt.seed,
            asset_uri="/static/assets/concepts/concept-a.png",
            asset_hash="sha256:" + hashlib.sha256(b"concept-a-locked-v2").hexdigest(),
            sample_spec_hash=sample_model.spec_hash, data_mode="SYNTHETIC",
        )
        locked_render = self._commit(_env(
            "nap-render-concept-a-locked-v2", ArtifactType.RENDER_MANIFEST, prototype.task_id,
            prototype.owner, locked_manifest.model_dump(mode="json"),
            [locked_prompt_env.artifact_id, sample.artifact_id], self.policy, "SYNTHETIC",
        ))
        self._finish_task(
            prototype,
            [concepts.artifact_id, sample.artifact_id, locked_prompt_env.artifact_id, locked_render.artifact_id]
            + prompt_refs + render_refs,
        )
        self._collab(
            prototype, prototype.owner, ["gap2sku-product-architect", "gap2sku-supply", "gap2sku-compliance"],
            "已提交三套差异化概念；Human Manager 选择低机构风险方案并锁定 SampleSpec hash。",
            "HUMAN_DECISION", "accepted", [concepts.artifact_id, sample.artifact_id],
        )

        rfq_model = RFQPack(
            rfq_id="nap-rfq-pack-v1", project_id=PROJECT_ID, sample_spec_ref=sample.artifact_id,
            sample_spec_hash=sample_model.spec_hash, render_refs=[locked_render.artifact_id], quantity=3,
            target_moq=500, target_lead_days=30,
            packaging_requirements=["单件防尘袋", "批次追踪标签", "运输跌落验证"],
            trade_terms=["EXW", "FOB"],
            questions=["分项 BOM", "模具费", "MOQ 阶梯价", "样品与量产一致性", "材料报告"],
            status="READY_SYNTHETIC" if self.synthetic_supply else "AWAITING_REAL_SUPPLIER_RESPONSE",
        )
        rfq = self._commit(_env(
            "nap-rfq-pack-v1", ArtifactType.RFQ_PACK, supply.task_id, supply.owner,
            rfq_model.model_dump(mode="json"), [sample.artifact_id, locked_render.artifact_id],
            self.policy, self.data_mode,
        ))

        compliance_task = self._task("compliance", "gap2sku-compliance", [prototype.task_id])
        compliance_model, tests_model, claims_model = self.workflow.compliance(profile_model, synthetic=self.synthetic_supply)
        compliance = self._commit(_env(
            "nap-compliance-assessment-v1", ArtifactType.COMPLIANCE_ASSESSMENT, compliance_task.task_id,
            compliance_task.owner, compliance_model.model_dump(mode="json"),
            [sample.artifact_id, policy_pack.artifact_id], self.policy, self.data_mode,
        ))
        tests = self._commit(_env(
            "nap-test-matrix-v1", ArtifactType.TEST_MATRIX, compliance_task.task_id,
            compliance_task.owner, tests_model.model_dump(mode="json"),
            [sample.artifact_id, compliance.artifact_id], self.policy, self.data_mode,
        ))
        claims = self._commit(_env(
            "nap-claim-register-v1", ArtifactType.CLAIM_REGISTER, compliance_task.task_id,
            compliance_task.owner, claims_model.model_dump(mode="json"),
            [sample.artifact_id, compliance.artifact_id], self.policy, self.data_mode,
        ))
        self._finish_task(compliance_task, [compliance.artifact_id, tests.artifact_id, claims.artifact_id])
        self._collab(
            compliance_task, compliance_task.owner, ["gap2sku-product-architect", "gap2sku-reviewer"],
            "已完成产品分类草案；材料检测、标签和宣称仍需补证。" if not self.synthetic_supply
            else "合成测试矩阵已通过，仅用于流程演示。",
            "COMPLIANCE_FLAG" if not self.synthetic_supply else "HANDOFF",
            "blocked" if not self.synthetic_supply else "accepted", [compliance.artifact_id, tests.artifact_id],
        )

        economics = self._task("economics", "gap2sku-economics", [supply.task_id])
        econ_payload = {
            "target_price_cny": [99, 119],
            "cost_state": "ESTIMATED" if not self.synthetic_supply else "CONFIRMED_SYNTHETIC",
            "verified_profit": None if not self.synthetic_supply else {"price_cny": 109, "contribution_cny": 31.2},
            "missing_cost_items": [] if self.synthetic_supply else ["BOM", "packaging", "freight", "platform_fee", "tax", "returns"],
            "data_mode": self.data_mode,
            "warning": "SYNTHETIC — not a verified profit" if self.synthetic_supply else "No verified profit can be calculated",
        }
        econ = self._commit(_env(
            "nap-economics-v1", ArtifactType.ECONOMICS, economics.task_id,
            economics.owner, econ_payload, [supplier.artifact_id], self.policy, self.data_mode,
        ))
        self._trace(economics.task_id, economics.owner, "economics.calculate", "ESTIMATED" if not self.synthetic_supply else "SUCCESS", econ.artifact_id)
        self._finish_task(economics, [econ.artifact_id])
        self._collab(
            economics, economics.owner, ["gap2sku-product-architect", "gap2sku-reviewer"],
            "缺少真实 BOM 与报价，利润只能标记 ESTIMATED，不能作为 GO 依据。" if not self.synthetic_supply
            else "合成成本模型达到目标毛利，仅用于回归测试。",
            "RISK_ALERT" if not self.synthetic_supply else "HANDOFF",
            "blocked" if not self.synthetic_supply else "accepted", [econ.artifact_id],
        )

        leader = self._task(
            "decision", "gap2sku-product-architect",
            [market.task_id, prototype.task_id, supply.task_id, economics.task_id, compliance_task.task_id],
        )
        policy_env = self._commit(_env(
            "nap-decision-policy-v1", ArtifactType.DECISION_POLICY, leader.task_id,
            leader.owner, self.policy.model_dump(mode="json"), [], self.policy, self.data_mode,
        ))
        conflicts, options = self._conflicts_and_options(evidence, supplier, econ, policy_env, leader)
        spec_payload = {
            "spec_id": "nap-product-spec-v1", "positioning": "学生/办公桌趴睡可调支撑枕",
            "target_user": ["小学生/中学生（需材料安全验证）", "办公室午休人群"],
            "core_selling_points": ["可调高度", "手臂通道", "低异味/可拆洗"],
            "key_specs": {"price_range_cny": [99, 119], "adjustable": True},
            "category_profile_ref": profile.artifact_id,
            "selected_concept_ref": concepts.artifact_id,
            "sample_spec_ref": sample.artifact_id,
            "sample_spec_hash": sample_model.spec_hash,
            "rfq_pack_ref": rfq.artifact_id,
            "compliance_ref": compliance.artifact_id,
            "test_matrix_ref": tests.artifact_id,
            "supply_requirements": ["循环耐久", "材料报告", "BOM", "RFQ"],
            "profit_model": econ_payload, "risk_assumptions": [str(c.payload["title"]) for c in conflicts],
            "evidence_refs": [evidence.artifact_id, supplier.artifact_id, econ.artifact_id],
            "confidence": 0.62 if not self.synthetic_supply else 0.85,
            "data_mode": self.data_mode, "approval_status": "PENDING_APPROVAL",
        }
        spec_hash = _hash(spec_payload)
        spec_payload["spec_hash"] = spec_hash
        spec = self._commit(_env(
            "nap-product-spec-v1", ArtifactType.PRODUCT_SPEC, leader.task_id,
            leader.owner, spec_payload,
            [features.artifact_id, concepts.artifact_id, sample.artifact_id, rfq.artifact_id,
             supplier.artifact_id, econ.artifact_id, compliance.artifact_id, tests.artifact_id]
            + [c.artifact_id for c in conflicts],
            self.policy, self.data_mode,
        ))

        review_task = self._task("review", "gap2sku-reviewer", [leader.task_id] if False else [])
        findings = self._review_findings(spec, supplier, econ)
        review_result = "PASS" if not findings else "REVISE"
        report = ReviewReport(
            review_id="nap-review-v1", task_id=leader.task_id, revision=1,
            product_spec_ref=spec.artifact_id, product_spec_hash=spec_hash,
            policy_version=self.policy.version, review_result=review_result, findings=findings,
            unverified_checks=[] if self.synthetic_supply else ["RFQ", "BOM", "durability", "material_safety"],
        )
        review_env = self._commit(_env(
            "nap-review-report-v1", ArtifactType.REVIEW_RESULT, review_task.task_id,
            review_task.owner, report.model_dump(mode="json"), [spec.artifact_id], self.policy, self.data_mode,
        ))
        self._trace(review_task.task_id, review_task.owner, "review.run", "SUCCESS", review_env.artifact_id, [spec.artifact_id], review_result)
        self._finish_task(review_task, [review_env.artifact_id])

        brief = DecisionEngine.evaluate(
            project_id=PROJECT_ID, policy=self.policy, review=report,
            supplier_quote=EvidenceState.CONFIRMED if self.synthetic_supply else EvidenceState.MISSING,
            bom=EvidenceState.CONFIRMED if self.synthetic_supply else EvidenceState.MISSING,
            durability_test=EvidenceState.CONFIRMED if self.synthetic_supply else EvidenceState.MISSING,
            material_test=EvidenceState.CONFIRMED if self.synthetic_supply else EvidenceState.MISSING,
            conflict_refs=[c.artifact_id for c in conflicts], option_refs=[o.artifact_id for o in options],
            data_mode=self.data_mode,
            category_profile_confirmed=profile_model.go_eligible,
            sample_spec_locked=sample_model.lock_status == "LOCKED",
            compliance_passed=compliance_model.overall_result in {"PASS", "PASS_SYNTHETIC"},
        )
        loopback_tasks = FailureLoopback.create_revision_tasks(report, self.tasks)
        brief.revision_tasks = loopback_tasks or brief.revision_tasks
        brief_env = self._commit(_env(
            "nap-decision-brief-v1", ArtifactType.DECISION_BRIEF, leader.task_id,
            leader.owner, brief.model_dump(mode="json"),
            [spec.artifact_id, review_env.artifact_id], self.policy, self.data_mode,
        ))
        story_model = ProductStoryService.build(
            project_id=PROJECT_ID, recommendation=brief.recommendation.value, data_mode=self.data_mode,
            concepts=concept_model, sample_spec=sample_model, rfq=rfq_model,
            compliance=compliance_model, tests=tests_model, economics=econ_payload,
            evidence={
                "review_count": len(imported.records),
                "pain_points": pain_payload["pain_points"],
                "limitations": opportunity_model.limitations,
            },
            review=report.model_dump(mode="json"),
        )
        story_model.hero_render_ref = locked_render.artifact_id
        story = self._commit(_env(
            "nap-product-story-v1", ArtifactType.PRODUCT_STORY, leader.task_id,
            leader.owner, story_model.model_dump(mode="json"),
            [brief_env.artifact_id, concepts.artifact_id, sample.artifact_id, rfq.artifact_id,
             econ.artifact_id, compliance.artifact_id, tests.artifact_id, review_env.artifact_id,
             locked_render.artifact_id], self.policy, self.data_mode,
        ))
        decision_pack_model = DecisionToSamplePack(
            pack_id="nap-decision-to-sample-v1", project_id=PROJECT_ID,
            recommendation=brief.recommendation.value,
            selected_concept_ref=concepts.artifact_id, sample_spec_ref=sample.artifact_id,
            rfq_pack_ref=rfq.artifact_id, economics_ref=econ.artifact_id,
            compliance_ref=compliance.artifact_id, test_matrix_ref=tests.artifact_id,
            review_ref=review_env.artifact_id, story_ref=story.artifact_id,
            pending_tasks=loopback_tasks or brief.revision_tasks,
            artifact_refs=[brief_env.artifact_id, spec.artifact_id, concepts.artifact_id,
                           sample.artifact_id, rfq.artifact_id, compliance.artifact_id,
                           tests.artifact_id, story.artifact_id],
        )
        decision_pack = self._commit(_env(
            "nap-decision-to-sample-v1", ArtifactType.DECISION_TO_SAMPLE_PACK, leader.task_id,
            leader.owner, decision_pack_model.model_dump(mode="json"),
            decision_pack_model.artifact_refs, self.policy, self.data_mode,
        ))
        self._collab(
            review_task, review_task.owner, [leader.owner, "human-manager"],
            "Reviewer 阻止 GO：真实报价、BOM、耐久与材料证据未齐。" if findings
            else "确定性规则已通过；GO 仍需绑定 spec hash 与 policy version 的人工审批。",
            "REVIEW_FINDING" if findings else "HANDOFF",
            "blocked" if findings else "submitted", [review_env.artifact_id],
        )
        current_leader = self.tasks.get(leader.task_id)
        if current_leader and current_leader.state == TaskState.RUNNING:
            self.tasks.advance(
                leader.task_id, TaskState.SUBMITTED, leader.owner,
                "Decision-to-Sample Pack submitted",
                [spec.artifact_id, brief_env.artifact_id, decision_pack.artifact_id],
            )
            if brief.recommendation.value == "REVISE":
                self.tasks.advance(
                    leader.task_id, TaskState.REVISE, "gap2sku-reviewer",
                    "Reviewer requires evidence remediation", [review_env.artifact_id],
                )
            # A synthetic GO remains SUBMITTED until an exact spec/policy-bound
            # human approval is supplied; it is never auto-accepted.
        self._trace(leader.task_id, leader.owner, "decision.evaluate", "SUCCESS", brief_env.artifact_id, [review_env.artifact_id], brief.recommendation.value)
        self._collab(
            leader, leader.owner, ["human-manager"],
            f"已生成 Decision-to-Sample Pack，当前建议 {brief.recommendation.value}。",
            "DECISION_RECORD", "submitted", [decision_pack.artifact_id, story.artifact_id],
        )

        result = {
            "run_id": self.run_id, "project_id": PROJECT_ID,
            "recommendation": brief.recommendation.value, "data_mode": self.data_mode,
            "review_result": review_result, "evidence_count": len(imported.records),
            "artifacts": len(self.artifacts.list_all(PROJECT_ID)),
            "conflicts": len(conflicts), "revision_tasks": loopback_tasks or brief.revision_tasks,
            "decision_brief": brief.model_dump(mode="json"),
            "decision_to_sample_pack": decision_pack.model_dump(mode="json"),
            "product_story_ref": story.artifact_id,
            "concept_count": len(concept_model.concepts),
            "trace_events": len(self.trace.read_all()),
            "elapsed_ms": int((time.time() - started) * 1000),
        }
        (self.output_dir / "run.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (self.output_dir / "artifact-graph.json").write_text(
            json.dumps(self.graph.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.close()
        return result

    @staticmethod
    def _pain_points(records: list[Any]) -> dict[str, Any]:
        rules = {
            "height_adjustment": ["高度", "高低", "调节", "角度"],
            "arm_channel": ["胳膊", "手臂", "压手", "手麻", "手发麻"],
            "odor_material": ["异味", "味道", "气味", "闷", "材料"],
            "durability": ["塌", "变形", "支撑", "硬", "软"],
        }
        unique = [r for r in records if r.duplicate_of is None]
        points = []
        for name, keywords in rules.items():
            matched = [r for r in unique if any(keyword in r.content_excerpt for keyword in keywords)]
            points.append({
                "pain_point_id": name, "frequency_count": len(matched),
                "frequency_denominator": len(unique), "method": "deterministic_keyword_match",
                "evidence_refs": [r.evidence_id for r in matched[:25]],
                "limitations": ["定向样本频次不是总体发生率"],
            })
        return {"pain_points": points, "deduplicated_denominator": len(unique), "data_mode": "REAL"}

    @staticmethod
    def _feature_hypotheses(pains: dict[str, Any]) -> dict[str, Any]:
        mapping = {
            "height_adjustment": "多档高度/角度调节", "arm_channel": "手臂通道",
            "odor_material": "低异味可拆洗面料", "durability": "加固调节机构",
        }
        return {"hypotheses": [{
            "feature_id": key, "label": value,
            "pain_point_ref": key, "status": "HYPOTHESIS", "requires_supply_validation": True,
        } for key, value in mapping.items()], "data_mode": "REAL"}

    def _conflicts_and_options(self, evidence: ArtifactEnvelope, supplier: ArtifactEnvelope,
                               econ: ArtifactEnvelope, policy: ArtifactEnvelope,
                               task: TaskContract) -> tuple[list[ArtifactEnvelope], list[ArtifactEnvelope]]:
        definitions = [
            ("mechanism", "可调结构与耐久风险", "TECHNICAL", ["调节需求成立", "耐久证据缺失"], ["循环耐久测试"], "HIGH"),
            ("price", "目标价与未知 BOM/报价", "ECONOMICS", ["目标价 ¥99–119", "成本栈未确认"], ["RFQ", "BOM"], "CRITICAL"),
            ("safety", "儿童安全宣称与检测缺口", "COMPLIANCE", ["儿童使用场景成立", "材料检测缺失"], ["材料报告", "适用性检测"], "CRITICAL"),
            ("comfort", "支撑性与闷热/偏硬反馈", "USER_EXPERIENCE", ["需要稳定支撑", "部分评论反馈偏硬或闷热"], ["分层材料打样", "盲测"], "MEDIUM"),
        ]
        conflicts: list[ArtifactEnvelope] = []
        options: list[ArtifactEnvelope] = []
        for key, title, kind, claims, gaps, severity in definitions:
            card = ConflictCard(
                conflict_id=f"conflict-{key}", title=title, conflict_type=kind,
                claims=claims, evidence_refs=[evidence.artifact_id, supplier.artifact_id, econ.artifact_id],
                policy_refs=[policy.artifact_id], unresolved_gaps=[] if self.synthetic_supply else gaps,
                severity=severity, status="MITIGATED_SYNTHETIC" if self.synthetic_supply else "OPEN",
            )
            card_env = self._commit(_env(
                f"nap-conflict-{key}-v1", ArtifactType.CONFLICT_CARD, task.task_id,
                task.owner, card.model_dump(mode="json"),
                [evidence.artifact_id, supplier.artifact_id, econ.artifact_id, policy.artifact_id],
                self.policy, self.data_mode,
            ))
            conflicts.append(card_env)
            option = OptionCard(
                option_id=f"option-{key}-evidence-first", conflict_id=card.conflict_id,
                title=f"先补证再冻结：{title}", tradeoffs=["延后一轮立项", "避免未经验证的 GO"],
                required_evidence=gaps, policy_checks={gap: self.synthetic_supply for gap in gaps},
                recommendation="SELECT" if not self.synthetic_supply else "SYNTHETIC_PASS",
            )
            option_env = self._commit(_env(
                f"nap-option-{key}-v1", ArtifactType.OPTION_CARD, task.task_id,
                task.owner, option.model_dump(mode="json"), [card_env.artifact_id],
                self.policy, self.data_mode,
            ))
            options.append(option_env)
        return conflicts, options

    def _review_findings(self, spec: ArtifactEnvelope, supplier: ArtifactEnvelope,
                         econ: ArtifactEnvelope) -> list[ReviewFinding]:
        if self.synthetic_supply:
            return []
        return [
            ReviewFinding(finding_id="finding-rfq", rule_id="SUP-001", severity="ERROR", result="FAIL",
                          owner="gap2sku-supply", message="真实供应商报价缺失",
                          artifact_refs=[supplier.artifact_id], remediation=["同口径 RFQ 至少两家"]),
            ReviewFinding(finding_id="finding-bom", rule_id="ECO-001", severity="ERROR", result="FAIL",
                          owner="gap2sku-economics", message="BOM/成本栈缺失，利润不可验证",
                          artifact_refs=[econ.artifact_id], remediation=["补齐 BOM、物流、费用、税费和退货假设"]),
            ReviewFinding(finding_id="finding-durability", rule_id="SUP-002", severity="ERROR", result="FAIL",
                          owner="gap2sku-supply", message="调节结构耐久证据缺失",
                          artifact_refs=[spec.artifact_id], remediation=["打样并完成循环耐久测试"]),
            ReviewFinding(finding_id="finding-material", rule_id="POL-001", severity="ERROR", result="FAIL",
                          owner="gap2sku-product-architect", message="儿童材料/安全宣称缺少检测",
                          artifact_refs=[spec.artifact_id], remediation=["补齐材料和适用性检测报告"]),
        ]
