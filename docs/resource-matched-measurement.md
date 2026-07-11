# Resource-Matched Measurement

ASI-proxy acceleration is a paired operational measurement, not proof of real
ASI. Use the same observation protocol, constraint frame, receiver family,
validity domain, fixed horizon, stopping rule, and resource envelope for the
baseline and candidate.

```bash
pic runtime certify-acceleration \
  --baseline examples/runtime_acceleration/baseline.json \
  --candidate examples/runtime_acceleration/candidate.json
```

For PIC-TS, use `npx pic-ts` in place of `pic`.

## Decision Layers

- `accepted=true` means the finite structural comparison found a positive
  lower bound and passed resource, SQOT, false-liquidity, verifier backlog, and
  residual-debt checks.
- `acceleration_metrics_certified=true` means the paired measurements are
  comparable, evidence-backed, and directionally improved.
- Treat the runtime as a measured accelerator only when both fields are true.

## Metric Directions

Higher is better for verification yield, receiver reuse, and certified capital
gain. Lower is better for time-to-verified, residual half-life, resource cost,
and the absolute value of error correlation.

Each metric may have a non-negative tolerance in
`ResourceMatchedBaselineConfig.metric_tolerances`. Certification requires no
regression beyond tolerance and at least one improvement beyond tolerance.
Missing or non-finite measurements are unknown and block certification.

Raw agent count, candidate count, cache hits, and provider receipts are
diagnostic volume. They do not establish progress.

The negative fixtures in `examples/runtime_acceleration/` show rejection for
resource mismatch, post-selected horizon, missing evidence, and metric
regression.

