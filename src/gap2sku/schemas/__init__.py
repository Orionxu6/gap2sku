"""Gap2SKU Domain Schemas (spec section 10).

All artifacts share a common ArtifactEnvelope. Core domain types:
  Constraint, EvidenceRecord, PainPoint, FeatureHypothesis,
  SupplierCapability, EconomicsArtifact, FeatureDecision,
  ProductSpec, ReviewResult, ChangeEvent, ImpactPlan.

Design principles:
  - Money is Decimal string in JSON, never binary float.
  - Every artifact is versioned, immutable, hash-linked.
  - ACCEPT requires Market + Supply + Economics refs (R004).
"""
from __future__ import annotations

from .change import ChangeEvent
from .constraint import Constraint, ConstraintSet
from .decision import DecisionStatus, FeatureDecision
from .economics import ConstraintCheck, EconomicsArtifact, SensitivityCase
from .envelope import ArtifactEnvelope, ArtifactStatus, ArtifactType
from .evidence import EvidenceRecord, RightsStatus, SourceType
from .feature import FeatureHypothesis, FeatureStatus
from .impact import ImpactAction, ImpactPlan
from .pain_point import PainPoint, PainPointSet
from .product import (
    CategoryProfile,
    ClaimRegister,
    ComplianceAssessment,
    CompliancePolicyPack,
    DecisionToSamplePack,
    IntakeMode,
    OpportunityBrief,
    ProductConceptSet,
    ProductIntake,
    ProductStoryBundle,
    ProfileStatus,
    PublicSupplierSignal,
    PublicSupplierSignalSet,
    RenderManifest,
    RenderPromptRecord,
    ResearchPlan,
    RFQPack,
    SampleSpec,
    SupplierQuoteSet,
    TestMatrix,
)
from .review import ReviewDecision, ReviewError, ReviewResult
from .spec import ProductSpec, SpecApprovalStatus
from .supplier import SupplierCapability, SupportState, VerificationLevel

__all__ = [
    "ArtifactEnvelope", "ArtifactStatus", "ArtifactType",
    "Constraint", "ConstraintSet",
    "EvidenceRecord", "SourceType", "RightsStatus",
    "PainPoint", "PainPointSet",
    "FeatureHypothesis", "FeatureStatus",
    "SupplierCapability", "SupportState", "VerificationLevel",
    "EconomicsArtifact", "SensitivityCase", "ConstraintCheck",
    "FeatureDecision", "DecisionStatus",
    "ProductSpec", "SpecApprovalStatus",
    "ReviewResult", "ReviewDecision", "ReviewError",
    "ChangeEvent",
    "ImpactPlan", "ImpactAction",
    "ProductIntake", "IntakeMode", "CategoryProfile", "ProfileStatus",
    "CompliancePolicyPack", "ResearchPlan", "OpportunityBrief",
    "ProductConceptSet", "SampleSpec", "RenderPromptRecord", "RenderManifest",
    "RFQPack", "SupplierQuoteSet", "PublicSupplierSignal", "PublicSupplierSignalSet",
    "ComplianceAssessment", "TestMatrix",
    "ClaimRegister", "ProductStoryBundle", "DecisionToSamplePack",
]
