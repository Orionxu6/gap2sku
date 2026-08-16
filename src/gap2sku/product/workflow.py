from __future__ import annotations

from dataclasses import dataclass

from ..schemas.product import (
    CategoryProfile,
    Claim,
    ClaimRegister,
    ComplianceAssessment,
    ComplianceCheck,
    CompliancePolicyPack,
    IntakeMode,
    OpportunityBrief,
    PolicyRule,
    ProductConcept,
    ProductConceptSet,
    ProductIntake,
    ProfileStatus,
    ResearchPlan,
    ResearchWorkstream,
    SampleSpec,
    SpecField,
    TestCase,
    TestMatrix,
)


class CategoryRegistry:
    """Classify intake without pretending an unknown category is review-ready."""

    @staticmethod
    def classify(intake: ProductIntake) -> CategoryProfile:
        normalized = intake.category_hint.lower().replace("_", " ")
        known_nap = any(token in normalized for token in ("午睡", "nap pillow", "sleep pillow"))
        known_headphone_hanger = any(
            token in normalized
            for token in ("headphone hanger", "headset hanger", "耳机挂架", "desk accessory")
        )
        if known_nap:
            return CategoryProfile(
                profile_id="category-rest-support-v1",
                category_name="Rest & Sleep Support",
                version="1.0.0",
                status=ProfileStatus.CONFIRMED,
                risk_tier="ENHANCED_CHILD_SAFETY",
                spec_fields=[
                    SpecField(key="overall_dimensions", label="展开尺寸", value_type="dimensions", unit="mm"),
                    SpecField(key="folded_dimensions", label="收纳尺寸", value_type="dimensions", unit="mm"),
                    SpecField(key="adjustment_range", label="调节范围", value_type="range", unit="mm"),
                    SpecField(key="weight", label="成品重量", value_type="decimal", unit="g"),
                    SpecField(key="cover_material", label="面料", value_type="text"),
                    SpecField(key="support_material", label="支撑材料", value_type="text"),
                ],
                manufacturing_processes=["foam molding", "injection molding", "textile sewing", "assembly"],
                required_evidence=["RFQ", "BOM", "material report", "durability test", "label review"],
                policy_pack_ref="policy-us-child-rest-support-v1",
                confirmed_by="gap2sku-policy-maintainer",
            )
        if known_headphone_hanger:
            return CategoryProfile(
                profile_id="category-desktop-organization-hardware-v1",
                category_name="Desktop Organization Hardware",
                version="1.0.0",
                status=ProfileStatus.CONFIRMED,
                risk_tier="STANDARD_MECHANICAL",
                spec_fields=[
                    SpecField(key="clamp_range", label="夹持范围", value_type="range", unit="mm"),
                    SpecField(key="rated_load", label="额定承载", value_type="decimal", unit="kg"),
                    SpecField(key="folded_dimensions", label="折叠尺寸", value_type="dimensions", unit="mm"),
                    SpecField(key="contact_material", label="桌面接触材料", value_type="text"),
                    SpecField(key="surface_finish", label="表面处理", value_type="text"),
                ],
                manufacturing_processes=[
                    "aluminum extrusion or die casting",
                    "injection molding",
                    "silicone molding",
                    "hinge assembly",
                ],
                required_evidence=[
                    "matched-spec RFQ",
                    "BOM",
                    "static load test",
                    "folding cycle test",
                    "surface and edge inspection",
                ],
                policy_pack_ref="policy-us-desktop-organization-v1",
                confirmed_by="gap2sku-policy-maintainer",
            )
        generic_fields = [
            SpecField(key="dimensions", label="关键尺寸", value_type="dimensions"),
            SpecField(key="materials", label="材料与表面处理", value_type="list"),
            SpecField(key="weight", label="重量", value_type="decimal"),
            SpecField(key="critical_performance", label="关键性能", value_type="object"),
            SpecField(key="packaging", label="包装要求", value_type="object"),
        ]
        return CategoryProfile(
            profile_id=f"draft-{intake.project_id}-category-v1",
            category_name=intake.category_hint,
            version="draft-1",
            status=ProfileStatus.DRAFT,
            risk_tier="UNCLASSIFIED",
            spec_fields=generic_fields,
            manufacturing_processes=[],
            required_evidence=["category classification", "official policy sources", "test matrix", "human confirmation"],
            policy_pack_ref=f"draft-{intake.project_id}-policy-v1",
        )

    @staticmethod
    def research_plan(intake: ProductIntake, profile: CategoryProfile) -> ResearchPlan:
        sources = ["user_upload", "public_web", "authorized_mcp", "replay_snapshot"]
        streams = [
            ResearchWorkstream(owner="gap2sku-market", objective="识别需求、痛点与竞品缺口", allowed_sources=sources,
                               required_outputs=["OpportunityBrief", "PainPointSet", "CompetitorGapMap"]),
            ResearchWorkstream(owner="gap2sku-supply", objective="识别工艺边界与供应证据缺口", allowed_sources=sources,
                               required_outputs=["SupplierAssessment", "RFQPack"]),
            ResearchWorkstream(owner="gap2sku-economics", objective="建立可重算成本与利润模型", allowed_sources=sources,
                               required_outputs=["Economics", "SensitivityAnalysis"]),
            ResearchWorkstream(owner="gap2sku-compliance", objective="完成分类、政策与测试矩阵", allowed_sources=["official_source", "authorized_mcp", "user_upload"],
                               required_outputs=["ComplianceAssessment", "TestMatrix", "ClaimRegister"]),
        ]
        return ResearchPlan(
            plan_id=f"research-{intake.project_id}-v1", project_id=intake.project_id,
            profile_ref=profile.profile_id, workstreams=streams,
        )


