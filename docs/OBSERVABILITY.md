# Observability (spec 22)

## P0 Minimum

Local JSONL trace at `evidence/domain-trace.jsonl`. Each line is a TraceEvent:

```
run_id, project_id, task_id, agent_name, agent_role, tool_name,
tool_call_id, artifact_id, artifact_version, parent_artifact_ids,
latency_ms, token_usage, result_status, review_decision,
replan_reason, timestamp
```

## Three Evidence Types (spec 22.2)

1. **Element Team Room**: real delegation, completion, revision, human intervention.
2. **Project/Task/Artifact State**: execution DAG, Artifact Graph, version, acceptance.
3. **Trace**: Agent -> Skill -> MCP Tool -> Artifact chain.

## AgentLoop (P1, optional)

- P0: local JSONL + structured logs + Matrix history.
- P1: OpenTelemetry/AgentLoop (if cloud available and verified).
- Fallback: AgentLoop failure continues writing local trace.
- AgentLoop never used for: Domain State, hard constraints, Artifact Graph, blocking P0.
