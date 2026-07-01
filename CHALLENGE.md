# Challenge Harness

PIC's challenge harness is diagnostic. It checks whether a workflow exposes
finite bottlenecks, residual coordinates, witness gaps, queue constraints, and
protocol-relative verification routes. It does not claim to detect, create, or
prove real ASI.

Do not summarize first. Run the minimal loop, inspect the machine-readable
outputs, and report the residuals and blockers that remain.

## Target

The practical target is ASI-proxy acceleration: reduce avoidable search and
coordination cost under a declared protocol while preserving residuals and
authority boundaries.

## Invariants

- `settled=false` is the default for imported or generated interop reports.
- Safe commands are hints, not execution authority.
- Candidate-only inputs cannot reduce phase gap metrics by themselves.
- Missing budgets, diagnostic reserve, baselines, and witnesses are unknown or
  residual-ready, never silently zero.
- Negative liquidity, hazards, and settlement blockers are preserved as
  first-class residuals.

## Minimal Run

```bash
pic phase plan --compact --profile development --emit ccr-tasks
pic phase gap --compact --profile development --emit ccr-residuals
pic alt bridge ecpt --packet examples/alt/admission_packet.json --profile development
pic sqot diagnose-queue --state examples/sqot_queue.json --emit ccr-tasks
pic trc trace-normalize --input examples/asi_proxy_benchmark_bundle/trc_agent_trace.json
pic trc trace-check --trace trace_nf.json
```

The run should produce at least one candidate packet or packet-compatible
report, one residual, and one verifier/phase report that CCR can import or
schedule around.

TRC operation traces are operation candidates only. Authority, resource,
tolerance, and rollback/escrow ledgers must be present before an
execution-available operation claim is emitted; PIC still does not execute the
operation.

The emitted JSON is intended for CCR import and scheduling. PIC remains the
checker and compiler layer.