@dataclass(frozen=True)
class ProductWorkflow:
    project_id: str

    def intake(self) -> ProductIntake:
        return ProductIntake(
            project_id=self.project_id, mode=IntakeMode.EXISTING_SKU_UPGRADE,
            title="学生午睡枕改款决策", target_market="US",
            target_users=["elementary students 6-12", "school procurement"],
            category_hint="student nap pillow", idea_or_problem="从竞品评论识别缺陷并形成可打样改款方案",
            hard_constraints={"target_price_cny": [99, 119], "target_margin": 0.40, "launch_weeks": 12},
        )

    def opportunity(self, pain_refs: list[str], evidence_refs: list[str]) -> OpportunityBrief:
        return OpportunityBrief(
            brief_id=f"opportunity-{self.project_id}-v1", project_id=self.project_id,
            target_segment="6–12 岁在校午休用户",
            pain_point_refs=pain_refs,
            competitor_gaps=["调节机构耐久与舒适难兼顾", "手臂摆放空间不足", "材料异味与安全证据不足"],
            innovation_questions=["能否用可替换支撑模块替代高故障折叠机构？", "如何在成本上限内保留通风和手臂通道？"],
            evidence_refs=evidence_refs,
            limitations=["定向评论不是市场总体发生率", "竞品评论不能证明供应商制造能力"],
        )

    def concepts(self, pain_refs: list[str]) -> ProductConceptSet:
        concepts = [
            ProductConcept(
                concept_id="concept-a", title="模块化支撑垫", strategy="低机构风险",
                pain_point_refs=pain_refs, differentiators=["可替换支撑垫片", "开放式手臂通道", "可拆洗面套"],
                parameter_ranges={"height_mm": [70, 95], "weight_g": [420, 520]},
                materials=["polyester cover", "molded foam", "PP support plate"],
                tradeoffs=["调节档位较少", "可靠性更高"], risk_flags=["材料测试待补"],
                render_manifest_refs=["render-concept-a-v1"],
            ),
            ProductConcept(
                concept_id="concept-b", title="中空通风可调芯", strategy="舒适与差异化",
                pain_point_refs=pain_refs, differentiators=["中空通风", "三档高度", "折叠收纳"],
                parameter_ranges={"height_mm": [60, 110], "weight_g": [480, 580]},
                materials=["polyester cover", "molded foam", "PP adjustment frame"],
                tradeoffs=["更强差异化", "机构成本和耐久风险增加"], risk_flags=["循环耐久待验证", "成本待 RFQ"],
                render_manifest_refs=["render-concept-b-v1"],
            ),
            ProductConcept(
                concept_id="concept-c", title="双腔软硬分区", strategy="触感优先",
                pain_point_refs=pain_refs, differentiators=["软硬双区", "宽手臂槽", "低压趴睡面"],
                parameter_ranges={"height_mm": [75, 90], "weight_g": [450, 560]},
                materials=["cool-touch cover", "dual-density foam"],
                tradeoffs=["无机械调节", "模具复杂度较高"], risk_flags=["双密度一致性待打样"],
                render_manifest_refs=["render-concept-c-v1"],
            ),
        ]
        return ProductConceptSet(
            concept_set_id=f"concepts-{self.project_id}-v1", project_id=self.project_id,
            concepts=concepts, selected_concept_id="concept-a",
            selection_reason="真实报价和耐久证据缺失时，优先选择结构风险较低的可替换支撑方案",
        )

    def sample_spec(self, profile: CategoryProfile, *, synthetic: bool) -> SampleSpec:
        return SampleSpec(
            sample_spec_id=f"sample-spec-{self.project_id}-v1", project_id=self.project_id,
            category_profile_ref=profile.profile_id, selected_concept_ref="concept-a",
            parameters={"adjustment": "replaceable pads", "colorways": ["blue", "green", "pink"]},
            materials=[{"component": "cover", "material": "polyester", "status": "UNVERIFIED"},
                       {"component": "support", "material": "molded foam + PP", "status": "UNVERIFIED"}],
            dimensions={"expanded_mm": [295, 235, 95], "folded_mm": [295, 235, 45]},
            tolerances={"dimension_mm": 3, "weight_g": 20},
            test_requirements=["10,000-cycle compression", "stability", "odor screening", "material and label review"],
            lock_status="LOCKED" if synthetic else "DRAFT",
            locked_by="human-manager-demo" if synthetic else None,
        )

    def policy_pack(self, profile: CategoryProfile) -> CompliancePolicyPack:
        rules = [
            PolicyRule(rule_id="CLASSIFY-001", title="儿童产品适用性分类", source_uri="https://www.cpsc.gov/Business--Manufacturing/Business-Education/Childrens-Products", source_version="captured-2026-08-14", applies_when="primarily intended for children 12 or younger", required_evidence=["age grading", "marketing copy", "dimensions", "label plan"]),
            PolicyRule(rule_id="MATERIAL-001", title="材料与化学物质证据", source_uri="https://www.cpsc.gov/Business--Manufacturing/Testing-Certification/Third-Party-Testing", source_version="captured-2026-08-14", applies_when="children product classification confirmed", required_evidence=["material report", "applicable third-party test"]),
            PolicyRule(rule_id="LABEL-001", title="标签与追踪信息", source_uri="https://www.cpsc.gov/Business--Manufacturing/Business-Education/tracking-label", source_version="captured-2026-08-14", applies_when="children product classification confirmed", required_evidence=["label artwork", "batch tracking plan"]),
        ]
        return CompliancePolicyPack(
            pack_id=profile.policy_pack_ref, version="1.0.0", target_market="US",
            category_profile_ref=profile.profile_id, rules=rules, status=ProfileStatus.CONFIRMED,
        )

    def compliance(self, profile: CategoryProfile, *, synthetic: bool) -> tuple[ComplianceAssessment, TestMatrix, ClaimRegister]:
        result = "PASS_SYNTHETIC" if synthetic else "REVISE"
        checks = [
            ComplianceCheck(check_id="classification", title="目标年龄与产品分类", result="CONFIRMED" if synthetic else "NEEDS_EVIDENCE", policy_refs=[profile.policy_pack_ref], evidence_refs=[], remediation=["确认年龄分级、页面文案和标签"]),
            ComplianceCheck(check_id="material", title="材料与安全检测", result="CONFIRMED_SYNTHETIC" if synthetic else "MISSING", policy_refs=[profile.policy_pack_ref], evidence_refs=[], remediation=["获取适用材料及第三方测试报告"]),
            ComplianceCheck(check_id="label", title="标签、追踪和宣称", result="CONFIRMED_SYNTHETIC" if synthetic else "DRAFT", policy_refs=[profile.policy_pack_ref], evidence_refs=[], remediation=["提交标签和宣称审查"]),
        ]
        assessment = ComplianceAssessment(
            assessment_id=f"compliance-{self.project_id}-v1", project_id=self.project_id,
            classification="children-product-candidate", profile_status=profile.status,
            checks=checks, overall_result=result,
            unverified_items=[] if synthetic else ["material test", "tracking label", "claim substantiation"],
        )
        matrix = TestMatrix(
            matrix_id=f"tests-{self.project_id}-v1", project_id=self.project_id,
            tests=[
                TestCase(test_id="durability", name="支撑结构循环耐久", method="10,000-cycle compression", acceptance_criteria="无断裂、锁止失效或永久变形超限", sample_size=3, status="PASS_SYNTHETIC" if synthetic else "PLANNED"),
                TestCase(test_id="comfort", name="舒适与稳定盲测", method="controlled user trial", acceptance_criteria="主要场景稳定且无明显压迫", sample_size=10, status="PASS_SYNTHETIC" if synthetic else "PLANNED"),
                TestCase(test_id="material", name="材料与标签检查", method="applicable lab and document review", acceptance_criteria="适用规则全部有可追溯证据", sample_size=3, status="PASS_SYNTHETIC" if synthetic else "MISSING_EVIDENCE"),
            ],
        )
        claims = ClaimRegister(
            register_id=f"claims-{self.project_id}-v1", project_id=self.project_id,
            claims=[
                Claim(claim_id="claim-adjustable", text="可替换支撑高度", status="DESIGN_INTENT", evidence_refs=[]),
                Claim(claim_id="claim-safe", text="儿童安全材料", status="PROHIBITED_PENDING_TEST", evidence_refs=[]),
                Claim(claim_id="claim-odor", text="低异味", status="PROHIBITED_PENDING_TEST", evidence_refs=[]),
            ],
        )
        return assessment, matrix, claims
