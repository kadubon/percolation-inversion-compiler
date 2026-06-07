# Resource-Matched Benchmarks

ECPT acceleration claims are comparative. v0.3.3 adds `ResourceEnvelope` and
`ResourceMatchedBaselineConfig` so candidate runs are compared against baselines
with matching operational resources.

Resource envelope coordinates:

- wall-clock window proxy;
- token budget;
- verifier calls;
- network calls;
- compute cost;
- human review budget;
- risk budget.

`certify_runtime_acceleration` accepts a finite acceleration certificate only
when resource units, envelope coordinates, baseline protocol, constraint frame,
receiver family, and validity domain match within the declared tolerance.

```powershell
uv run pic runtime compare --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
```

The certificate is a finite ASI-proxy comparison result, not a real-world ASI
or physical-domain proof.
