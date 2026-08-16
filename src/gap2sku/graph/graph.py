"""Artifact Graph — versioned JSON adjacency list (spec 11).

P0: no Neo4j. Uses in-memory adjacency + SQLite edge table (via ArtifactStore).
Allowed relations (spec 11.1).
"""
from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EdgeRelation(str, Enum):
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MOTIVATES = "motivates"
    VALIDATED_BY = "validated_by"
    CONSTRAINS = "constrains"
    SELECTED_BY = "selected_by"
    REJECTED_BY = "rejected_by"
    SUPERSEDES = "supersedes"
    REVIEWED_BY = "reviewed_by"


class GraphNode(BaseModel):
    id: str
    type: str
    version: int = 1


class GraphEdge(BaseModel):
    src: str
    dst: str
    relation: EdgeRelation


class ArtifactGraph(BaseModel):
    """In-memory artifact dependency graph."""

    graph_version: int = 1
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    # adjacency: node_id -> list of (dst, relation)
    out_edges: dict[str, list[GraphEdge]] = Field(default_factory=dict)
    in_edges: dict[str, list[GraphEdge]] = Field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        current = self.nodes.get(node.id)
        if current is not None and current != node:
            raise ValueError(f"node {node.id} already registered with another version/type")
        self.nodes[node.id] = node
        self.out_edges.setdefault(node.id, [])
        self.in_edges.setdefault(node.id, [])

    def add_edge(self, src: str, dst: str, relation: EdgeRelation) -> None:
        missing = [node_id for node_id in (src, dst) if node_id not in self.nodes]
        if missing:
            raise KeyError(f"edge references missing graph nodes: {missing}")
        edge = GraphEdge(src=src, dst=dst, relation=relation)
        self.out_edges.setdefault(src, []).append(edge)
        self.in_edges.setdefault(dst, []).append(edge)

    def downstream(self, artifact_id: str) -> list[str]:
        """BFS all downstream nodes (spec 19.1 step 4)."""
        visited: set[str] = set()
        queue = deque([artifact_id])
        while queue:
            cur = queue.popleft()
            for edge in self.out_edges.get(cur, []):
                if edge.dst not in visited:
                    visited.add(edge.dst)
                    queue.append(edge.dst)
        return sorted(visited)

    def upstream(self, artifact_id: str) -> list[str]:
        visited: set[str] = set()
        queue = deque([artifact_id])
        while queue:
            cur = queue.popleft()
            for edge in self.in_edges.get(cur, []):
                if edge.src not in visited:
                    visited.add(edge.src)
                    queue.append(edge.src)
        return sorted(visited)

    def subgraph(self, artifact_ids: list[str], depth: int = 2) -> dict[str, Any]:
        """Minimal context subgraph for an Agent (spec 11.2)."""
        include: set[str] = set(artifact_ids)
        frontier = list(artifact_ids)
        for _ in range(depth):
            nxt: list[str] = []
            for n in frontier:
                for edge in self.out_edges.get(n, []):
                    if edge.dst not in include:
                        include.add(edge.dst)
                        nxt.append(edge.dst)
                for edge in self.in_edges.get(n, []):
                    if edge.src not in include:
                        include.add(edge.src)
                        nxt.append(edge.src)
            frontier = nxt
        nodes = [self.nodes[i].model_dump() for i in include if i in self.nodes]
        edges = [
            {"from": e.src, "to": e.dst, "relation": e.relation.value}
            for n in include for e in self.out_edges.get(n, [])
            if e.dst in include
        ]
        return {"nodes": nodes, "edges": edges}

    def why(self, feature_id: str) -> dict[str, Any]:
        """Trace a feature back to evidence/sources (spec 11.2)."""
        return {
            "feature": feature_id,
            "upstream": self.upstream(feature_id),
            "subgraph": self.subgraph([feature_id], depth=3),
        }

    def trace_to_sources(self, decision_id: str) -> list[str]:
        """Backtrace to Evidence/Snapshot nodes (spec 11.2)."""
        chain = self.upstream(decision_id)
        return [n for n in chain if self.nodes.get(n) and self.nodes[n].type in ("Evidence", "ReviewSnapshot")]

    def stale_refs(self, spec_id: str, stale_ids: set[str]) -> list[str]:
        """Check if spec references STALE/SUPERSEDED artifacts (spec 11.2)."""
        downstream = set(self.downstream(spec_id))
        return sorted(downstream & stale_ids)
