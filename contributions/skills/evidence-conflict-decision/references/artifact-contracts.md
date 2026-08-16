# Minimal artifact contracts

## EvidenceRecord

Require `evidence_id`, `source_type`, `content_hash`, `file_hash` when uploaded, `workbook/sheet/row_number` for spreadsheet evidence, `evidence_grade`, `data_mode`, and transformation/duplicate metadata.

## ConflictCard

Require `conflict_id`, `conflict_type`, two or more `claims`, `evidence_refs`, `policy_refs`, `unresolved_gaps`, `severity`, and `status`.

## OptionCard

Require `option_id`, `conflict_id`, `tradeoffs`, `required_evidence`, `policy_checks`, and `recommendation`.

## ReviewReport

Require task/revision, exact Product Spec reference and hash, policy version, atomic findings with rule IDs and owners, unverified checks, and review time.

## DecisionBrief

Require `GO | REVISE | NO-GO`, evidence and risk summaries, Conflict/Option refs, pending confirmations, remediation tasks, policy version, data mode, and approval requirement.
