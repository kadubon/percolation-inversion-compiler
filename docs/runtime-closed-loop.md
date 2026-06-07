# ECPT Closed-Loop Runtime

v0.3.3 closes the agent loop around the ECPT active runtime:

```text
observe -> packetize -> resolve evidence -> promote verified packets
-> schedule -> act -> apply result -> compare runs -> certify finite acceleration
-> repeat
```

The loop is a finite certificate and residual-ledger workflow. It helps agents
move protocol-relative ASI-proxy phase-control forward by turning agent output
and evidence into reusable packet capital, verifier requests, SQOT scheduling
decisions, and baseline comparison reports. It does not prove unobserved ASI,
physical, simulator, or oracle outcomes.

CLI path:

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input_with_evidence.json --profile production --output runtime-step.json
uv run pic runtime resolve-evidence --input examples/runtime_step_input_with_evidence.json --profile production
uv run pic runtime apply-results --state examples/runtime_state.json --report runtime-step.json --results examples/runtime_action_results.json --output runtime-next-state.json
uv run pic runtime compare --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json
```

SDK path:

```python
from percolation_inversion_compiler.runtime import (
    AgentRuntimeConfig,
    RuntimeState,
    RuntimeStepInput,
    apply_action_results,
    build_runtime_step,
    compare_runtime_runs,
    resolve_step_evidence,
)
from percolation_inversion_compiler.io.schema import load_data

state = RuntimeState.model_validate(load_data("examples/runtime_state.json"))
step_input = RuntimeStepInput.model_validate(
    load_data("examples/runtime_step_input_with_evidence.json")
)
report = build_runtime_step(state, step_input, AgentRuntimeConfig(profile="production"))
batch = resolve_step_evidence(step_input, profile="production")
```

Operational rules:

- `RuntimeActionResult` can update packet state and event logs, but cannot
  promote status to settled by itself.
- `EvidenceResolutionBatch` reduces missing obligations only within the finite
  scope accepted by verifier route contracts.
- `RuntimeEventLog.aggregate_sha256` makes closed-loop state transitions
  replayable and portable.
- SQOT quarantine prevents unsafe packets from becoming operational runtime
  advice.
- `AccelerationCertificate` is a finite ASI-proxy certificate, not a real-world
  ASI proof.
