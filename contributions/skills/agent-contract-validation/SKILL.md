---
name: agent-contract-validation
description: Validate and compile strict gap2sku.agent/v1 multi-agent packages. Use when checking Agent ZIP references, JSON Schemas, model environment placeholders, default-deny Skill/tool permissions, budgets, event routes, or generating an auditable identity and capability manifest before AgentTeams deployment.
assign_when: Use before any Agent package is uploaded, updated, or accepted into an AgentTeams runtime.
---

# Agent Contract Validation

Treat `agent.yaml` as an enforced runtime contract, not prompt documentation.

1. Preserve and hash the input ZIP before extraction.
2. Require `agent.yaml`, `SOUL.md`, `AGENTS.md`, `rubrics.md`, `MEMORY.md`, and `memory.scope`.
3. Resolve every relative reference inside the package; fail startup when any file or Schema is absent.
4. Require `runtime_adapter.contract=gap2sku.agent/v1`, `required=true`, `on_missing=fail_startup`, and `reject_unknown_fields=true`.
5. Expand model placeholders only from process environment. Never print or package secret values.
6. Require default-deny behavior for unknown Skills and explicit mapping from contract tool names to runtime capabilities.
7. Ensure every emitted event has a subscriber. Route governance events to an audit/manager sink.
8. Produce a report containing package hashes, identities, allowed Skills/tools, capability mapping, event routes, and validation errors.
9. Do not start AgentTeams or claim runtime readiness when validation fails.

Use `scripts/validate_contracts.py` for the Gap2SKU v3 repository. A zero exit code and `valid: true` are required before packaging.
