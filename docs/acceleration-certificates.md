# Finite Acceleration Certificates

`PhaseAccelerationScore` ranks one runtime step. v1.1 comparison records let
agents test whether a candidate ECPT runtime path improves on a
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
- paired direction-aware measurements with fixed horizon, stopping rule,
  evidence, and per-metric tolerances.

`accepted=true` records the finite structural lower bound.
`acceleration_metrics_certified=true` records the paired empirical comparison.
Require both for an operational acceleration claim. Neither settles external
physical, oracle, simulator, policy, or real ASI claims.

CLI:

```powershell
uv run pic runtime compare --baseline examples/runtime_acceleration/baseline.json --candidate examples/runtime_acceleration/candidate.json
uv run pic runtime certify-acceleration --baseline examples/runtime_acceleration/baseline.json --candidate examples/runtime_acceleration/candidate.json
```

Agent policy:

- Use certificates to rank runtime strategies and route verifier work.
- Do not treat positive certificates as permission to ignore residual ledgers.
- Re-run comparison after applying action results and packet promotions.
