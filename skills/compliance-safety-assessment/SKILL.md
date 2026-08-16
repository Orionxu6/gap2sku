---
name: compliance-safety-assessment
description: Classify a product and build versioned material, test, label, packaging, and claim gates for its target market.
assign_when: Use whenever category, intended user, target country, materials, claims, or locked SampleSpec changes.
version: 0.2.0
owner: gap2sku
agents: [gap2sku-compliance]
license: Apache-2.0
---

# Compliance and Safety Assessment

## Inputs

- ProductIntake, CategoryProfile, target countries, intended user, use context, and claims.
- Locked SampleSpec, material declarations, supplier certificates, labels, and test reports.
- Versioned CompliancePolicyPack with official source citations.

## Procedure

1. Classify intended use, foreseeable use, user population/age, contact type, energy/mechanical structure, claims, jurisdiction, and risk level before choosing a policy pack.
2. Separate official requirements, supplier assertions, marketplace signals, generated content, retrieved knowledge, and missing product evidence.
3. Build six explicit matrices: material/contact, mechanical/electrical risk, TestMatrix, label, packaging/traceability, and ClaimRegister.
4. Mark each row `PASS`, `MISSING`, `ESTIMATED`, `NEEDS_EVIDENCE`, `NOT_APPLICABLE`, or `FAIL` with official source URL, authority, version/date, captured-at, applicability condition, product evidence refs, owner, and remediation.
5. Treat children, food contact, electrical, medical, protective, chemical, or load-bearing products as enhanced-review categories.
6. Never infer compliance from a marketplace listing, competitor review, generated image, or expired certificate.
7. Emit `COMPLIANCE_FLAG` for hard failures and `NEEDS_EVIDENCE` for remediable gaps.
8. Re-run classification whenever target market, user age, intended use, material, structure, power source, or claim changes; old PASS cannot be reused across a different `spec_hash` or policy version.

## Output

- `ComplianceAssessment`, `TestMatrix`, and `ClaimRegister`.

## Hard Gate

Unconfirmed category classification, missing applicable official policy source, critical material/test failure, or unsupported safety claim prevents GO.
