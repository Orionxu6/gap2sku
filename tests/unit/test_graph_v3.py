from __future__ import annotations

import pytest

from gap2sku.graph.graph import ArtifactGraph, EdgeRelation, GraphNode


def test_graph_ref_integrity_and_bfs() -> None:
    graph = ArtifactGraph()
    graph.add_node(GraphNode(id="a", type="Evidence"))
    with pytest.raises(KeyError):
        graph.add_edge("a", "missing", EdgeRelation.DERIVED_FROM)
    graph.add_node(GraphNode(id="b", type="PainPointSet"))
    graph.add_node(GraphNode(id="c", type="ProductSpec"))
    graph.add_edge("a", "b", EdgeRelation.DERIVED_FROM)
    graph.add_edge("b", "c", EdgeRelation.DERIVED_FROM)
    assert graph.downstream("a") == ["b", "c"]
    assert graph.upstream("c") == ["a", "b"]


def test_node_version_collision() -> None:
    graph = ArtifactGraph()
    graph.add_node(GraphNode(id="a", type="Evidence", version=1))
    with pytest.raises(ValueError):
        graph.add_node(GraphNode(id="a", type="Evidence", version=2))
