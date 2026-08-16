from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeCitation(BaseModel):
    """Untrusted retrieved knowledge; never interchangeable with EvidenceRecord."""

    model_config = ConfigDict(extra="forbid")
    citation_id: str
    title: str
    source_uri: str
    excerpt: str
    content_hash: str
    retrieved_at: str
    trust_level: str = "UNTRUSTED_RETRIEVAL"
    can_authorize_business_fact: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class SQLiteKnowledgeRetriever:
    def __init__(self, db_path: str | Path = "shared/knowledge.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(citation_id UNINDEXED, title, source_uri UNINDEXED, body, content_hash UNINDEXED)"
        )

    def ingest(self, title: str, source_uri: str, body: str) -> str:
        content_hash = hashlib.sha256(body.encode()).hexdigest()
        citation_id = f"knowledge-{content_hash[:16]}"
        self.conn.execute("DELETE FROM knowledge_fts WHERE citation_id=?", (citation_id,))
        self.conn.execute(
            "INSERT INTO knowledge_fts VALUES (?,?,?,?,?)",
            (citation_id, title, source_uri, body, f"sha256:{content_hash}"),
        )
        self.conn.commit()
        return citation_id

    def search(self, query: str, limit: int = 5) -> list[KnowledgeCitation]:
        query = query.strip()
        if not query:
            return []
        rows = self.conn.execute(
            "SELECT citation_id,title,source_uri,body,content_hash FROM knowledge_fts WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, max(1, min(limit, 20))),
        ).fetchall()
        # Default FTS5 tokenization does not reliably segment Chinese. Keep a
        # deterministic substring fallback so the offline retriever remains
        # useful without adding an external tokenizer/vector service.
        if not rows:
            rows = self.conn.execute(
                "SELECT citation_id,title,source_uri,body,content_hash FROM knowledge_fts WHERE title LIKE ? OR body LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", max(1, min(limit, 20))),
            ).fetchall()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return [KnowledgeCitation(
            citation_id=row["citation_id"], title=row["title"], source_uri=row["source_uri"],
            excerpt=row["body"][:500], content_hash=row["content_hash"], retrieved_at=now,
        ) for row in rows]

    def close(self) -> None:
        self.conn.close()
