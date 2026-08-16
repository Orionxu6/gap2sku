# Third-Party Notices for Gap2SKU AgentTeams Demo

This project uses third-party packages and services. Each entry lists name,
version constraint, license, source, and how it is used.

## Runtime Dependencies

| Package | Version | License | Source | Usage |
|---|---|---|---|---|
| AgentTeams | v1.2.2 (pinned) | Apache-2.0 | https://github.com/agentscope-ai/AgentTeams | Multi-agent orchestration runtime (Team/Worker/TeamHarness/Matrix/MinIO/Higress) |
| Motion JavaScript | 12.42.2 (pinned local asset) | MIT | https://github.com/motiondivision/motion | Stagger, reveal and micro-interactions without a React build chain |
| Agent Skills Spec | — | Code Apache-2.0 / Docs CC-BY-4.0 | https://github.com/agentskills/agentskills | Skill open format (`SKILL.md`) |
| MCP Python SDK | >=1.28,<2 | MIT | https://github.com/modelcontextprotocol/python-sdk | Self-hosted `gap2sku-tools` MCP server |
| Pydantic | >=2.5,<3 | MIT | https://github.com/pydantic/pydantic | Domain Schema and JSON validation |
| httpx | >=0.27,<1 | BSD-3-Clause | https://github.com/encode/httpx | HTTP client for fixture/MCP/AgentTeams |
| Starlette | >=0.31,<1 | BSD-3-Clause | https://github.com/encode/starlette | ASGI framework for MCP HTTP transport |
| Uvicorn | >=0.23,<1 | BSD-3-Clause | https://github.com/encode/uvicorn | ASGI server |
| SQLite | bundled | Public Domain | https://www.sqlite.org/ | Domain State metadata store |

## Optional / P1 Dependencies

| Package | Version | License | Source | Usage | Default |
|---|---|---|---|---|---|
| Microsoft Playwright MCP | — | Apache-2.0 | https://github.com/microsoft/playwright-mcp | Optional page verification, screenshot/trace | disabled |
| Brave Search MCP | — | MIT | https://github.com/brave/brave-search-mcp-server | Optional real-time web search | disabled (needs API key) |
| Promptfoo | — | MIT | https://github.com/promptfoo/promptfoo | Prompt/trajectory regression | P1/P2 |
| python-docx | >=1.1,<2 | MIT | https://github.com/python-openxml/python-docx | Optional Word Spec export | optional |

## Platform Services (operated separately, not bundled)

| Service | License | Source | Usage |
|---|---|---|---|
| AgentTeams (Manager/Worker containers) | Apache-2.0 | https://github.com/agentscope-ai/AgentTeams | Runtime orchestration |
| Matrix / Element | Apache-2.0 (Synapse) | https://github.com/element-hq/synapse | Visible, interventionable, persistent messaging |
| MinIO | AGPL-3.0 | https://github.com/minio/minio | Shared project/task/artifact files |
| Higress | Apache-2.0 | https://github.com/alibaba/higress | LLM/MCP unified gateway, consumer auth |

> MinIO is AGPL-3.0. It is operated as a separate service, not modified or
> redistributed within this repository. No MinIO source code is included.

## Data Sources

- All Laptop Stand reviews, competitor SKUs, supplier offers, and fee tables
  in `data/fixtures/laptop_stand/` are **synthetic** and generated
  deterministically by `src/gap2sku/fixtures/generate.py`.
- No real Amazon, Alibaba, or 1688 data is bundled.
- No third-party scraper is a default or compliant data source.

## Excluded by Design (not P0 dependencies)

- Firecrawl, Apify MCP, Crawl4AI, Browser Use
- Great Expectations
- Neo4j / vector databases
- Third-party Amazon/1688 scrapers
