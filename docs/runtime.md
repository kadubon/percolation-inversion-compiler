# ECPT Active Agent Runtime

`pic runtime` is the v0.3.2 active loop for agents. It composes the existing
finite ECPT planner, SQOT salience scheduler, packet ecology, certificate
checks, verifier route catalog, provenance policy, and residual ledgers into
one deterministic report.

The runtime accepts:

- `RuntimeState`: ECPT phase state, target objective, phase actions, packet
  registry, thresholds, verified packet inventory, quarantine ledger, event
  log, residual ledger, and loop memory.
- `RuntimeStepInput`: one batch of agent output, local packet sources, optional
  live sources, packet candidates, edge certificates, inline evidence envelopes,
  and evidence envelope references.
- `AgentRuntimeConfig`: profile, action commit policy, live connector policy,
  attention/risk budgets, thresholds, and task limits.

It returns `RuntimeStepReport`:

- `registry`: updated capability packet registry with finite edge witnesses.
- `psi`: ECPT ASI-proxy dashboard over `G, DE, AC, VT, LX, SD, CV, FR, BR, QS, HZ`.
- `bottleneck_plan`: ranked finite packet-ecology interventions.
- `phase_run_report`: ECPT phase-control action candidates.
- `salience_schedule`: SQOT queue decisions for packets, obligations, and
  verifier tasks.
- `phase_acceleration_score`: finite score for ranking active agent work.
- `evidence_resolution_batch`: accepted and rejected verifier obligations for
  inline evidence envelopes.
- `promotion_report`: verified packet capital and packet rejections.
- `event_log_delta`: replayable state-transition event records.
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
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input_with_evidence.json --profile production --output runtime-step.json
uv run pic runtime resolve-evidence --input examples/runtime_step_input_with_evidence.json --profile production
uv run pic runtime execute-task --state examples/runtime_state.json --task examples/runtime_agent_task.json --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime run-agent-loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --store runtime.sqlite --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime apply-results --state examples/runtime_state.json --report runtime-step.json --results examples/runtime_action_results.json --output runtime-next-state.json
uv run pic runtime compare --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json
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
    apply_action_results,
    build_runtime_step,
    resolve_step_evidence,
)

state = RuntimeState.model_validate(load_data("examples/runtime_state.json"))
step_input = RuntimeStepInput.model_validate(load_data("examples/runtime_step_input.json"))
report = build_runtime_step(state, step_input, AgentRuntimeConfig(profile="production"))
evidence_batch = resolve_step_evidence(step_input, profile="production")
print(report.model_dump(mode="json")["agent_tasks"])
```

## Agent Loop

1. Observe system output or repository state.
2. Packetize it as `RuntimeStepInput.agent_output` or packet candidates.
3. Run `pic runtime step`.
4. Resolve inline evidence or route `route_execution_requests` to evidence
   adapters.
5. Promote only packets accepted by `promotion_report`.
6. Execute only tasks allowed by the selected `action_commit_policy`.
7. Apply `RuntimeActionResult` records back to state.
8. Compare baseline and candidate `RuntimeRunReport` trajectories.
9. Preserve `residual_ledger`, `event_log`, and `missing_obligations`.
10. Repeat with `pic runtime loop` or the SDK.

The runtime accelerates protocol-relative ASI-proxy phase-control by reducing
agent overhead around evidence routing, semantic edge verification, packet
prioritization, allowlisted execution, and bottleneck selection. It does not
prove unobserved ASI, physical, simulator, or oracle outcomes.
