from __future__ import annotations

from gap2sku.knowledge.retriever import SQLiteKnowledgeRetriever


def test_knowledge_never_authorizes_fact(tmp_path) -> None:
    retriever = SQLiteKnowledgeRetriever(tmp_path / "knowledge.db")
    retriever.ingest("材料标准", "https://example.invalid/standard", "儿童材料 检测 标准 背景知识")
    result = retriever.search("儿童")
    assert result and result[0].trust_level == "UNTRUSTED_RETRIEVAL"
    assert result[0].can_authorize_business_fact is False
