uv run pic agent explain
uv run pic agent guide --profile development
uv run pic agent readiness --profile development
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development --output intake-report.json
uv run pic agent next --intake-report intake-report.json --profile development
uv run pic snapshot list
uv run pic snapshot routes
uv run pic runtime store init --store runtime.sqlite
uv run pic ecology psi --registry examples/collective_packet_registry.json --threshold examples/ecology_threshold.json
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
