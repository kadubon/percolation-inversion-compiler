# Benchmarks

v0.3.2 treats acceleration as a finite, protocol-relative measurement problem.
The package does not claim to prove an unobserved ASI transition. It gives
agents measurable proxy loops for comparing packet ecology workflows.

Recommended benchmark families:

- repository understanding: time to accepted packet graph over a codebase;
- theorem-to-implementation: time to claim-to-code and claim-to-test witnesses;
- verifier construction: accepted route count per unit verification cost;
- proof-obligation discharge: residual debt reduction without false liquidity;
- cross-domain transfer: accepted liquidity bridge packets across receiver
  families;
- workflow recovery: quarantine/rollback effectiveness after invalid packets;
- long-horizon debt control: unresolved obligation backlog under fixed budget.

Minimum metrics:

- accepted packet rate;
- rejected and abstained packet rate;
- unresolved obligation backlog;
- verifier latency proxy;
- stale packet ratio;
- evidence hash mismatch rate;
- false-liquidity rate;
- residual debt growth;
- Psi distance-to-threshold before and after the intervention.

Use the runtime commands as benchmark probes:

```powershell
uv run pic sqot schedule --packets examples\sqot_queue.json --profile production
uv run pic ecology build-edges --packets examples\ecology_packets.json --output ecology-registry.json
uv run pic ecology psi --registry ecology-registry.json --threshold examples\ecology_threshold.json --output ecology-psi.json
uv run pic ecology plan --registry ecology-registry.json --psi ecology-psi.json --profile production
uv run pic runtime compare --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json --threshold examples\runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json
```

An accepted `AccelerationCertificate` is a finite benchmark result. It should be
logged with the residual ledger and external obligations that remain after the
comparison.
