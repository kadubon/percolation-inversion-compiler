# Collective Phase Certificate

`CollectivePhaseCertificate` is the main v0.3.3 record for ECPT collective phase progress. It is designed for agents that need to compare finite packet ecology runs without claiming proof of real ASI.

## What It Certifies

A certificate can be accepted when all required finite checks pass:

- fixed agent population;
- no self-rewrite and no model-weight update;
- unchanged policy digests for the declared observation window;
- no hidden capability injection from undeclared packet, edge, route, evidence, event, or source kinds;
- accepted productive autocatalytic closure witnesses;
- accepted execution-available path certificates;
- threshold-crossed Psi components;
- bounded false liquidity and verification backlog;
- live SQOT diagnostic reserve;
- non-rejecting hazard, authority, rollback, and receiver-context checks;
- resource-matched baseline comparison.

`settled` remains false unless the existing verifier settlement rules discharge the complete scoped finite route. Certification alone is a protocol-relative ASI-proxy result.

## Why It Is Not Self-Rewrite

ECPT collective phase progress is represented as packet availability and composability across a fixed population. The runtime checks that the population identity and policy digests remain fixed unless a protocol explicitly permits otherwise. Model-weight change, fine-tuning, and self-rewrite are not prerequisites and are treated as rejection conditions for this certificate profile.

## Main Records

- `AgentPolicyIdentity`: stable identity, policy digest, model digest, source-kind allowlist, route allowlist, and self-rewrite flags.
- `FixedPopulationLedger`: before/after population comparison.
- `ProtocolFrameDigest`: declared source kinds, packet ids, evidence prefixes, route ids, validity domain, and observation window.
- `AutocatalyticClosureWitness`: accepted packet set with productive regeneration edges.
- `ExecutionAvailablePathCertificate`: accepted path that is available, gated, authorized, rollback-capable, receiver-compatible, and not executed.
- `HiddenCapabilityInjectionReport`: fail-closed check against undeclared packets, routes, edges, sources, evidence refs, or runtime events.
- `CollectivePhaseCertificate`: aggregate finite certificate over the above records.

## Minimal CLI

```powershell
uv run pic ecology closures --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology execution-paths --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology hidden-injection-check --registry examples/collective_packet_registry.json --events examples/walkthrough_collective_phase/empty-events.json --protocol examples/collective_protocol_frame.json
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
```

## Agent Use

An agent should use the certificate as a routing and comparison object:

1. Preserve residual obligations.
2. Route missing verifier evidence.
3. Prefer accepted closure/path evidence over raw packet volume.
4. Compare candidate runs against resource-matched baselines.
5. Avoid treating protocol-relative acceptance as proof of external ASI or physical outcomes.
