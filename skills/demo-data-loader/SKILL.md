---
name: demo-data-loader
description: Load the fully synthetic laptop-stand regression fixture with version and hash checks.
assign_when: Use only for the explicit synthetic regression or offline demo path.
version: 0.1.0
owner: gap2sku
agents: [gap2sku-product-architect]
license: Apache-2.0
---

# Demo Data Loader

## Purpose

Load synthetic Laptop Stand fixture into versioned snapshots for the demo.
All data is SYNTHETIC and labeled as such.

## Inputs

- Fixture manifest path.

## Procedure

1. Read manifest.json; verify fixture_version.
2. Load reviews.synthetic.jsonl, competitors.synthetic.json, supplier_offers.synthetic.json, fees.v1.json.
3. Verify content_hash of each file.
4. Wrap as versioned snapshots with snapshot_id and is_synthetic=true.

## Output

VersionedSnapshot@1.0.0 list.

## Failure Path

- Hash mismatch or schema error -> BLOCK.
- Missing file -> BLOCK.
