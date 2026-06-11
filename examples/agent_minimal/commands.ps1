uv run pic agent explain
uv run pic agent doctor --profile development
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile production --identity-context identity-context.json
