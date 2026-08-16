---
name: evidence-conflict-decision
description: Convert traceable product evidence into governed ConflictCard, OptionCard, ReviewReport, and DecisionBrief artifacts. Use for cross-functional product decisions requiring GO, REVISE, or NO-GO with deterministic policy gates, missing-evidence handling, human approval binding, and separation of retrieved knowledge from business evidence.
assign_when: Use when cross-role claims disagree or a GO, REVISE, or NO-GO recommendation must be justified.
---

# Evidence Conflict Decision

1. Record each observed fact as an `EvidenceRecord` with source hash, locator, time, rights, grade, and data mode.
2. Keep sampling limitations visible. Never infer population rates from targeted samples.
3. Store retrieved background as `KnowledgeCitation`; treat it as untrusted and never silently promote it to a supplier, cost, compliance, or safety fact.
4. Represent disagreement as a `ConflictCard` with both claims, evidence and policy references, unresolved gaps, severity, and status.
5. Generate at least two materially distinct options when resolution is possible. Record trade-offs and evidence needed for each option; do not use majority voting.
6. Run deterministic policy and Reviewer checks before explanatory model output.
7. Return `REVISE` when a GO prerequisite is missing and create owned remediation tasks. Return `NO-GO` only when a hard rule fails with no feasible remediation.
8. Bind human approval to exact `spec_hash`, `policy_version`, approver, reason, and decision.
9. Label every synthetic input and output `SYNTHETIC`; never present it as a real commercial conclusion.

Read [artifact-contracts.md](references/artifact-contracts.md) when producing or validating concrete JSON artifacts.
