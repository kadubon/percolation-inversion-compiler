# Runtime Acceleration Fixtures

Run the accepted pair:

```bash
pic runtime certify-acceleration --baseline examples/runtime_acceleration/baseline.json --candidate examples/runtime_acceleration/candidate.json
```

For PIC-TS, replace `pic` with `npx pic-ts`.

The four `candidate_*.json` negative cases demonstrate rejection for a
resource mismatch, post-selected horizon, missing evidence, and a metric
regression. A usable acceleration claim requires both `accepted=true` and
`acceleration_metrics_certified=true`.

