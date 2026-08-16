# Gap2SKU AgentTeams Demo — command entrypoints
# All targets must be actually runnable per spec section 25.

PYTHON ?= python3
export PYTHONPATH := src
UV ?= uv
VENV ?= .venv
PIP := $(VENV)/bin/pip -q

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

doctor: ## Read-only check: Docker, AgentTeams version, resources, ports, deps
	@bash scripts/doctor.sh

bootstrap: ## Install project deps, prepare fixture and agent packages
	@bash scripts/bootstrap.sh

check: ## Lint, strict typing, tests and >=85% coverage
	@$(VENV)/bin/ruff check src tests
	@$(VENV)/bin/mypy src/gap2sku
	@$(VENV)/bin/pytest --cov --cov-report=term-missing -ra

test: check ## Backward-compatible alias

demo-core: ## Deterministic Domain Core path (no AgentTeams dependency)
	@bash scripts/demo_core.sh

demo-agentteams: ## Run first Spec V1 via AgentTeams/Matrix/TeamHarness
	@bash scripts/demo_agentteams.sh

demo-replan: ## Submit $8.00 -> $6.50 change and generate V2
	@bash scripts/demo_replan.sh

evidence: ## Collect redacted run evidence
	@bash scripts/collect_evidence.sh

verify-evidence: ## Verify evidence manifest, hash, tests, artifact refs
	@bash scripts/verify_evidence.sh

mcp: ## Run Gap2SKU MCP server (all role endpoints) on :18090
	@$(VENV)/bin/python -m gap2sku.mcp_server --host 0.0.0.0 --port 18090 --db shared/nap_pillow.db

demo-real: ## Run nap-pillow real-evidence path; expected REVISE without RFQ/BOM
	@bash scripts/demo_real.sh

demo-synthetic: ## Run clearly labelled synthetic supply PASS path
	@bash scripts/demo_synthetic.sh

demo-nogo: ## Run repeated critical durability failure NO-GO path
	@bash scripts/demo_nogo.sh

demo-new-category: ## Run adult desk-accessory path with public supplier signals; expected REVISE
	@$(VENV)/bin/python -m gap2sku.cli.demo_new_category --fresh

demo-new-category-synthetic: ## Run fully labelled synthetic new-category GO regression
	@$(VENV)/bin/python -m gap2sku.cli.demo_new_category --synthetic --fresh

workbench: ## Serve the independent Decision Workbench on :8080
	@$(VENV)/bin/python -m gap2sku.workbench --host 0.0.0.0 --port 8080

workbench-live: ## Serve Workbench with .env.local and live Matrix observer on :8080
	@bash scripts/workbench_live.sh

review-snapshot: ## Prepare the read-only review snapshot evidence
	@bash scripts/review_snapshot.sh

package-review: ## Build the read-only review snapshot code package
	@$(PYTHON) scripts/package_review_snapshot.py

contracts: ## Strictly validate and compile seven gap2sku.agent/v1 packages
	@$(VENV)/bin/python -m gap2sku.cli.contracts

configure-api: ## Securely configure local model/API and Matrix admin credentials
	@bash scripts/configure_api.sh

model-preflight: ## Verify local model credentials without recording secrets
	@set -a; . ./.env.local; set +a; $(VENV)/bin/python -m gap2sku.cli.preflight_models

agentteams-install: ## Install pinned AgentTeams v1.2.2 locally with Docker
	@bash scripts/install_agentteams_local.sh

agentteams-apply: ## Compile/upload seven Agent packages and apply Worker/Team CRs
	@bash scripts/apply_agentteams.sh

agentteams-connect: ## Connect the dedicated Matrix Human Observer to Decision Room
	@set -a; . ./.env.local; set +a; $(VENV)/bin/python -m gap2sku.cli.connect_matrix --env .env.local

agentteams-policy: ## Apply exact default-ask MCP permissions to all seven QwenPaw Workers
	@$(VENV)/bin/python -m gap2sku.cli.configure_worker_mcp

agentteams-verify: ## Verify seven Workers, Team Room, Observer, skills and identities
	@$(VENV)/bin/python -m gap2sku.cli.verify_agentteams

local-up: ## Start local Workbench and MCP services
	@bash scripts/local_start.sh

local-down: ## Stop local Workbench and MCP services
	@bash scripts/local_stop.sh

local-status: ## Check local services and AgentTeams containers
	@bash scripts/local_status.sh

package-v3: ## Build Cloud Studio delivery ZIP and Skill ZIPs
	@bash scripts/package_v3.sh

verify-bundle: ## Verify cloud bundle manifest and run smoke checks
	@bash scripts/verify_bundle.sh

cloud-e2e-report: ## Validate current cloud runtime and write evidence/cloud-studio-e2e.json
	@PYTHONPATH=src $(VENV)/bin/python -m gap2sku.cli.cloud_e2e --root . --started-at "$${CLOUD_RUN_STARTED_AT:?set CLOUD_RUN_STARTED_AT}"

fixture: ## Regenerate synthetic laptop_stand fixture
	@$(VENV)/bin/python -m gap2sku.fixtures.generate --out data/fixtures/laptop_stand

clean: ## Remove build artifacts and venv
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache evidence/*.txt evidence/*.jsonl evidence/*.json 2>/dev/null || true

.PHONY: help doctor bootstrap check test demo-core demo-real demo-synthetic demo-nogo demo-new-category demo-new-category-synthetic demo-agentteams demo-replan evidence verify-evidence mcp workbench workbench-live review-snapshot package-review contracts configure-api model-preflight agentteams-install agentteams-apply agentteams-connect agentteams-policy agentteams-verify local-up local-down local-status fixture package-v3 verify-bundle cloud-e2e-report clean
