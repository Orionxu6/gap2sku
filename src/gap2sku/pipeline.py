"""Pipeline — orchestrates the full Gap2SKU Domain Core flow (spec 7, 23).

This is the deterministic offline core used by `make demo-core`.
It does NOT require AgentTeams; it drives the same domain logic that
the MCP tools expose to Workers.

Flow:
  T0 Parse & Validate Constraints
  -> T1 Market Evidence (reviews -> pain points -> feature hypotheses)
  -> T2 Supplier Capability (filter offers by constraints)
  -> T3 Baseline Fee Model
  -> T4 (merged into T1) Feature Hypotheses
  -> T5 (merged into T2) Supplier Assessment
  -> T6 Unit Economics (per candidate)
  -> T7 Product Spec V1 (decisions + spec synthesis)
  -> T8 Reviewer Gate (R001-R012)
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, cast

from .artifacts.store import ArtifactStore
from .economics.calculator import EconomicsCalculator, EconomicsInput
from .graph.graph import ArtifactGraph, EdgeRelation, GraphNode
from .observability.trace import TraceEvent, TraceRecorder
from .review.rules import ReviewerGate
from .schemas.constraint import Constraint, ConstraintOperator, ConstraintSet
from .schemas.decision import DecisionStatus, FeatureDecision
from .schemas.envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from .schemas.evidence import EvidenceRecord, RightsStatus, SourceType
from .schemas.feature import FeatureHypothesis, FeatureStatus
from .schemas.pain_point import PainPoint
from .schemas.spec import ProductSpec, SpecApprovalStatus
from .schemas.supplier import SupplierAssessment, SupplierCapability


def _envelope(
    artifact_id: str, atype: ArtifactType, project_id: str, agent: str, task: str,
    payload: dict, input_refs: list[str] | None = None,
    constraint_deps: list[str] | None = None, snapshot_ids: list[str] | None = None,
    version: int = 1,
) -> ArtifactEnvelope:
    content = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return ArtifactEnvelope(
        artifact_id=artifact_id, artifact_type=atype, artifact_version=version,
        project_id=project_id, producer_agent=agent, producer_task_id=task,
        status=ArtifactStatus.VALID, input_refs=input_refs or [],
        constraint_dependencies=constraint_deps or [], source_snapshot_ids=snapshot_ids or [],
        content_hash="sha256:" + hashlib.sha256(content.encode()).hexdigest()[:16],
        payload=payload,
    )


def default_constraints(project_id: str) -> ConstraintSet:
    """Laptop Stand demo constraints (spec 23.1)."""
    return ConstraintSet(
        project_id=project_id, version=1,
        constraints=[
            Constraint(constraint_id="retail_price_max", path="business.retail_price_max",
                       operator=ConstraintOperator.LE, value="39.99", unit="USD/unit", hard=True),
            Constraint(constraint_id="factory_cost_max", path="business.factory_cost_max",
                       operator=ConstraintOperator.LE, value="8.00", unit="USD/unit", hard=True),
            Constraint(constraint_id="moq_max", path="business.moq_max",
                       operator=ConstraintOperator.LE, value="300", unit="units", hard=True),
            Constraint(constraint_id="target_margin_min", path="business.target_margin_min",
                       operator=ConstraintOperator.GE, value="0.35", unit="ratio", hard=True),
            Constraint(constraint_id="max_laptop_size", path="product.max_laptop_size",
                       operator=ConstraintOperator.GE, value="16", unit="inch", hard=True),
        ],
    )


class DomainCorePipeline:
    """Deterministic offline pipeline. No LLM, no AgentTeams."""

    def __init__(self, fixture_dir: Path, store: ArtifactStore | None = None,
                 trace: TraceRecorder | None = None) -> None:
        self.fixture_dir = fixture_dir
        self.store = store or ArtifactStore()
        self.trace = trace or TraceRecorder()
        self.graph = ArtifactGraph()
        self.project_id = "laptop-stand-us-20260803-001"
        self.run_id = f"run-{int(time.time())}"
        self.constraints = default_constraints(self.project_id)
        self.artifacts: list[ArtifactEnvelope] = []

    def _emit(self, task_id: str, agent: str, role: str, tool: str, status: str,
              artifact_id: str = "", parent_ids: list[str] | None = None,
              latency_ms: int = 0, review_decision: str = "") -> None:
        self.trace.record(TraceEvent(
            run_id=self.run_id, project_id=self.project_id, task_id=task_id,
            agent_name=agent, agent_role=role, tool_name=tool,
            artifact_id=artifact_id, parent_artifact_ids=parent_ids or [],
            latency_ms=latency_ms, result_status=status, review_decision=review_decision,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ))

    def run(self) -> dict[str, Any]:
        t0 = time.time()
        # --- T0: constraints ---
        self._emit("T0", "gap2sku-product-architect", "leader", "state.get_constraints", "SUCCESS")
        cs_env = _envelope(
            "constraints-v001", ArtifactType.CONSTRAINT, self.project_id,
            "gap2sku-product-architect", f"{self.project_id}-constraints-r001",
            self.constraints.model_dump(mode="json"),
            constraint_deps=[c.constraint_id for c in self.constraints.constraints],
        )
        self.artifacts.append(cs_env)

        # --- T1: Market Evidence ---
        reviews = self._load_reviews()
        evidence_env = self._market_evidence(reviews)
        pain_env = self._pain_points(evidence_env)
        feature_env = self._feature_hypotheses(pain_env)

        # --- T2: Supplier Capability ---
        offers = self._load_supplier_offers()
        supply_env = self._supplier_capability(offers, feature_env)
        assessment_env = self._supplier_assessment(supply_env)

        # --- T3: Fee model ---
        fees = self._load_fees()

        # --- T6: Economics ---
        econ_env = self._economics(assessment_env, fees)

        # --- T7: Product Spec V1 ---
        spec_env = self._spec_v1(econ_env, assessment_env, feature_env, pain_env)
        decisions_env = self._decisions(feature_env, assessment_env, econ_env)

        # --- T8: Reviewer Gate ---
        review_env = self._review(spec_env, decisions_env)

        elapsed = int((time.time() - t0) * 1000)
        self._emit("pipeline", "gap2sku-product-architect", "leader", "pipeline.run", "SUCCESS",
                   latency_ms=elapsed)

        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "spec": spec_env.payload,
            "review": review_env.payload,
            "decisions": [d.payload for d in decisions_env],
            "artifact_count": len(self.artifacts),
            "elapsed_ms": elapsed,
        }

    # --- Helpers ---

    def _load_reviews(self) -> list[dict[str, Any]]:
        path = self.fixture_dir / "reviews.synthetic.jsonl"
        return [cast(dict[str, Any], json.loads(line)) for line in path.read_text().splitlines() if line.strip()]

    def _load_supplier_offers(self) -> list[dict[str, Any]]:
        path = self.fixture_dir / "supplier_offers.synthetic.json"
        return cast(list[dict[str, Any]], json.loads(path.read_text())["offers"])

    def _load_fees(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads((self.fixture_dir / "fees.v1.json").read_text()))

    def _market_evidence(self, reviews: list[dict]) -> ArtifactEnvelope:
        t = time.time()
        evidences = []
        for r in reviews[:50]:  # sample for demo
            ev = EvidenceRecord(
                evidence_id=r["review_id"], source_type=SourceType.SYNTHETIC_FIXTURE,
                source_id=r["review_id"], snapshot_id=r["snapshot_id"],
                observed_at=r["observed_at"], content_excerpt=r["text"][:120],
                content_hash=r["content_hash"], locator=r["locator"],
                rights_status=RightsStatus.SYNTHETIC, is_synthetic=True, language=r["language"],
            )
            evidences.append(ev.model_dump(mode="json"))
        env = _envelope(
            "evidence-set-v1", ArtifactType.EVIDENCE, self.project_id,
            "gap2sku-market", f"{self.project_id}-market-r001",
            {"evidences": evidences, "is_synthetic": True},
            snapshot_ids=["reviews-laptop-stand-us-synthetic-v1"],
            constraint_deps=["target_market"],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value, version=1))
        self._emit(f"{self.project_id}-market-r001", "gap2sku-market", "market",
                   "evidence.search_reviews", "SUCCESS", env.artifact_id, latency_ms=int((time.time()-t)*1000))
        return env

    def _pain_points(self, evidence_env: ArtifactEnvelope) -> ArtifactEnvelope:
        t = time.time()
        pain_data = json.loads((self.fixture_dir / "pain_points.synthetic.json").read_text())["pain_points"]
        total = len(self._load_reviews())
        pains = []
        for p in pain_data:
            related = [e for e in evidence_env.payload["evidences"] if p["pain_point_id"].split("-")[1] in e.get("content_excerpt", "").lower() or (p["feature"] in e.get("template_key", ""))]
            pains.append(PainPoint(
                pain_point_id=p["pain_point_id"], label=p["label"],
                frequency_count=len(related), frequency_denominator=total,
                frequency_method="keyword_match_on_synthetic_fixture",
                severity=p["severity"], evidence_ids=[e["evidence_id"] for e in related[:10]],
                feature_hypotheses=[p["feature"]], confidence=min(0.9, len(related)/20),
                limitations=["synthetic_fixture"] if not related else [],
            ).model_dump(mode="json"))
        env = _envelope(
            "pain-point-set-v1", ArtifactType.PAIN_POINT_SET, self.project_id,
            "gap2sku-market", f"{self.project_id}-market-r001",
            {"pain_points": pains, "is_synthetic": True},
            input_refs=[evidence_env.artifact_id], constraint_deps=["target_market"],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        self.graph.add_edge(evidence_env.artifact_id, env.artifact_id, EdgeRelation.DERIVED_FROM)
        self._emit(f"{self.project_id}-market-r001", "gap2sku-market", "market",
                   "evidence.search_reviews", "SUCCESS", env.artifact_id,
                   parent_ids=[evidence_env.artifact_id], latency_ms=int((time.time()-t)*1000))
        return env

    def _feature_hypotheses(self, pain_env: ArtifactEnvelope) -> ArtifactEnvelope:
        t = time.time()
        features_data = json.loads((self.fixture_dir / "feature_taxonomy.v1.json").read_text())["features"]
        hypos = []
        for f in features_data:
            pain_refs = [p["pain_point_id"] for p in pain_env.payload["pain_points"] if p.get("feature_hypotheses", [None])[0] == f["feature_id"]]
            hypos.append(FeatureHypothesis(
                feature_id=f["feature_id"], label=f["label"], cost_delta=f["cost_delta"],
                pain_point_refs=pain_refs, status=FeatureStatus.HYPOTHESIS,
                rationale=f"Derived from {len(pain_refs)} pain point(s)",
            ).model_dump(mode="json"))
        env = _envelope(
            "feature-hypotheses-v1", ArtifactType.FEATURE_HYPOTHESIS, self.project_id,
            "gap2sku-market", f"{self.project_id}-market-r001",
            {"hypotheses": hypos, "is_synthetic": True},
            input_refs=[pain_env.artifact_id],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        self.graph.add_edge(pain_env.artifact_id, env.artifact_id, EdgeRelation.MOTIVATES)
        self._emit(f"{self.project_id}-market-r001", "gap2sku-market", "market",
                   "evidence.search_reviews", "SUCCESS", env.artifact_id,
                   parent_ids=[pain_env.artifact_id], latency_ms=int((time.time()-t)*1000))
        return env

    def _supplier_capability(self, offers: list[dict], feature_env: ArtifactEnvelope) -> ArtifactEnvelope:
        t = time.time()
        caps = [SupplierCapability(**o).model_dump(mode="json") for o in offers]
        env = _envelope(
            "supplier-capability-set-v1", ArtifactType.SUPPLIER_CAPABILITY, self.project_id,
            "gap2sku-supply", f"{self.project_id}-supply-r001",
            {"capabilities": caps, "is_synthetic": True},
            input_refs=[feature_env.artifact_id], constraint_deps=["moq_max", "factory_cost_max"],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        self.graph.add_edge(feature_env.artifact_id, env.artifact_id, EdgeRelation.VALIDATED_BY)
        self._emit(f"{self.project_id}-supply-r001", "gap2sku-supply", "supply",
                   "evidence.get_supplier_records", "SUCCESS", env.artifact_id,
                   parent_ids=[feature_env.artifact_id], latency_ms=int((time.time()-t)*1000))
        return env

    def _supplier_assessment(self, supply_env: ArtifactEnvelope) -> ArtifactEnvelope:
        t = time.time()
        moq_max = 300
        accepted = []
        rejected = []
        conflicts = []
        for c in supply_env.payload["capabilities"]:
            if c["support_state"] in ("unsupported",):
                rejected.append(c)
                continue
            if c["support_state"] == "conflict":
                conflicts.append(c["offer_id"])
                continue
            total_cost = float(c["base_unit_cost"]) + float(c["cost_delta"])
            if c["moq"] <= moq_max and total_cost <= 8.0 and c["existing_mold"]:
                accepted.append(c)
            else:
                rejected.append(c)
        assessment = SupplierAssessment(
            assessment_id="supplier-assessment-v1",
            accepted_options=accepted, rejected_options=rejected, conflicts=conflicts,
        ).model_dump(mode="json")
        env = _envelope(
            "supplier-assessment-v1", ArtifactType.SUPPLIER_ASSESSMENT, self.project_id,
            "gap2sku-supply", f"{self.project_id}-supply-r001",
            assessment, input_refs=[supply_env.artifact_id],
            constraint_deps=["moq_max", "factory_cost_max"],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        self.graph.add_edge(supply_env.artifact_id, env.artifact_id, EdgeRelation.DERIVED_FROM)
        self._emit(f"{self.project_id}-supply-r001", "gap2sku-supply", "supply",
                   "artifact.validate_local", "SUCCESS", env.artifact_id,
                   parent_ids=[supply_env.artifact_id], latency_ms=int((time.time()-t)*1000))
        return env

    def _economics(self, assessment_env: ArtifactEnvelope, fees: dict) -> ArtifactEnvelope:
        t = time.time()
        # Use Supplier B (SUP-B) accepted option as candidate
        accepted = assessment_env.payload.get("accepted_options", [])
        if not accepted:
            raise RuntimeError("No accepted supplier options for economics")
        sup_b = next((c for c in accepted if c["supplier_id"] == "SUP-B"), accepted[0])
        factory_cost = float(sup_b["base_unit_cost"]) + float(sup_b["cost_delta"])
        inp = EconomicsInput.from_dict({
            "candidate_id": "candidate-sup-b-v1",
            "retail_price": "39.99",
            "factory_cost": str(factory_cost),
            "feature_cost_deltas": ["0.80", "0.30", "0.40"],  # wider_base + silicone + 16inch
            "packaging_cost": fees["packaging_cost"],
            "shipping_cost": fees["shipping_cost"],
            "fulfillment_fee": fees["fulfillment_fee"],
            "platform_fee_rate": fees["platform_fee_rate"],
            "marketing_rate": fees["marketing_rate"],
            "loss_allowance_rate": fees["loss_allowance_rate"],
        })
        hard_constraints = [c for c in self.constraints.constraints if c.hard]
        art = EconomicsCalculator.calculate(inp, hard_constraints)
        env = _envelope(
            "economics-v1", ArtifactType.ECONOMICS, self.project_id,
            "gap2sku-economics", f"{self.project_id}-economics-r001",
            art.model_dump(mode="json"), input_refs=[assessment_env.artifact_id],
            constraint_deps=["factory_cost_max", "target_margin_min"],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        self.graph.add_edge(assessment_env.artifact_id, env.artifact_id, EdgeRelation.CONSTRAINS)
        self._emit(f"{self.project_id}-economics-r001", "gap2sku-economics", "economics",
                   "economics.calculate", "SUCCESS", env.artifact_id,
                   parent_ids=[assessment_env.artifact_id], latency_ms=int((time.time()-t)*1000))
        return env

    def _decisions(self, feature_env: ArtifactEnvelope, assessment_env: ArtifactEnvelope,
                   econ_env: ArtifactEnvelope) -> list[ArtifactEnvelope]:
        results = []
        accepted_offers = {o["feature_id"]: o for o in assessment_env.payload["accepted_options"]}
        for fh in feature_env.payload["hypotheses"]:
            fid = fh["feature_id"]
            has_supply = fid in accepted_offers
            has_econ = econ_env.payload.get("constraint_checks") is not None
            # carbon_fiber: weak market evidence (no pain refs) + expensive
            if fid == "carbon_fiber_structure":
                status = DecisionStatus.REJECT
                rationale = "Weak market evidence (no pain point refs) and cost exceeds factory_cost_max"
                reconsider = ["If strong demand evidence emerges and cost drops below threshold"]
            elif has_supply:
                status = DecisionStatus.ACCEPT
                rationale = f"Supported by supplier {accepted_offers[fid]['supplier_id']} and within economics"
                reconsider = []
            else:
                status = DecisionStatus.DEFER
                rationale = "No confirmed supplier within constraints"
                reconsider = ["If new supplier with lower MOQ/cost is found"]
            fd = FeatureDecision(
                feature_id=fid, status=status,
                market_refs=[fh["feature_id"]] if fh["pain_point_refs"] else [],
                supply_refs=[accepted_offers[fid]["offer_id"]] if has_supply else [],
                economics_refs=[econ_env.artifact_id] if has_econ and has_supply else [],
                rationale=rationale, reconsider_if=reconsider, confidence=0.8 if has_supply else 0.3,
            )
            env = _envelope(
                f"decision-{fid}-v1", ArtifactType.FEATURE_DECISION, self.project_id,
                "gap2sku-product-architect", f"{self.project_id}-spec-r001",
                fd.model_dump(mode="json"),
                input_refs=[feature_env.artifact_id, assessment_env.artifact_id, econ_env.artifact_id],
            )
            self.artifacts.append(env)
            self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
            self.graph.add_edge(feature_env.artifact_id, env.artifact_id, EdgeRelation.SELECTED_BY if status == DecisionStatus.ACCEPT else EdgeRelation.REJECTED_BY)
            results.append(env)
        return results

    def _spec_v1(self, econ_env: ArtifactEnvelope, assessment_env: ArtifactEnvelope,
                 feature_env: ArtifactEnvelope, pain_env: ArtifactEnvelope) -> ArtifactEnvelope:
        accepted = [d.artifact_id for d in self.artifacts if d.artifact_type == ArtifactType.FEATURE_DECISION and d.payload.get("status") == "ACCEPT"]
        rejected = [d.artifact_id for d in self.artifacts if d.artifact_type == ArtifactType.FEATURE_DECISION and d.payload.get("status") == "REJECT"]
        deferred = [d.artifact_id for d in self.artifacts if d.artifact_type == ArtifactType.FEATURE_DECISION and d.payload.get("status") == "DEFER"]
        spec = ProductSpec(
            spec_id="product-spec-v1", spec_version=1, project_id=self.project_id,
            business_constraints=[c.constraint_id for c in self.constraints.constraints],
            target_market="US Amazon",
            selected_supplier_option="SUP-B",
            accepted_features=accepted, rejected_features=rejected, deferred_features=deferred,
            dimensions_and_materials={"max_laptop_size": "16 inch", "material": "aluminum alloy"},
            bom_and_cost=econ_env.payload,
            constraint_checks=econ_env.payload.get("constraint_checks", []),
            open_questions=["Confirm 16-inch compatibility across all laptop models"],
            artifact_refs=[econ_env.artifact_id, assessment_env.artifact_id, feature_env.artifact_id, pain_env.artifact_id],
            review_status="PENDING", approval_status=SpecApprovalStatus.DRAFT,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        content = spec.model_dump_json()
        spec.spec_hash = "sha256:" + hashlib.sha256(content.encode()).hexdigest()[:16]
        env = _envelope(
            "product-spec-v1", ArtifactType.PRODUCT_SPEC, self.project_id,
            "gap2sku-product-architect", f"{self.project_id}-spec-r001",
            spec.model_dump(mode="json"),
            input_refs=[econ_env.artifact_id, assessment_env.artifact_id],
            constraint_deps=[c.constraint_id for c in self.constraints.constraints],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        for d in self.artifacts:
            if d.artifact_type == ArtifactType.FEATURE_DECISION:
                self.graph.add_edge(d.artifact_id, env.artifact_id, EdgeRelation.DERIVED_FROM)
        return env

    def _review(self, spec_env: ArtifactEnvelope, decisions: list[ArtifactEnvelope]) -> ArtifactEnvelope:
        t = time.time()
        spec = ProductSpec(**spec_env.payload)
        review = ReviewerGate.run(self.artifacts, spec, review_id="review-spec-v1")
        spec.review_status = review.decision.value
        env = _envelope(
            "review-spec-v1", ArtifactType.REVIEW_RESULT, self.project_id,
            "gap2sku-reviewer", f"{self.project_id}-review-r001",
            review.model_dump(mode="json"), input_refs=[spec_env.artifact_id],
        )
        self.artifacts.append(env)
        self.graph.add_node(GraphNode(id=env.artifact_id, type=env.artifact_type.value))
        self.graph.add_edge(spec_env.artifact_id, env.artifact_id, EdgeRelation.REVIEWED_BY)
        self._emit(f"{self.project_id}-review-r001", "gap2sku-reviewer", "reviewer",
                   "review.run_rules", review.decision.value, env.artifact_id,
                   parent_ids=[spec_env.artifact_id], latency_ms=int((time.time()-t)*1000),
                   review_decision=review.decision.value)
        return env
