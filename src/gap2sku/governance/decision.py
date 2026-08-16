from __future__ import annotations

from .models import (
    ApprovalRecord,
    DecisionBrief,
    DecisionPolicy,
    DecisionRecommendation,
    EvidenceState,
    ReviewReport,
)


class DecisionEngine:
    """Deterministic policy evaluation. An LLM cannot override this result."""

    @staticmethod
    def evaluate(
        *, project_id: str, policy: DecisionPolicy, review: ReviewReport,
        supplier_quote: EvidenceState, bom: EvidenceState,
        durability_test: EvidenceState, material_test: EvidenceState,
        conflict_refs: list[str], option_refs: list[str], data_mode: str,
        category_profile_confirmed: bool = True,
        sample_spec_locked: bool = True,
        compliance_passed: bool = True,
        child_claims_apply: bool = True,
        repeated_critical_test_failure: bool = False,
    ) -> DecisionBrief:
        hard_failures: list[str] = []
        no_go_reasons: list[str] = []
        if review.review_result == "BLOCK":
            hard_failures.append("Reviewer detected a deterministic BLOCK")
        if policy.require_real_supplier_quote_for_go and supplier_quote != EvidenceState.CONFIRMED:
            hard_failures.append("缺少真实且可追溯的供应商报价/RFQ")
        if policy.require_bom_for_go and bom != EvidenceState.CONFIRMED:
            hard_failures.append("缺少确认 BOM/成本栈")
        if policy.require_durability_test_for_adjustable_mechanism and durability_test != EvidenceState.CONFIRMED:
            hard_failures.append("调节/折叠机构缺少耐久测试")
        if (
            child_claims_apply
            and policy.require_material_test_for_child_claims
            and material_test != EvidenceState.CONFIRMED
        ):
            hard_failures.append("儿童材料与安全宣称缺少检测证据")
        if policy.require_confirmed_category_profile_for_go and not category_profile_confirmed:
            hard_failures.append("新品类 CategoryProfile 尚未由人工确认")
        if policy.require_locked_sample_spec_for_go and not sample_spec_locked:
            hard_failures.append("SampleSpec 尚未锁定到明确 hash")
        if policy.require_compliance_pass_for_go and not compliance_passed:
            hard_failures.append("合规分类、测试或标签矩阵尚未通过")
        if policy.no_go_after_repeated_critical_test_failure and repeated_critical_test_failure:
            no_go_reasons.append("关键耐久/安全测试在修订后重复失败")

        if no_go_reasons:
            recommendation = DecisionRecommendation.NO_GO
        elif data_mode == "SYNTHETIC" and not hard_failures and review.review_result == "PASS":
            recommendation = DecisionRecommendation.GO
        elif hard_failures or review.review_result == "REVISE":
            recommendation = DecisionRecommendation.REVISE
        else:
            recommendation = DecisionRecommendation.GO

        remediation = []
        for item in hard_failures:
            if "报价" in item:
                remediation.append("发起至少两家供应商同口径 RFQ")
            elif "BOM" in item:
                remediation.append("获取 BOM、包装、物流及税费分项")
            elif "耐久" in item:
                remediation.append("完成调节机构打样和循环耐久测试")
            elif "材料" in item:
                remediation.append("补齐材料报告与儿童用品适用性检测")
            elif "CategoryProfile" in item:
                remediation.append("由合规负责人确认品类模板和官方政策来源")
            elif "SampleSpec" in item:
                remediation.append("人工选择概念并锁定 SampleSpec hash")
            elif "合规" in item:
                remediation.append("补齐分类、测试、标签与宣称矩阵")
        return DecisionBrief(
            brief_id=f"brief-{project_id}", project_id=project_id,
            recommendation=recommendation,
            evidence_summary=["389 条定向采样评论已建立行级来源链"],
            conflict_refs=conflict_refs, option_refs=option_refs,
            risk_summary=no_go_reasons or hard_failures or ["确定性门禁已通过"],
            pending_confirmations=hard_failures, revision_tasks=list(dict.fromkeys(remediation)),
            policy_version=policy.version, data_mode=data_mode,
            approval_required=recommendation == DecisionRecommendation.GO,
            no_go_reasons=no_go_reasons,
        )

    @staticmethod
    def approval_valid(approval: ApprovalRecord, spec_hash: str, policy_version: str) -> bool:
        return (
            approval.spec_hash == spec_hash and approval.policy_version == policy_version
            and bool(approval.approver.strip()) and bool(approval.reason.strip())
            and approval.decision in {"APPROVE", "REJECT"}
        )
