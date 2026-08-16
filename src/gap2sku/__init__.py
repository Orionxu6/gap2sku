"""Gap2SKU Domain Core — evidence-backed product definition.

Subpackages:
  schemas:      Pydantic models for all artifacts (spec section 10)
  economics:    Deterministic Decimal unit-economics (spec section 17)
  artifacts:    Artifact store, envelope, validation (spec section 9-10)
  graph:        Artifact Graph adjacency + impact BFS (spec section 11, 19)
  context:      Context Routing policy (spec section 12)
  review:       Deterministic Reviewer Gate R001-R012 (spec section 18)
  replanning:   Selective Re-planning (spec section 19)
  fixtures:     Synthetic laptop_stand fixture generator (spec section 16)
  observability: JSONL trace + metrics (spec section 22)
  mcp_server:   Multi-role MCP endpoints (spec section 13)
  cli:          Command entrypoints (make targets, spec section 25)
"""

__version__ = "0.1.0"
