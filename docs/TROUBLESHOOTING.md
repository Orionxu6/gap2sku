# Troubleshooting

## `make bootstrap` fails

- Ensure Python >= 3.10: `python3 --version`
- Ensure pip available: `python3 -m pip --version`
- Try: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`

## `make test` fails

- Check fixture generated: `ls data/fixtures/laptop_stand/`
- Regenerate: `make fixture`
- Run single test: `.venv/bin/pytest tests/unit/test_economics.py -v`

## `make demo-core` fails

- Ensure fixture exists (run `make bootstrap` first)
- Check DB path writable: `shared/gap2sku.db`
- Read trace: `cat evidence/domain-trace.jsonl`

## MCP server not reachable from Docker

- Worker in Docker cannot use `127.0.0.1`; use host gateway:
  `docker inspect -f '{{range .NetworkSettings.Networks}}{{println .Gateway}}{{end}}' hiclaw-manager`
- Set `GAP2SKU_MCP_BASE_URL=http://<GATEWAY_IP>:18090` in `.env`
- Verify from container: `docker exec -it hiclaw-manager curl http://<GATEWAY_IP>:18090/health`

## AgentTeams agt CLI not found

- This is expected in dev (Plan B). Use `at/create_agents_messages.md` for manual setup.
- Install: `bash <(curl -fsSL https://raw.githubusercontent.com/agentscope-ai/AgentTeams/v1.2.0/install/agentteams-install.sh)`

## Reviewer returns BLOCK

- Check `evidence/demo-core-run.json` -> review.errors for Rule IDs.
- Common: R003 (hard constraint), R004 (ACCEPT without evidence), R007 (no econ trace).
- Fix domain logic, not the reviewer.

## Replan shows Market calls > 0

- Check `CONSTRAINT_PATH_IMPACT` in `src/gap2sku/graph/impact.py`.
- `factory_cost_max` must NOT include Evidence/PainPoint/Feature types.
- Run: `.venv/bin/pytest tests/unit/test_replanning.py -v`
