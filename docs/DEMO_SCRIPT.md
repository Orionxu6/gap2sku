# Demo Script (spec 23.5)

## 3-5 minute demo flow

```
00:00-00:30  Input target & hard constraints
             -> make demo-core  (or send task to Team room)

00:30-01:30  Show TeamHarness DAG, Market/Supply parallel tasks
             -> evidence/domain-trace.jsonl

01:30-02:15  Open one Feature's Artifact Graph and "Why This Feature"
             -> graph.subgraph(feature_id)

02:15-02:45  Show Reviewer REJECT/BLOCK on carbon_fiber
             -> review result R004/R009

02:45-03:15  Publish Spec V1
             -> evidence/demo-core-run.json

03:15-03:45  $8.00 -> $6.50
             -> make demo-replan

03:45-04:30  Show ImpactPlan, skipped Market, selective re-run
             -> evidence/demo-replan-plan.json

04:30-05:00  Show Spec Diff, Trace, test/evidence
             -> make verify-evidence
```

## Expected Signals

### V1 (db_pool_exhausted equivalent: factory_cost_max=8.00)

| Check | Expected |
|---|---|
| Root cause | Supplier B option within $8.00, MOQ 100, existing mold |
| Evidence | wobbling + slipping + 16-inch pain points with review refs |
| Spec | >= 2 ACCEPT features (wider_base, silicone_pad, 16_inch_compat) |
| Reviewer | PASS or REVISE (no BLOCK) |
| carbon_fiber | REJECT (weak evidence, cost > $8) |

### V2 (factory_cost_max=6.50)

| Check | Expected |
|---|---|
| ChangeEvent | recorded |
| ImpactPlan | preserved: evidence, pain, feature, raw supplier; stale: assessment, econ, decisions, spec, review |
| Market calls | 0 |
| New tasks | r002 IDs |
| Spec V2 hash | different from V1 |
| Unaffected artifact hash | unchanged |
