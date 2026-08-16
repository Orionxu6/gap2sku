# Skill Registry (spec 14)

## P0 Domain Skills

| Skill | Caller | Input | Output | Failure |
|---|---|---|---|---|
| demo-data-loader | Leader/test | Fixture manifest | Versioned snapshots | hash/schema error -> BLOCK |
| market-evidence-mining | Market | Review/competitor snapshot + constraints | EvidenceSet + PainPointSet | data insufficient -> BLOCKED |
| supplier-capability-assessment | Supply | Feature hypotheses + supplier snapshot + constraints | CapabilitySet + Assessment | conflict -> CONFLICT |
| unit-economics-evaluation | Economics | Candidate + fee table + constraints | EconomicsArtifact | missing input -> BLOCKED |
| product-spec-synthesis | Product Architect | Valid Artifacts + constraints | ProductSpec Draft | hard constraint -> BLOCK |
| evidence-review-gate | Reviewer | Spec + subgraph + rule results | PASS/REVISE/BLOCK | missing Rule ID/Spec Hash -> invalid |
| impact-aware-replanning | Product Architect | ChangeEvent + Artifact Graph | ImpactPlan + revision tasks | graph inconsistent -> BLOCK + human |

## Registry File

`skills/registry.yaml` lists name, version, owner, agents, input/output schemas,
license, tests.

## Not Duplicated from AgentTeams (spec 14.4)

Domain Skills do NOT re-implement: Team org, Project lifecycle, Task delegation,
Task acknowledge/submit/check/accept, Matrix communication, MinIO file sync.
These use AgentTeams/TeamHarness built-in Skills.
