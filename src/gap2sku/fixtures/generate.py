"""Deterministic synthetic fixture generator for Laptop Stand demo (spec 16).

All data is SYNTHETIC. Files/README/payload all labeled `synthetic`.
Seedable for reproducibility.

Produces (spec 16.1):
  - 300-800 reviews
  - 8-12 competitor SKUs
  - 8-15 supplier offers
  - 1 fee table
  - 10-20 reviewer rules (in src/gap2sku/review/rules.py, not here)
  - 10 bad cases + 5 good cases (reviewer tests)
  - feature taxonomy
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

# --- Feature taxonomy (spec 16.2) ---
FEATURE_TAXONOMY = [
    {"feature_id": "wider_base", "label": "Wider base for stability", "cost_delta": "0.80",
     "pain_refs": ["pain-wobbling"]},
    {"feature_id": "silicone_pad", "label": "Anti-slip silicone pads", "cost_delta": "0.30",
     "pain_refs": ["pain-slipping"]},
    {"feature_id": "stiffened_hinge", "label": "Stiffened hinge mechanism", "cost_delta": "1.20",
     "pain_refs": ["pain-wobbling"]},
    {"feature_id": "double_axis", "label": "Double-axis rotation", "cost_delta": "1.50",
     "pain_refs": ["pain-angle"]},
    {"feature_id": "height_adjustable", "label": "Height adjustable", "cost_delta": "1.10",
     "pain_refs": ["pain-ergonomics"]},
    {"feature_id": "16_inch_compatibility", "label": "16-inch laptop compatibility", "cost_delta": "0.40",
     "pain_refs": ["pain-compatibility"]},
    {"feature_id": "carbon_fiber_structure", "label": "Carbon fiber structure", "cost_delta": "3.50",
     "pain_refs": []},  # weak market evidence -> REJECT
]

PAIN_POINTS = [
    {"pain_point_id": "pain-wobbling", "label": "Stand wobbles while typing",
     "severity": "high", "feature": "wider_base"},
    {"pain_point_id": "pain-slipping", "label": "Stand slides on desk / scratches laptop",
     "severity": "high", "feature": "silicone_pad"},
    {"pain_point_id": "pain-compatibility", "label": "Does not fit 16-inch laptop",
     "severity": "medium", "feature": "16_inch_compatibility"},
    {"pain_point_id": "pain-angle", "label": "Limited viewing angles",
     "severity": "medium", "feature": "double_axis"},
    {"pain_point_id": "pain-ergonomics", "label": "Not height adjustable",
     "severity": "low", "feature": "height_adjustable"},
]

REVIEW_TEMPLATES = [
    ("wobbling", "The stand wobbles a lot when I type, very annoying.", "high"),
    ("slipping", "It slides around on my glass desk and scratched my laptop bottom.", "high"),
    ("compatibility", "My 16 inch MacBook Pro barely fits, feels unsafe.", "medium"),
    ("angle", "Wish it had more angle options for different chairs.", "medium"),
    ("ergonomics", "Too low for standing use, not height adjustable.", "low"),
    ("positive", "Great value, sturdy enough for daily use.", None),
    ("positive", "Compact and folds flat, perfect for travel.", None),
    ("wobbling", "Unstable when I type fast on my external keyboard.", "high"),
    ("slipping", "Rubber feet are too small, it keeps moving.", "medium"),
    ("compatibility", "Fits my 13 inch fine but friend's 16 inch wobbles.", "low"),
]

COMPETITOR_SKUS = [
    {"sku": "COMP-001", "brand": "BrandA", "price": 29.99, "rating": 4.2, "reviews": 1200,
     "features": ["wider_base", "silicone_pad"], "size_max": 15.6},
    {"sku": "COMP-002", "brand": "BrandB", "price": 34.99, "rating": 4.5, "reviews": 2100,
     "features": ["wider_base", "silicone_pad", "height_adjustable"], "size_max": 17.0},
    {"sku": "COMP-003", "brand": "BrandC", "price": 24.99, "rating": 3.8, "reviews": 800,
     "features": ["silicone_pad"], "size_max": 15.6},
    {"sku": "COMP-004", "brand": "BrandD", "price": 39.99, "rating": 4.7, "reviews": 3400,
     "features": ["wider_base", "silicone_pad", "double_axis", "16_inch_compatibility"], "size_max": 17.3},
    {"sku": "COMP-005", "brand": "BrandE", "price": 27.99, "rating": 4.0, "reviews": 950,
     "features": ["wider_base", "stiffened_hinge"], "size_max": 15.6},
    {"sku": "COMP-006", "brand": "BrandF", "price": 44.99, "rating": 4.6, "reviews": 1800,
     "features": ["wider_base", "silicone_pad", "carbon_fiber_structure"], "size_max": 17.0},
    {"sku": "COMP-007", "brand": "BrandG", "price": 19.99, "rating": 3.5, "reviews": 500,
     "features": [], "size_max": 14.0},
    {"sku": "COMP-008", "brand": "BrandH", "price": 32.99, "rating": 4.3, "reviews": 1500,
     "features": ["silicone_pad", "height_adjustable", "16_inch_compatibility"], "size_max": 17.0},
    {"sku": "COMP-009", "brand": "BrandI", "price": 36.99, "rating": 4.4, "reviews": 1100,
     "features": ["wider_base", "double_axis"], "size_max": 16.0},
    {"sku": "COMP-010", "brand": "BrandJ", "price": 22.99, "rating": 3.9, "reviews": 700,
     "features": ["silicone_pad"], "size_max": 15.6},
]

# Supplier offers: Supplier B supports wider_base within $8 budget; carbon_fiber too expensive.
SUPPLIER_OFFERS = [
    {"supplier_id": "SUP-A", "offer_id": "OFFER-A1", "feature_id": "wider_base",
     "support_state": "confirmed", "existing_mold": True, "moq": 200,
     "base_unit_cost": "5.20", "cost_delta": "0.80", "lead_time_days": 15,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-B", "offer_id": "OFFER-B1", "feature_id": "wider_base",
     "support_state": "confirmed", "existing_mold": True, "moq": 100,
     "base_unit_cost": "5.50", "cost_delta": "0.80", "lead_time_days": 10,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-B", "offer_id": "OFFER-B2", "feature_id": "silicone_pad",
     "support_state": "confirmed", "existing_mold": True, "moq": 100,
     "base_unit_cost": "5.50", "cost_delta": "0.30", "lead_time_days": 10,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-B", "offer_id": "OFFER-B3", "feature_id": "16_inch_compatibility",
     "support_state": "confirmed", "existing_mold": True, "moq": 100,
     "base_unit_cost": "5.50", "cost_delta": "0.40", "lead_time_days": 10,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-C", "offer_id": "OFFER-C1", "feature_id": "stiffened_hinge",
     "support_state": "listed", "existing_mold": False, "moq": 500,
     "base_unit_cost": "4.80", "cost_delta": "1.20", "lead_time_days": 30,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-C", "offer_id": "OFFER-C2", "feature_id": "double_axis",
     "support_state": "listed", "existing_mold": False, "moq": 500,
     "base_unit_cost": "4.80", "cost_delta": "1.50", "lead_time_days": 30,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-D", "offer_id": "OFFER-D1", "feature_id": "height_adjustable",
     "support_state": "listed", "existing_mold": True, "moq": 300,
     "base_unit_cost": "6.10", "cost_delta": "1.10", "lead_time_days": 20,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-E", "offer_id": "OFFER-E1", "feature_id": "carbon_fiber_structure",
     "support_state": "listed", "existing_mold": False, "moq": 1000,
     "base_unit_cost": "9.50", "cost_delta": "3.50", "lead_time_days": 45,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-F", "offer_id": "OFFER-F1", "feature_id": "wider_base",
     "support_state": "unsupported", "existing_mold": False, "moq": 2000,
     "base_unit_cost": "4.00", "cost_delta": "0.00", "lead_time_days": 60,
     "verification_level": "platform_visible"},
    {"supplier_id": "SUP-G", "offer_id": "OFFER-G1", "feature_id": "silicone_pad",
     "support_state": "conflict", "existing_mold": True, "moq": 100,
     "base_unit_cost": "7.20", "cost_delta": "0.30", "lead_time_days": 10,
     "verification_level": "platform_visible"},
]

FEE_TABLE_V1 = {
    "assumption_version": "1.0.0",
    "currency": "USD",
    "platform_fee_rate": "0.15",
    "platform_fixed_fee": "0.00",
    "fulfillment_fee": "3.50",
    "marketing_rate": "0.08",
    "loss_allowance_rate": "0.03",
    "packaging_cost": "0.80",
    "shipping_cost": "2.20",
    "rounding": {"decimals": 2, "mode": "ROUND_HALF_UP"},
}


def _hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_fixture(out_dir: Path, seed: int = 42) -> dict:
    """Generate all synthetic fixture files deterministically."""
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Reviews ---
    reviews = []
    for i in range(1, 501):  # 500 reviews (spec: 300-800)
        template_key, text, severity = rng.choice(REVIEW_TEMPLATES)
        review = {
            "review_id": f"review_{i:04d}",
            "is_synthetic": True,
            "source_type": "synthetic_fixture",
            "rights_status": "synthetic",
            "snapshot_id": "reviews-laptop-stand-us-synthetic-v1",
            "observed_at": "2026-07-15",
            "language": "en",
            "rating": rng.choice([2, 3, 3, 4, 4, 4, 5]) if severity is None else rng.choice([1, 2, 2, 3]),
            "verified_purchase": True,
            "product_ref": rng.choice([c["sku"] for c in COMPETITOR_SKUS]),
            "template_key": template_key,
            "text": text,
            "severity": severity,
            "content_hash": _hash(f"review_{i}_{text}"),
            "locator": f"reviews.synthetic.jsonl#{i}",
        }
        reviews.append(review)

    # --- Manifest ---
    manifest = {
        "fixture_version": "1.0.0",
        "generated_at_seed": seed,
        "category": "laptop_stand",
        "target_market": "US Amazon",
        "is_synthetic": True,
        "counts": {
            "reviews": len(reviews),
            "competitors": len(COMPETITOR_SKUS),
            "supplier_offers": len(SUPPLIER_OFFERS),
            "pain_points": len(PAIN_POINTS),
            "features": len(FEATURE_TAXONOMY),
        },
        "files": [
            "manifest.json", "reviews.synthetic.jsonl", "competitors.synthetic.json",
            "supplier_offers.synthetic.json", "fees.v1.json", "feature_taxonomy.v1.json",
            "pain_points.synthetic.json", "bad_cases/", "good_cases/",
        ],
        "rights_notice": "All data is SYNTHETIC. Not real Amazon/Alibaba data. Redistributable.",
    }

    # --- Write files ---
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    with (out_dir / "reviews.synthetic.jsonl").open("w") as f:
        for r in reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out_dir / "competitors.synthetic.json").write_text(
        json.dumps({"is_synthetic": True, "skus": COMPETITOR_SKUS}, indent=2, ensure_ascii=False))
    (out_dir / "supplier_offers.synthetic.json").write_text(
        json.dumps({"is_synthetic": True, "offers": SUPPLIER_OFFERS}, indent=2, ensure_ascii=False))
    (out_dir / "fees.v1.json").write_text(json.dumps(FEE_TABLE_V1, indent=2, ensure_ascii=False))
    (out_dir / "feature_taxonomy.v1.json").write_text(
        json.dumps({"is_synthetic": True, "features": FEATURE_TAXONOMY}, indent=2, ensure_ascii=False))
    (out_dir / "pain_points.synthetic.json").write_text(
        json.dumps({"is_synthetic": True, "pain_points": PAIN_POINTS}, indent=2, ensure_ascii=False))

    # --- Reviewer bad/good cases ---
    bad_dir = out_dir / "reviewer_bad_cases"
    good_dir = out_dir / "reviewer_good_cases"
    bad_dir.mkdir(exist_ok=True)
    good_dir.mkdir(exist_ok=True)

    # 10 bad cases (each violates one rule)
    bad_cases = [
        {"case": "bad-001", "rule": "R003", "desc": "Hard constraint violated: factory_cost 9.00 > 8.00"},
        {"case": "bad-002", "rule": "R004", "desc": "ACCEPT feature without supply ref"},
        {"case": "bad-003", "rule": "R005", "desc": "Evidence without snapshot_id"},
        {"case": "bad-004", "rule": "R006", "desc": "platform_visible labeled human_confirmed"},
        {"case": "bad-005", "rule": "R007", "desc": "Economics without calculation_trace"},
        {"case": "bad-006", "rule": "R009", "desc": "REJECT feature without rationale"},
        {"case": "bad-007", "rule": "R010", "desc": "Reviewer spec_hash mismatch"},
        {"case": "bad-008", "rule": "R011", "desc": "Synthetic evidence not labeled"},
        {"case": "bad-009", "rule": "R012", "desc": "Spec committed by market agent, not leader"},
        {"case": "bad-010", "rule": "R002", "desc": "Spec references STALE artifact"},
    ]
    for bc in bad_cases:
        (bad_dir / f"{bc['case']}.json").write_text(json.dumps(bc, indent=2))

    # 5 good cases
    good_cases = [
        {"case": "good-001", "desc": "All constraints satisfied, full evidence chain"},
        {"case": "good-002", "desc": "Two ACCEPT features with Market+Supply+Economics"},
        {"case": "good-003", "desc": "carbon_fiber correctly REJECTED with rationale"},
        {"case": "good-004", "desc": "Economics recomputable, trace complete"},
        {"case": "good-005", "desc": "Spec hash matches reviewer hash"},
    ]
    for gc in good_cases:
        (good_dir / f"{gc['case']}.json").write_text(json.dumps(gc, indent=2))

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic laptop_stand fixture")
    parser.add_argument("--out", default="data/fixtures/laptop_stand")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    manifest = generate_fixture(Path(args.out), args.seed)
    print(f"[fixture] Generated synthetic laptop_stand fixture at {args.out}")
    print(f"[fixture] counts: {manifest['counts']}")
    print("[fixture] All data is SYNTHETIC and labeled as such.")


if __name__ == "__main__":
    main()
