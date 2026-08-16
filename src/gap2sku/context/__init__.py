"""Context Routing — minimal sufficient context_bundle per role (spec 12)."""
from .router import ROLE_POLICY, ContextBundle, ContextRouter

__all__ = ["ContextRouter", "ContextBundle", "ROLE_POLICY"]
