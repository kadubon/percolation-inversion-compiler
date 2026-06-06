# ECPT Active Agent Runtime

`pic runtime` is the v0.3.0 active loop for agents. It composes the existing
finite ECPT planner, SQOT salience scheduler, packet ecology, certificate
checks, verifier route catalog, provenance policy, and residual ledgers into
one deterministic report.

The runtime accepts:

- `RuntimeState`: ECPT phase state, target objective, phase actions, packet
  registry, thresholds, residual ledger, and loop memory.
- `RuntimeStepInput`: one batch of agent output, local packet sources, optional
  live sources, packet candidates, and evidence envelope references.
- `AgentRuntimeConfig`: profile, action commit policy, live connector policy,
  attention/risk budgets, thresholds, and task limits.

It returns `RuntimeStepReport`:

- `registry`: updated capability packet registry with finite edge witnesses.
- `psi`: ECPT ASI-proxy dashboard over `G, DE, AC, VT, LX, SD, CV, FR, BR`.
- `bottleneck_plan`: ranked finite packet-ecology interventions.
- `phase_run_report`: ECPT phase-control action candidates.
- `salience_schedule`: SQOT queue decisions for packets, obligations, and
  verifier tasks.
- `phase_acceleration_score`: finite score for ranking active agent work.
- `agent_tasks`: concrete next tasks with rollback conditions, required
  evidence kind, verifier route, and residual coordinates.
- `route_execution_requests`: verifier route requests with settlement scope and
  residual external obligations.
- `residual_ledger` and `missing_obligations`: carried forward for the next
  runtime step.

`settled` remains `false` unless existing verifier-resolution rules discharge
the full finite scope. Planning, packet priority, text output, registry metadata,
snapshot metadata, and route availability do not promote a claim to settled.

## CLI

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
uv run pic runtime loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --max-steps 2 --profile production
uv run pic runtime health --state examples/runtime_state.json --profile production
uv run pic runtime export-openapi --output runtime-openapi.json
```

Live connectors are disabled by default. A runtime step uses GitHub, Zenodo, or
arXiv only when both the runtime config and the step input set
`allow_live_connectors=true`.

## Python SDK

```python
from percolation_inversion_compiler.io.schema import load_data
from percolation_inversion_compiler.runtime import (
    AgentRuntimeConfig,
    RuntimeState,
    RuntimeStepInput,
    build_runtime_step,
)

state = RuntimeState.model_validate(load_data("examples/runtime_state.json"))
step_input = RuntimeStepInput.model_validate(load_data("examples/runtime_step_input.json"))
report = build_runtime_step(state, step_input, AgentRuntimeConfig(profile="production"))
print(report.model_dump(mode="json")["agent_tasks"])
```

## Agent Loop

1. Observe system output or repository state.
2. Packetize it as `RuntimeStepInput.agent_output` or packet candidates.
3. Run `pic runtime step`.
4. Route `route_execution_requests` to evidence adapters.
5. Execute only tasks allowed by the selected `action_commit_policy`.
6. Preserve `residual_ledger` and `missing_obligations`.
7. Repeat with `pic runtime loop` or the SDK.

The runtime accelerates protocol-relative ASI-proxy phase-control by reducing
agent overhead around evidence routing, packet prioritization, and bottleneck
selection. It does not prove unobserved ASI, physical, simulator, or oracle
outcomes.
