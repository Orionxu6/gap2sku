# Architecture

## Overview (spec section 3)

```
Human Admin / Judge
  -> AgentTeams Global Manager (platform routing, lifecycle)
      -> Product Architect (Team Leader)
          -> Market Worker
          -> Supply Worker
          -> Economics Worker
          -> Reviewer Worker
```

## Three State Layers (spec 3.2)

| Layer | Authority | Meaning |
|---|---|---|
| Collaboration execution state | TeamHarness `shared/projects` / `shared/tasks` | Who, dependency, submit, accept |
| Gap2SKU Domain State | State MCP + SQLite + MinIO Artifacts | Constraints, evidence, cost, decisions, Spec, review, version |
| Chat & Trace | Matrix + JSONL/OTel | Observable, auditable |

## Two Graphs (spec 3.3)

- **TeamHarness Project DAG** (execution): who executes, when ready, accepted, next wave.
- **Gap2SKU Artifact Graph** (evidence/decision): why feature kept, what evidence, what invalidated.
- Linked via `producer_task_id`, `artifact_refs`, `input_refs`. Never share schema.

## Module Map

```
src/gap2sku/
  schemas/       Pydantic models (spec 10)
  economics/     Deterministic Decimal calculator (spec 17)
  artifacts/     ArtifactStore (SQLite WAL, single-writer, optimistic revision)
  graph/         ArtifactGraph + ImpactAnalyzer (BFS, spec 11/19)
  context/       ContextRouter (minimal context per role, spec 12)
  review/        ReviewerGate R001-R012 (deterministic, spec 18)
  replanning/    ReplanningCoordinator (spec 19)
  fixtures/      Synthetic laptop_stand generator (spec 16)
  observability/ TraceRecorder (JSONL, spec 22)
  mcp_server.py  Multi-role MCP endpoints (spec 13)
  pipeline.py    DomainCorePipeline (offline deterministic, spec 7/23)
  cli/           make target entrypoints (spec 25)
```

## Extension Points (MVP upgrade path)

1. **Storage**: `ArtifactRepository` ABC -> swap SQLite for PostgreSQL.
2. **Data sources**: `EvidenceSource` interface -> add SafeFetch/BraveSearch/SP-API (P1/P2).
3. **MCP transport**: current HTTP JSON -> full MCP SDK Streamable HTTP (P1).
4. **Reviewer**: `RULE_REGISTRY` dict -> add R013+ or plug in LLM explanation layer.
5. **Replanning**: `CONSTRAINT_PATH_IMPACT` map -> add new constraint paths.
6. **Agents**: `agents/*/Agent.md` -> publish to Nacos AI Registry (future).
7. **Skills**: `skills/registry.yaml` -> dynamic load by version/tag.
