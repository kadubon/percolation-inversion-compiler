# Population Runtime

`AgentPopulationState` groups several `RuntimeState` records under one protocol
frame and fixed-population ledger. `build_population_runtime_step` runs one
runtime step per agent state, merges packet registries deterministically, checks
hidden capability injection, and returns `PopulationRuntimeStepReport`.

The population runtime is for collective ECPT phase evaluation:

```powershell
uv run pic runtime population-step --population examples/agent_population.json --inputs examples/runtime_loop_inputs.jsonl --profile production
```

The report includes:

- per-agent `RuntimeStepReport` values;
- checked `FixedPopulationLedger`;
- `HiddenCapabilityInjectionReport`;
- aggregate Psi dashboard;
- next population state;
- residual ledger and diagnostic reasons.

The service exposes the same contract at `POST /runtime/population/step`.
Production service mode still requires bearer auth, rejects oversized requests,
and does not allow live connectors unless the request and service settings both
opt in.
