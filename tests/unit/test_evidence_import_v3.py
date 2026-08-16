from __future__ import annotations

from collections import Counter

from gap2sku.evidence.reviews import ReviewWorkbookImporter


def test_import_counts_and_provenance() -> None:
    result = ReviewWorkbookImporter("private/raw_reviews").import_all()
    assert len(result.records) == 389
    assert Counter(record.metadata["brand"] for record in result.records) == {
        "尼拉": 69, "睡洞": 103, "祺加": 122, "西诺思": 95,
    }
    assert result.report["column_migrations"] == 65
    assert result.report["duplicate_count"] == 7
    assert result.report["source_url_count"] == 122
    assert all(record.file_hash and record.sheet == "评论数据" and record.row_number for record in result.records)


def test_low_traceability_is_downgraded() -> None:
    records = ReviewWorkbookImporter("private/raw_reviews").import_all().records
    nila = [r for r in records if r.metadata["brand"] == "尼拉"]
    qijia = [r for r in records if r.metadata["brand"] == "祺加"]
    assert all(r.evidence_grade == "C" for r in nila)
    assert all(r.evidence_grade == "A" for r in qijia)
    assert all(not r.is_synthetic for r in records)
