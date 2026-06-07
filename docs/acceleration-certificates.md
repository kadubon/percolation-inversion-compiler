# Finite Acceleration Certificates

`PhaseAccelerationScore` ranks one runtime step. v0.3.3 adds finite comparison
records so agents can test whether a candidate ECPT runtime path improves on a
resource-matched baseline:

- `RuntimeRunReport`
- `RuntimeComparisonReport`
- `AccelerationCertificate`

The certificate compares:

- threshold crossing step;
- Psi distance reduction;
- score gain;
- residual debt;
- SQOT quarantine obstruction;
- false-liquidity bound;
- verifier backlog bound;
- resource matching.

An accepted certificate means the candidate run improved the finite
protocol-relative ASI-proxy workflow under the declared comparison contract. It
does not settle external physical, oracle, simulator, policy, or real ASI
claims.

CLI:

```powershell
uv run pic runtime compare --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json
```

Agent policy:

- Use certificates to rank runtime strategies and route verifier work.
- Do not treat positive certificates as permission to ignore residual ledgers.
- Re-run comparison after applying action results and packet promotions.
