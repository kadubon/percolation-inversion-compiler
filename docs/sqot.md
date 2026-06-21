# SQOT Salience Scheduler

SQOT support adds a finite attention-queue layer over certificate and obligation
workflows. The scheduler does not decide that a claim is true. It decides which
packet, obligation, or verifier task should occupy finite attention next while
preserving diagnostic reserve and fail-closed quarantine rules.

```powershell
uv run pic snapshot show --artifact sqot
uv run pic sqot schedule --packets examples\sqot_queue.json --profile production
```

Core records:

- `SalienceQueueRecord`: packet, obligation, or verifier task with expected
  downstream gain, residual reduction, verification cost, freshness, hazard,
  authority, rollback, audit-recursion, latency/deadline, aggregation, and
  route safety fields.
- `OccupationLedger`: finite attention budget and class-level occupation.
- `DiagnosticReservePolicy`: reserve that protects diagnostic work from being
  consumed by attractive but unsafe packets.
- `QuarantineLedger`: stale, hash-invalid, authority-invalid, unsafe-route, or
  rollback-required records.
- `SalienceScheduleReport`: deterministic scheduling output for agents.
  v0.4.4 adds effective diagnostic reserve, audit recursion violations,
  latency/deadline loss, rollback-class summary, aggregation occupation, and
  label-laundering suspicions. It also exposes distributed-origin count,
  protocol-integrity refs, privacy/rejoin refs, sovereignty-kernel refs,
  adversarial-transfer charge, and thermodynamic-discharge charge.

In common terms, SQOT is the finite task scheduler. These diagnostics tell an
agent whether attention is being consumed safely, whether labels are hiding
underlying signals, and whether rollback or deadline pressure should route work
to diagnostic repair instead of promotion.

Decision meanings:

- `run`: finite queue checks passed and the task fits budget/reserve/risk.
- `defer`: valid task, but priority, reserve, or risk is not favorable enough.
- `quarantine`: unsafe task without accepted rollback path.
- `rollback`: unsafe task with rollback available.
- `abstain`: insufficient attention budget.

Scheduler priority is finite and explicit:

```text
expected downstream gain
+ residual reduction
- verification cost
- hazard charge
- latency and deadline loss
- residual ledger burden
- adversarial transfer risk
- thermodynamic discharge cost
```

Freshness scales positive value. Queue priority never promotes a claim to
`settled`; it only routes attention and preserves residual debt.

Canonical source:

Takahashi, K. (2026). *Salience-Queue Occupation Theory*. Zenodo.
https://doi.org/10.5281/zenodo.20526451
