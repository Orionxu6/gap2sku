"""Category-agnostic second-case proof: an adult desktop headphone hanger.

The public path uses captured public listing signals and must end in REVISE.
The synthetic path supplies clearly labelled fake RFQ/BOM/test inputs and proves
that the same governed path can reach GO after a spec/policy-bound approval.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .artifacts.store import ArtifactStore
from .collaboration.models import CollaborationEvent
from .collaboration.store import CollaborationStore
from .governance.decision import DecisionEngine
from .governance.models import (
    ApprovalRecord,
    ConflictCard,
    DecisionPolicy,
    EvidenceState,
    ReviewFinding,
    ReviewReport,
)
from .product.workflow import CategoryRegistry
from .schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from .schemas.product import (
    Claim,
    ClaimRegister,
    ComplianceAssessment,
    ComplianceCheck,
    CompliancePolicyPack,
    DecisionToSamplePack,
    IntakeMode,
    OpportunityBrief,
    PolicyRule,
    ProductConcept,
    ProductConceptSet,
    ProductIntake,
    PublicSupplierSignal,
    PublicSupplierSignalSet,
    RenderManifest,
    RenderPromptRecord,
    RFQPack,
    SampleSpec,
    TestCase,
    TestMatrix,
)
from .story.service import ProductStoryService
from .tasking.models import TaskContract, TaskState
from .tasking.store import TaskStore

PUBLIC_PROJECT_ID = "desk-headphone-hanger-us-public-001"
SYNTHETIC_PROJECT_ID = "desk-headphone-hanger-us-synthetic-001"
SOURCE_DATA = Path("data/public_signals/desk_headphone_hanger.json")
HERO_ASSET = Path("web/assets/concepts/new-category/concept-a-headphone-hanger.png")


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class NewCategoryPipeline:
    """Run the same decision firewall on a category unrelated to the nap pillow."""

    def __init__(
        self,
        *,
        synthetic: bool,
        db_path: str | Path,
        output_dir: str | Path,
        source_path: str | Path = SOURCE_DATA,
    ) -> None:
        self.synthetic = synthetic
        self.data_mode = "SYNTHETIC" if synthetic else "PUBLIC_SIGNAL"
        self.project_id = SYNTHETIC_PROJECT_ID if synthetic else PUBLIC_PROJECT_ID
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.source_path = Path(source_path)
        self.policy = DecisionPolicy(
            policy_id="gap2sku-adult-desk-accessory",
            version="policy-us-desktop-organization-v1.0.0",
            price_min_cny=69,
            price_max_cny=99,
        )
        self.artifacts = ArtifactStore(db_path)
        self.tasks = TaskStore(db_path)
        self.collaboration = CollaborationStore(db_path)

    def close(self) -> None:
        self.collaboration.close()
        self.tasks.close()
        self.artifacts.close()

    def _artifact(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        task: TaskContract,
        payload: dict[str, Any],
        refs: list[str],
        *,
        data_mode: str | None = None,
    ) -> ArtifactEnvelope:
        envelope = ArtifactEnvelope(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            artifact_version=1,
            project_id=self.project_id,
            producer_agent=task.owner,
            producer_task_id=task.task_id,
            status=ArtifactStatus.VALID,
            input_refs=refs,
            content_hash=_digest(payload),
            policy_version=self.policy.version,
            data_mode=data_mode or self.data_mode,
            payload=payload,
        )
        return self.artifacts.commit(
            envelope,
            self.artifacts.project_revision(self.project_id),
            f"{self.project_id}:{artifact_id}:v1",
        )

    def _task(self, slug: str, owner: str, dependencies: list[str] | None = None) -> TaskContract:
        task = self.tasks.create(
            TaskContract(
                task_id=f"{self.project_id}-{slug}-r001",
                project_id=self.project_id,
                owner=owner,
                depends_on=dependencies or [],
                idempotency_key=f"{self.project_id}:{slug}:r001",
                acceptance_criteria=[
                    "schema valid",
                    "input refs resolvable",
                    "evidence class and data mode explicit",
                ],
            )
        )
        if task.state == TaskState.PENDING:
            self.tasks.advance(task.task_id, TaskState.READY, owner, "dependencies accepted")
            self.tasks.advance(task.task_id, TaskState.RUNNING, owner, "execution started")
        return self.tasks.get(task.task_id) or task

    def _finish(self, task: TaskContract, refs: list[str]) -> None:
        current = self.tasks.get(task.task_id)
        if current and current.state == TaskState.RUNNING:
            self.tasks.advance(task.task_id, TaskState.SUBMITTED, task.owner, "artifacts submitted", refs)
            self.tasks.advance(
                task.task_id,
                TaskState.ACCEPTED,
                "acceptance-gate",
                "artifact contract passed",
                refs,
            )

    def _event(
        self,
        task: TaskContract,
        event_type: str,
        summary: str,
        recipients: list[str],
        refs: list[str],
    ) -> None:
        self.collaboration.append_event(
            CollaborationEvent(
                event_id=f"evt-{task.task_id}-{event_type.lower()}",
                project_id=self.project_id,
                task_id=task.task_id,
                revision=1,
                event_type=event_type,
                sender=task.owner,
                recipients=recipients,
                summary=summary,
                artifact_refs=refs,
                status="accepted",
                data_mode=self.data_mode,
            )
        )

    def run(self) -> dict[str, Any]:
        started = time.time()
        snapshot = json.loads(self.source_path.read_text(encoding="utf-8"))

        leader = self._task("intake", "gap2sku-product-architect")
        intake_model = ProductIntake(
            project_id=self.project_id,
            mode=IntakeMode.NEW_CONCEPT,
            title="折叠夹持式桌边耳机与线材挂架",
            target_market="US",
            target_users=["adult home-office users", "gaming and creator desks"],
            category_hint="foldable desk accessory headphone hanger",
            idea_or_problem="在不损伤桌面的前提下，兼顾耳机收纳、线材归位与折叠避让",
            hard_constraints={
                "target_retail_cny": [69, 99],
                "target_contribution_margin": 0.4,
                "rated_load_kg": 2.0,
                "no_drill": True,
            },
            source_urls=[row["source_url"] for row in snapshot["signals"]],
        )
        intake = self._artifact(
            "desk-product-intake-v1",
            ArtifactType.PRODUCT_INTAKE,
            leader,
            intake_model.model_dump(mode="json"),
            [],
        )
        profile_model = CategoryRegistry.classify(intake_model)
        profile = self._artifact(
            "desk-category-profile-v1",
            ArtifactType.CATEGORY_PROFILE,
            leader,
            profile_model.model_dump(mode="json"),
            [intake.artifact_id],
        )
        policy_model = CompliancePolicyPack(
            pack_id=profile_model.policy_pack_ref,
            version="1.0.0",
            target_market="US",
            category_profile_ref=profile_model.profile_id,
            rules=[
                PolicyRule(
                    rule_id="MECH-HAZARD-001",
                    title="夹伤、锐边、脱落与静载风险评估",
                    source_uri="https://www.cpsc.gov/Business--Manufacturing/Business-Education",
                    source_version="captured-2026-08-15",
                    applies_when="consumer desk accessory uses clamp and folding mechanism",
                    required_evidence=["edge inspection", "static load", "folding cycle", "desk surface test"],
                ),
                PolicyRule(
                    rule_id="CLAIM-001",
                    title="性能与材料宣称必须有合理依据",
                    source_uri="https://www.ftc.gov/business-guidance/advertising-marketing",
                    source_version="captured-2026-08-15",
                    applies_when="marketing makes load, durability or material claims",
                    required_evidence=["claim register", "test result", "material declaration"],
                ),
            ],
            status=profile_model.status,
        )
        policy = self._artifact(
            "desk-compliance-policy-pack-v1",
            ArtifactType.COMPLIANCE_POLICY_PACK,
            leader,
            policy_model.model_dump(mode="json"),
            [profile.artifact_id],
        )
        research_model = CategoryRegistry.research_plan(intake_model, profile_model)
        research = self._artifact(
            "desk-research-plan-v1",
            ArtifactType.RESEARCH_PLAN,
            leader,
            research_model.model_dump(mode="json"),
            [intake.artifact_id, profile.artifact_id, policy.artifact_id],
        )
        self._finish(leader, [intake.artifact_id, profile.artifact_id, policy.artifact_id, research.artifact_id])
        self._event(
            leader,
            "TASK_ASSIGNMENT",
            "新品类模板已确认；Market、Supply 与 Compliance 并行研究。",
            ["gap2sku-market", "gap2sku-supply", "gap2sku-compliance"],
            [research.artifact_id],
        )

        market = self._task("market", "gap2sku-market", [leader.task_id])
        opportunity_model = OpportunityBrief(
            brief_id="desk-opportunity-brief-v1",
            project_id=self.project_id,
            target_segment="重视桌面整洁且频繁拿取耳机的成人办公/游戏用户",
            pain_point_refs=["desk-damage", "cable-clutter", "hook-obstruction", "headband-pressure"],
            competitor_gaps=[
                "粘贴式存在胶层老化与残胶风险",
                "固定式挂钩在不用时占用腿部或桌边空间",
                "窄钩面可能形成耳机头梁压痕",
            ],
            innovation_questions=[
                "能否用可逆夹持代替钻孔和长期胶粘？",
                "能否将折叠避让、宽支撑面和线材槽组合而不过度增加成本？",
            ],
            evidence_refs=[snapshot["snapshot_id"]],
            limitations=["本轮没有代表性评论样本", "公开页面只提供机会和供应线索"],
        )
        opportunity = self._artifact(
            "desk-opportunity-brief-v1",
            ArtifactType.OPPORTUNITY_BRIEF,
            market,
            opportunity_model.model_dump(mode="json"),
            [research.artifact_id],
        )
        self._finish(market, [opportunity.artifact_id])
        self._event(
            market,
            "HANDOFF",
            "形成成人桌面收纳机会图；公开页面不是代表性市场需求证明。",
            ["gap2sku-product-architect", "gap2sku-prototype-designer"],
            [opportunity.artifact_id],
        )

        supply = self._task("supply", "gap2sku-supply", [leader.task_id])
        public_signals = []
        for row in snapshot["signals"]:
            public_signals.append(
                PublicSupplierSignal(
                    signal_id=row["signal_id"],
                    supplier_name=row["supplier_name"],
                    source_url=row["source_url"],
                    captured_at=snapshot["captured_at"],
                    source_hash=_digest(row),
                    observed_facts=row["observed_facts"],
                    limitations=row["limitations"],
                )
            )
        signal_set_model = PublicSupplierSignalSet(
            signal_set_id="desk-public-supplier-signals-v1",
            project_id=self.project_id,
            signals=public_signals,
        )
        signals = self._artifact(
            "desk-public-supplier-signals-v1",
            ArtifactType.PUBLIC_SUPPLIER_SIGNAL_SET,
            supply,
            signal_set_model.model_dump(mode="json"),
            [research.artifact_id],
            data_mode="PUBLIC_SIGNAL",
        )
        supply_payload = {
            "candidate_count": len(public_signals),
            "candidate_refs": [item.signal_id for item in public_signals],
            "quote_state": "CONFIRMED_SYNTHETIC" if self.synthetic else "MISSING",
            "bom_state": "CONFIRMED_SYNTHETIC" if self.synthetic else "MISSING",
            "matched_spec_rfq": self.synthetic,
            "synthetic_factory": {
                "supplier": "SYNTHETIC-DESK-HARDWARE-FACTORY",
                "exw_unit_cny": 22.8,
                "moq": 500,
                "sample_lead_days": 9,
            }
            if self.synthetic
            else None,
            "public_signal_policy": "shortlist and RFQ target only; never verified cost",
            "data_mode": self.data_mode,
        }
        supplier = self._artifact(
            "desk-supplier-assessment-v1",
            ArtifactType.SUPPLIER_ASSESSMENT,
            supply,
            supply_payload,
            [signals.artifact_id],
        )
        self._finish(supply, [signals.artifact_id, supplier.artifact_id])
        self._event(
            supply,
            "HANDOFF" if self.synthetic else "NEEDS_EVIDENCE",
            "已加载合成同规格 RFQ。" if self.synthetic else "发现 3 条公开供应线索，但同规格 RFQ 与 BOM 仍缺失。",
            ["gap2sku-product-architect", "gap2sku-economics"],
            [signals.artifact_id, supplier.artifact_id],
        )

        compliance_task = self._task("compliance", "gap2sku-compliance", [leader.task_id])
        compliance_model = ComplianceAssessment(
            assessment_id="desk-compliance-v1",
            project_id=self.project_id,
            classification="adult mechanical desk accessory",
            profile_status=profile_model.status,
            checks=[
                ComplianceCheck(
                    check_id="mechanical",
                    title="夹持、折叠、锐边与静载安全",
                    result="PASS_SYNTHETIC" if self.synthetic else "PLANNED",
                    policy_refs=[policy_model.pack_id],
                    evidence_refs=[],
                    remediation=["完成静载、循环、夹伤和桌面损伤检查"],
                ),
                ComplianceCheck(
                    check_id="materials",
                    title="材料、表面处理与接触垫声明",
                    result="PASS_SYNTHETIC" if self.synthetic else "MISSING",
                    policy_refs=[policy_model.pack_id],
                    evidence_refs=[],
                    remediation=["获取材料与表面处理声明"],
                ),
                ComplianceCheck(
                    check_id="claims",
                    title="2 kg 承重与耐久宣称",
                    result="PASS_SYNTHETIC" if self.synthetic else "PROHIBITED_PENDING_TEST",
                    policy_refs=[policy_model.pack_id],
                    evidence_refs=[],
                    remediation=["测试通过前不得发布承重和循环寿命宣称"],
                ),
            ],
            overall_result="PASS_SYNTHETIC" if self.synthetic else "REVISE",
            unverified_items=[] if self.synthetic else ["static load", "folding cycle", "material declaration"],
        )
        compliance = self._artifact(
            "desk-compliance-assessment-v1",
            ArtifactType.COMPLIANCE_ASSESSMENT,
            compliance_task,
            compliance_model.model_dump(mode="json"),
            [profile.artifact_id, policy.artifact_id],
        )
        self._finish(compliance_task, [compliance.artifact_id])
        self._event(
            compliance_task,
            "HANDOFF" if self.synthetic else "COMPLIANCE_FLAG",
            "合成测试证据通过。" if self.synthetic else "风险矩阵已建立；承重、循环和材料声明仍待补证。",
            ["gap2sku-product-architect", "gap2sku-reviewer"],
            [compliance.artifact_id],
        )

        prototype = self._task(
            "prototype",
            "gap2sku-prototype-designer",
            [market.task_id, supply.task_id, compliance_task.task_id],
        )
        concepts_model = ProductConceptSet(
            concept_set_id="desk-product-concepts-v1",
            project_id=self.project_id,
            concepts=[
                ProductConcept(
                    concept_id="desk-concept-a",
                    title="可逆夹持宽面折叠钩",
                    strategy="低风险平衡型",
                    pain_point_refs=opportunity_model.pain_point_refs,
                    differentiators=["10–45 mm 可逆夹持", "38 mm 宽支撑面", "折叠避让", "双线材槽"],
                    parameter_ranges={"clamp_mm": [10, 45], "rated_load_kg": 2.0},
                    materials=["anodized aluminum", "glass-fiber nylon", "silicone pads"],
                    tradeoffs=["零模具创新程度有限", "可逆安装与耐久更易验证"],
                    risk_flags=["夹紧力和桌面压痕需实测"],
                    render_manifest_refs=["desk-render-concept-a-v1"],
                ),
                ProductConcept(
                    concept_id="desk-concept-b",
                    title="磁吸快拆模块",
                    strategy="高差异化",
                    pain_point_refs=opportunity_model.pain_point_refs,
                    differentiators=["挂钩模块快拆", "左右位置切换", "线材模块可替换"],
                    parameter_ranges={"clamp_mm": [12, 42], "rated_load_kg": 1.8},
                    materials=["aluminum", "PA66-GF", "encapsulated magnets"],
                    tradeoffs=["交互新颖", "磁体成本、夹手和兼容性风险更高"],
                    risk_flags=["磁体保持力与脱落模式待验证"],
                ),
                ProductConcept(
                    concept_id="desk-concept-c",
                    title="超薄粘贴折叠钩",
                    strategy="极致成本型",
                    pain_point_refs=opportunity_model.pain_point_refs,
                    differentiators=["超薄隐藏", "最低零件数", "线材扣一体化"],
                    parameter_ranges={"adhesive_area_mm2": [2200, 3000], "rated_load_kg": 1.2},
                    materials=["injection-molded ABS", "silicone", "pressure-sensitive adhesive"],
                    tradeoffs=["成本低", "残胶、老化和不可逆安装风险"],
                    risk_flags=["不同桌面涂层兼容性待验证"],
                ),
            ],
            selected_concept_id="desk-concept-a",
            selection_reason="在供应证据不足时，优先锁定可逆安装、失效模式清晰且易测试的平衡方案",
        )
        prompt_model = RenderPromptRecord(
            prompt_id="desk-render-prompt-a-v1",
            project_id=self.project_id,
            concept_ref="desk-concept-a",
            sample_spec_hash=None,
            provider="codex-built-in-fallback",
            model="imagegen-project-asset",
            seed=20260815,
            prompt=(
                "成人桌面用可逆夹持折叠耳机与线材挂架；石墨色铝合金夹具、硅胶保护垫、"
                "宽面圆角挂钩和双线材槽；展示展开与折叠状态；高级工作室产品摄影。"
            ),
            negative_prompt="品牌、文字、认证标志、人体、手、不可制造结构、未在规格中的功能",
            input_refs=[opportunity.artifact_id, supplier.artifact_id, compliance.artifact_id],
        )
        prompt = self._artifact(
            "desk-render-prompt-a-v1",
            ArtifactType.RENDER_PROMPT,
            prototype,
            prompt_model.model_dump(mode="json"),
            prompt_model.input_refs,
            data_mode="SYNTHETIC",
        )
        asset_hash = "sha256:" + hashlib.sha256(HERO_ASSET.read_bytes()).hexdigest()
        render_model = RenderManifest(
            render_id="desk-render-concept-a-v1",
            prompt_ref=prompt.artifact_id,
            provider="codex-built-in-fallback",
            model="imagegen-project-asset",
            seed=prompt_model.seed,
            asset_uri="/static/assets/concepts/new-category/concept-a-headphone-hanger.png",
            asset_hash=asset_hash,
            sample_spec_hash=None,
            data_mode="SYNTHETIC",
        )
        render = self._artifact(
            "desk-render-concept-a-v1",
            ArtifactType.RENDER_MANIFEST,
            prototype,
            render_model.model_dump(mode="json"),
            [prompt.artifact_id],
            data_mode="SYNTHETIC",
        )
        concepts = self._artifact(
            "desk-product-concepts-v1",
            ArtifactType.PRODUCT_CONCEPT_SET,
            prototype,
            concepts_model.model_dump(mode="json"),
            [opportunity.artifact_id, supplier.artifact_id, compliance.artifact_id, render.artifact_id],
        )
        sample_model = SampleSpec(
            sample_spec_id="desk-sample-spec-v1",
            project_id=self.project_id,
            category_profile_ref=profile_model.profile_id,
            selected_concept_ref="desk-concept-a",
            parameters={
                "installation": "reversible screw clamp",
                "clamp_range_mm": [10, 45],
                "folding_angle_deg": 90,
                "rated_load_kg": 2.0,
                "cable_slots": 2,
            },
            materials=[
                {"component": "clamp_and_hook", "material": "anodized aluminum", "status": "UNVERIFIED"},
                {"component": "hinge", "material": "PA66-GF candidate", "status": "UNVERIFIED"},
                {"component": "contact_pad", "material": "silicone candidate", "status": "UNVERIFIED"},
            ],
            dimensions={"overall_mm": [92, 58, 105], "folded_mm": [92, 58, 32], "hook_width_mm": 38},
            tolerances={"dimension_mm": 0.5, "folding_angle_deg": 2},
            test_requirements=[
                "2 kg static load for 24 h",
                "10,000 folding cycles",
                "desk surface indentation and slip test",
                "edge, pinch and fastener inspection",
            ],
            lock_status="LOCKED",
            locked_by="human-manager-new-category-demo",
        )
        sample = self._artifact(
            "desk-sample-spec-v1",
            ArtifactType.SAMPLE_SPEC,
            prototype,
            sample_model.model_dump(mode="json"),
            [concepts.artifact_id],
        )
        rfq_model = RFQPack(
            rfq_id="desk-rfq-pack-v1",
            project_id=self.project_id,
            sample_spec_ref=sample.artifact_id,
            sample_spec_hash=sample_model.spec_hash,
            render_refs=[render.artifact_id],
            quantity=3,
            target_moq=500,
            target_lead_days=30,
            packaging_requirements=["single-unit recyclable carton", "surface protection", "batch trace label"],
            trade_terms=["EXW", "FOB"],
            questions=[
                "分项 BOM 与工艺",
                "500/1000/3000 阶梯价",
                "模具/NRE",
                "样品和量产交期",
                "静载、循环和表面处理证据",
            ],
            status="RESPONDED_SYNTHETIC" if self.synthetic else "AWAITING_MATCHED_SPEC_RESPONSE",
        )
        rfq = self._artifact(
            "desk-rfq-pack-v1",
            ArtifactType.RFQ_PACK,
            prototype,
            rfq_model.model_dump(mode="json"),
            [sample.artifact_id, render.artifact_id, signals.artifact_id],
        )
        self._finish(prototype, [concepts.artifact_id, sample.artifact_id, render.artifact_id, rfq.artifact_id])
        self._event(
            prototype,
            "HANDOFF",
            "三套方案完成并锁定平衡型 SampleSpec；效果图仅为 SYNTHETIC_CONCEPT。",
            ["gap2sku-supply", "gap2sku-economics", "gap2sku-reviewer"],
            [concepts.artifact_id, sample.artifact_id, rfq.artifact_id],
        )

        economics_task = self._task("economics", "gap2sku-economics", [supply.task_id])
        economics_payload = {
            "target_retail_cny": 89.0,
            "factory_cost_cny": 22.8 if self.synthetic else None,
            "cost_stack_cny": {
                "factory": 22.8,
                "packaging": 2.2,
                "inbound_and_fulfilment": 8.5,
                "platform_and_payment": 11.6,
                "returns_allowance": 3.9,
            }
            if self.synthetic
            else None,
            "verified_profit": {
                "contribution_cny": 40.0,
                "contribution_margin": 0.449,
                "status": "CONFIRMED_SYNTHETIC",
            }
            if self.synthetic
            else None,
            "public_listing_ranges": [item.observed_facts for item in public_signals],
            "public_listing_use": "context only, excluded from verified profit",
            "cost_state": "CONFIRMED_SYNTHETIC" if self.synthetic else "ESTIMATED_SIGNAL_ONLY",
            "data_mode": self.data_mode,
            "warning": "SYNTHETIC — not a commercial conclusion" if self.synthetic else "No matched-spec quote; profit cannot be verified",
        }
        economics = self._artifact(
            "desk-economics-v1",
            ArtifactType.ECONOMICS,
            economics_task,
            economics_payload,
            [supplier.artifact_id, rfq.artifact_id],
        )
        self._finish(economics_task, [economics.artifact_id])
        self._event(
            economics_task,
            "HANDOFF" if self.synthetic else "RISK_ALERT",
            "合成成本栈达到目标。" if self.synthetic else "公开展示价不能替代项目报价，利润保持未验证。",
            ["gap2sku-product-architect", "gap2sku-reviewer"],
            [economics.artifact_id],
        )

        tests_model = TestMatrix(
            matrix_id="desk-test-matrix-v1",
            project_id=self.project_id,
            tests=[
                TestCase(
                    test_id="static-load",
                    name="2 kg 静载",
                    method="2 kg / 24 h at clamp extremes",
                    acceptance_criteria="无滑移、裂纹、永久变形或桌面可见损伤",
                    sample_size=3,
                    status="PASS_SYNTHETIC" if self.synthetic else "PLANNED",
                ),
                TestCase(
                    test_id="fold-cycle",
                    name="折叠循环",
                    method="10,000 full folding cycles",
                    acceptance_criteria="无断裂、松脱，保持力衰减不超过规定阈值",
                    sample_size=3,
                    status="PASS_SYNTHETIC" if self.synthetic else "PLANNED",
                ),
                TestCase(
                    test_id="desk-contact",
                    name="桌面接触兼容性",
                    method="wood veneer, glass and painted MDF contact trial",
                    acceptance_criteria="无明显压痕、划伤或不可清洁残留",
                    sample_size=9,
                    status="PASS_SYNTHETIC" if self.synthetic else "PLANNED",
                ),
            ],
        )
        tests = self._artifact(
            "desk-test-matrix-v1",
            ArtifactType.TEST_MATRIX,
            compliance_task,
            tests_model.model_dump(mode="json"),
            [sample.artifact_id, compliance.artifact_id],
        )
        claims_model = ClaimRegister(
            register_id="desk-claim-register-v1",
            project_id=self.project_id,
            claims=[
                Claim(
                    claim_id="claim-load",
                    text="承重 2 kg",
                    status="VERIFIED_SYNTHETIC" if self.synthetic else "PROHIBITED_PENDING_TEST",
                    evidence_refs=[tests.artifact_id] if self.synthetic else [],
                ),
                Claim(
                    claim_id="claim-surface",
                    text="不伤桌面",
                    status="VERIFIED_SYNTHETIC" if self.synthetic else "PROHIBITED_PENDING_TEST",
                    evidence_refs=[tests.artifact_id] if self.synthetic else [],
                ),
            ],
        )
        claims = self._artifact(
            "desk-claim-register-v1",
            ArtifactType.CLAIM_REGISTER,
            compliance_task,
            claims_model.model_dump(mode="json"),
            [tests.artifact_id],
        )

        reviewer = self._task(
            "review",
            "gap2sku-reviewer",
            [prototype.task_id, economics_task.task_id],
        )
        product_spec_payload = {
            "title": intake_model.title,
            "selected_concept_ref": concepts.artifact_id,
            "sample_spec_ref": sample.artifact_id,
            "sample_spec_hash": sample_model.spec_hash,
            "rfq_ref": rfq.artifact_id,
            "economics_ref": economics.artifact_id,
            "compliance_ref": compliance.artifact_id,
            "test_matrix_ref": tests.artifact_id,
            "claim_register_ref": claims.artifact_id,
            "data_mode": self.data_mode,
        }
        product_spec_hash = _digest(product_spec_payload)
        product_spec_payload["spec_hash"] = product_spec_hash
        product_spec = self._artifact(
            "desk-product-spec-v1",
            ArtifactType.PRODUCT_SPEC,
            reviewer,
            product_spec_payload,
            [
                concepts.artifact_id,
                sample.artifact_id,
                rfq.artifact_id,
                economics.artifact_id,
                compliance.artifact_id,
                tests.artifact_id,
                claims.artifact_id,
            ],
        )
        findings = []
        if not self.synthetic:
            findings = [
                ReviewFinding(
                    finding_id="desk-finding-rfq",
                    rule_id="SUP-001",
                    severity="ERROR",
                    result="FAIL",
                    owner="gap2sku-supply",
                    message="公开供应条目不是与锁定 SampleSpec 绑定的真实 RFQ",
                    artifact_refs=[signals.artifact_id, rfq.artifact_id],
                    remediation=["向至少两家候选供应商发送同口径 RFQ 并导入响应"],
                ),
                ReviewFinding(
                    finding_id="desk-finding-bom",
                    rule_id="ECO-001",
                    severity="ERROR",
                    result="FAIL",
                    owner="gap2sku-economics",
                    message="BOM 和完整成本栈缺失，利润不可验证",
                    artifact_refs=[economics.artifact_id],
                    remediation=["导入 BOM、包装、物流、平台费用、税费和退货假设"],
                ),
                ReviewFinding(
                    finding_id="desk-finding-tests",
                    rule_id="SAFE-001",
                    severity="ERROR",
                    result="FAIL",
                    owner="gap2sku-compliance",
                    message="承重、折叠循环、桌面损伤和材料声明未形成证据",
                    artifact_refs=[tests.artifact_id, compliance.artifact_id],
                    remediation=["按 TestMatrix 打样并导入可追溯测试记录"],
                ),
            ]
        report_model = ReviewReport(
            review_id="desk-review-v1",
            task_id=reviewer.task_id,
            revision=1,
            product_spec_ref=product_spec.artifact_id,
            product_spec_hash=product_spec_hash,
            policy_version=self.policy.version,
            review_result="PASS" if self.synthetic else "REVISE",
            findings=findings,
            unverified_checks=[] if self.synthetic else ["matched-spec RFQ", "BOM", "static load", "folding cycle"],
        )
        review = self._artifact(
            "desk-review-report-v1",
            ArtifactType.REVIEW_RESULT,
            reviewer,
            report_model.model_dump(mode="json"),
            [product_spec.artifact_id],
        )
        self._finish(reviewer, [product_spec.artifact_id, review.artifact_id])
        self._event(
            reviewer,
            "HANDOFF" if self.synthetic else "REVIEW_FINDING",
            "合成回归门禁全部通过。" if self.synthetic else "阻止 GO：同规格报价、BOM 和测试证据未闭环。",
            ["gap2sku-product-architect", "human-manager"],
            [review.artifact_id],
        )

        decision_task = self._task("decision", "gap2sku-product-architect", [reviewer.task_id])
        conflict_models = [
            ConflictCard(
                conflict_id="desk-conflict-mechanism-v1",
                title="折叠便利与结构耐久/夹伤风险",
                conflict_type="USER_VALUE_VS_SAFETY",
                claims=["折叠避让提升桌下空间利用", "转轴与夹持结构需承受长期循环"],
                evidence_refs=[sample.artifact_id, tests.artifact_id],
                policy_refs=[self.policy.version],
                unresolved_gaps=[] if self.synthetic else ["静载、折叠循环与夹伤点评估缺失"],
                severity="HIGH",
                status="RESOLVED_SYNTHETIC" if self.synthetic else "OPEN",
            ),
            ConflictCard(
                conflict_id="desk-conflict-cost-v1",
                title="目标售价与未知同规格报价/BOM",
                conflict_type="PRICE_VS_MANUFACTURING",
                claims=["目标零售价 ¥69–99", "公开列表价不能替代锁定规格报价"],
                evidence_refs=[signals.artifact_id, economics.artifact_id, rfq.artifact_id],
                policy_refs=[self.policy.version],
                unresolved_gaps=[] if self.synthetic else ["同规格 RFQ、BOM 与完整成本栈缺失"],
                severity="CRITICAL",
                status="RESOLVED_SYNTHETIC" if self.synthetic else "OPEN",
            ),
            ConflictCard(
                conflict_id="desk-conflict-surface-v1",
                title="不伤桌面宣称与材料/接触面证据",
                conflict_type="CLAIM_VS_TEST_EVIDENCE",
                claims=["硅胶垫与宽夹面降低桌面损伤", "不同桌板材质和厚度响应未知"],
                evidence_refs=[claims.artifact_id, compliance.artifact_id, tests.artifact_id],
                policy_refs=[self.policy.version],
                unresolved_gaps=[] if self.synthetic else ["桌板兼容、压痕和材料声明测试缺失"],
                severity="HIGH",
                status="RESOLVED_SYNTHETIC" if self.synthetic else "OPEN",
            ),
        ]
        conflict_artifacts = [
            self._artifact(
                model.conflict_id,
                ArtifactType.CONFLICT_CARD,
                decision_task,
                model.model_dump(mode="json"),
                model.evidence_refs,
            )
            for model in conflict_models
        ]
        brief_model = DecisionEngine.evaluate(
            project_id=self.project_id,
            policy=self.policy,
            review=report_model,
            supplier_quote=EvidenceState.CONFIRMED if self.synthetic else EvidenceState.MISSING,
            bom=EvidenceState.CONFIRMED if self.synthetic else EvidenceState.MISSING,
            durability_test=EvidenceState.CONFIRMED if self.synthetic else EvidenceState.MISSING,
            material_test=EvidenceState.CONFIRMED if self.synthetic else EvidenceState.MISSING,
            conflict_refs=[artifact.artifact_id for artifact in conflict_artifacts],
            option_refs=[],
            data_mode=self.data_mode,
            category_profile_confirmed=profile_model.go_eligible,
            sample_spec_locked=sample_model.lock_status == "LOCKED",
            compliance_passed=compliance_model.overall_result == "PASS_SYNTHETIC",
            child_claims_apply=False,
        )
        brief_model.evidence_summary = [
            "3 条带时间戳和内容 hash 的公开供应线索已分级",
            "公开展示价仅用于候选漏斗，不进入验证利润",
        ]
        brief = self._artifact(
            "desk-decision-brief-v1",
            ArtifactType.DECISION_BRIEF,
            decision_task,
            brief_model.model_dump(mode="json"),
            [review.artifact_id, product_spec.artifact_id]
            + [artifact.artifact_id for artifact in conflict_artifacts],
        )
        approval: ArtifactEnvelope | None = None
        if self.synthetic:
            approval_model = ApprovalRecord(
                approval_id="desk-synthetic-approval-v1",
                spec_hash=product_spec_hash,
                policy_version=self.policy.version,
                approver="human-manager-synthetic-regression",
                reason="仅批准 SYNTHETIC 回归流程，不形成商业立项结论",
                decision="APPROVE",
            )
            if not DecisionEngine.approval_valid(approval_model, product_spec_hash, self.policy.version):
                raise RuntimeError("synthetic approval failed exact hash/policy validation")
            approval = self._artifact(
                "desk-synthetic-approval-v1",
                ArtifactType.APPROVAL,
                decision_task,
                approval_model.model_dump(mode="json"),
                [product_spec.artifact_id, brief.artifact_id],
                data_mode="SYNTHETIC",
            )
        story_model = ProductStoryService.build(
            project_id=self.project_id,
            recommendation=brief_model.recommendation.value,
            data_mode=self.data_mode,
            concepts=concepts_model,
            sample_spec=sample_model,
            rfq=rfq_model,
            compliance=compliance_model,
            tests=tests_model,
            economics=economics_payload,
            evidence={
                "review_count": len(public_signals),
                "pain_points": [
                    {"pain_point_id": "desk-damage", "title": "安装可能损伤桌面", "summary": "胶粘、压痕与残胶需要验证"},
                    {"pain_point_id": "cable-clutter", "title": "耳机与线材分散", "summary": "收纳和拿取路径需要一体化"},
                    {"pain_point_id": "hook-obstruction", "title": "固定挂钩占用桌边空间", "summary": "不用时应折叠避让"},
                ],
                "supplier_signals": signal_set_model.model_dump(mode="json"),
                "limitations": opportunity_model.limitations,
            },
            review=report_model.model_dump(mode="json"),
            title="桌边耳机挂架 · 决策故事",
            subtitle="从新品构思、公开供应线索到可执行 RFQ 的证据闭环",
            render_assets={
                "desk-concept-a": "/static/assets/concepts/new-category/concept-a-headphone-hanger.png"
            },
        )
        story_model.hero_render_ref = "/static/assets/concepts/new-category/concept-a-headphone-hanger.png"
        story = self._artifact(
            "desk-product-story-v1",
            ArtifactType.PRODUCT_STORY,
            decision_task,
            story_model.model_dump(mode="json"),
            [brief.artifact_id, product_spec.artifact_id, render.artifact_id],
        )
        pack_model = DecisionToSamplePack(
            pack_id="desk-decision-to-sample-v1",
            project_id=self.project_id,
            recommendation=brief_model.recommendation.value,
            selected_concept_ref=concepts.artifact_id,
            sample_spec_ref=sample.artifact_id,
            rfq_pack_ref=rfq.artifact_id,
            economics_ref=economics.artifact_id,
            compliance_ref=compliance.artifact_id,
            test_matrix_ref=tests.artifact_id,
            review_ref=review.artifact_id,
            story_ref=story.artifact_id,
            pending_tasks=brief_model.revision_tasks,
            artifact_refs=[
                brief.artifact_id,
                concepts.artifact_id,
                sample.artifact_id,
                rfq.artifact_id,
                economics.artifact_id,
                compliance.artifact_id,
                tests.artifact_id,
                story.artifact_id,
            ] + ([approval.artifact_id] if approval else []),
        )
        pack = self._artifact(
            "desk-decision-to-sample-v1",
            ArtifactType.DECISION_TO_SAMPLE_PACK,
            decision_task,
            pack_model.model_dump(mode="json"),
            pack_model.artifact_refs,
        )
        current = self.tasks.get(decision_task.task_id)
        if current and current.state == TaskState.RUNNING:
            self.tasks.advance(
                decision_task.task_id,
                TaskState.SUBMITTED,
                decision_task.owner,
                "Decision-to-Sample Pack submitted",
                [brief.artifact_id, story.artifact_id, pack.artifact_id],
            )
            if self.synthetic:
                self.tasks.advance(
                    decision_task.task_id,
                    TaskState.ACCEPTED,
                    "acceptance-gate",
                    "synthetic exact-hash approval and all gates passed",
                    [approval.artifact_id] if approval else [],
                )
            else:
                self.tasks.advance(
                    decision_task.task_id,
                    TaskState.REVISE,
                    "gap2sku-reviewer",
                    "matched-spec supply and test evidence required",
                    [review.artifact_id],
                )
        self._event(
            decision_task,
            "DECISION_RECORD",
            f"Decision-to-Sample Pack 已生成；结论 {brief_model.recommendation.value}。",
            ["human-manager"],
            [brief.artifact_id, story.artifact_id, pack.artifact_id],
        )

        result = {
            "project_id": self.project_id,
            "category": profile_model.category_name,
            "recommendation": brief_model.recommendation.value,
            "data_mode": self.data_mode,
            "public_supplier_signal_count": len(public_signals),
            "public_signals_used_as_quote": False,
            "matched_spec_quote_state": "CONFIRMED_SYNTHETIC" if self.synthetic else "MISSING",
            "verified_profit": economics_payload["verified_profit"],
            "sample_spec_hash": sample_model.spec_hash,
            "product_spec_hash": product_spec_hash,
            "approval_ref": approval.artifact_id if approval else None,
            "concept_count": len(concepts_model.concepts),
            "task_count": len(self.tasks.list(self.project_id)),
            "artifact_count": len(self.artifacts.list_all(self.project_id)),
            "product_story_ref": story.artifact_id,
            "decision_to_sample_pack_ref": pack.artifact_id,
            "story_url": "/story?project=desk-synthetic" if self.synthetic else "/story?project=desk-public",
            "elapsed_ms": int((time.time() - started) * 1000),
        }
        (self.output_dir / "run.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "supplier-signal-manifest.json").write_text(
            json.dumps(signal_set_model.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.close()
        return result
