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
  authority, rollback, and route safety fields.
- `OccupationLedger`: finite attention budget and class-level occupation.
- `DiagnosticReservePolicy`: reserve that protects diagnostic work from being
  consumed by attractive but unsafe packets.
- `QuarantineLedger`: stale, hash-invalid, authority-invalid, unsafe-route, or
  rollback-required records.
- `SalienceScheduleReport`: deterministic scheduling output for agents.

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
- residual ledger burden
```

Freshness scales positive value. Queue priority never promotes a claim to
`settled`; it only routes attention and preserves residual debt.

Canonical source:

Takahashi, K. (2026). *Salience-Queue Occupation Theory*. Zenodo.
https://doi.org/10.5281/zenodo.20526451
