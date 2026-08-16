"""Artifact Graph — adjacency list + impact BFS (spec 11, 19)."""
from .graph import ArtifactGraph, EdgeRelation
from .impact import ROLE_BY_TYPE, ImpactAnalyzer

__all__ = ["ArtifactGraph", "EdgeRelation", "ImpactAnalyzer", "ROLE_BY_TYPE"]
