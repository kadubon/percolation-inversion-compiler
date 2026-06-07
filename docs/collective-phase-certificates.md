# Collective Phase Certificates

`CollectivePhaseCertificate` is the v0.3.3 ECPT certificate that asks whether a
finite packet ecology has crossed a protocol-relative ASI-proxy phase threshold.
It is not a proof of real ASI or physical outcomes.

The certificate accepts only when all finite checks pass:

- the agent population is fixed and no self-rewrite or weight update is allowed;
- `HiddenCapabilityInjectionReport` accepts the registry, events, routes, and
  evidence refs against a declared `ProtocolFrameDigest`;
- at least one `AutocatalyticClosureWitness` is accepted;
- at least one `ExecutionAvailablePathCertificate` is accepted and marked
  `not_executed=true`;
- Psi crosses the supplied threshold;
- false liquidity and verifier backlog are bounded;
- SQOT reserve is live and hazard/authority checks are non-rejecting;
- a resource-matched baseline run is present.

`settled` remains `false` unless verifier settlement rules discharge the full
finite route scope. The certificate is useful for agent routing because it
separates productive finite packet closure from raw packet volume and leaves
external physical, oracle, simulator, and real ASI claims as residual
obligations.

CLI:

```powershell
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
```
