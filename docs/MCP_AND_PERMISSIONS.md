# MCP and Permissions (spec 13, 20)

## Endpoints

One process, role-isolated:

| Endpoint | Role | Tools |
|---|---|---|
| `/market/mcp` | Market | fixtures.list_snapshots, evidence.search_reviews, evidence.get_competitor_records, state.get_constraints, artifact.validate_local |
| `/supply/mcp` | Supply | fixtures.list_snapshots, evidence.get_supplier_records, state.get_constraints, artifact.get_feature_hypotheses, artifact.validate_local |
| `/economics/mcp` | Economics | state.get_constraints, economics.calculate, economics.verify, artifact.validate_local |
| `/review/mcp` | Reviewer (read-only) | review.run_rules, graph.get_subgraph |
| `/leader/mcp` | Leader | state.create_run, state.get_project, state.get_constraints, context.build_bundle, graph.get_subgraph |

## Write Contract (spec 13.3)

All writes require:
```
project_id, task_id, producer_agent, artifact_id, artifact_version,
schema_version, expected_project_revision, idempotency_key, content_hash
```

Server validates:
- Project scope
- Task/Agent identity + allowed role
- Schema
- Expected revision (optimistic lock)
- Artifact not already existing
- Upstream refs valid
- No Worker overwrite of history
- No Reviewer Spec write
- No LLM override of deterministic BLOCK

## Permission Matrix

See `configs/permissions.yaml`.
