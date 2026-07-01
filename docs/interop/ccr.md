# CCR Interop

PIC emits three CCR-facing shapes:

- `ccr.task.v0.1` JSONL for schedulable work;
- `ccr.residual.v0.1` JSONL for residual ledgers;
- diagnostic reports for ALT/ECPT, SQOT, TRC, and BIT adapters.
- `pic.trc_operation_gate_report.v1` for non-executing TRC operation
  preflight data.

The interop schemas under `schemas/interop/` are intentionally minimal. They
validate the PIC side of the contract while CCR remains the normative runtime
schema owner.

## Authority Boundary

`constraints.allowed_commands` is always empty in PIC-emitted CCR tasks. Any
PIC command appears only in `extensions.x_pic_safe_command_hints` and
`pic_interop.recommended_pic_commands`.

This distinction is required because a command hint is evidence for scheduling,
not permission to execute.

## TRC Operation Gate

Use `pic trc operation-gate --trace <trace_nf.json> --provider-profile
<profile.json>` when a runtime needs authority and dispatch diagnostics before
CCR planning. The report contains `operation_ready`,
`provider_dispatch_ready`, `physical_dispatch_ready`, gate objects, residuals,
and non-claims.

Authority envelopes must be `approved` or `active`, unexpired relative to the
operation evaluation clock, and scoped to the validity domain and provider
target. Missing time data becomes `authority_time_unknown` unless the trace is
explicitly `fixture_mode=true` with `side_effect_policy=dry_run_only`. A
fixture-only `expires_at: 1970-01-01T00:00:00Z` trace is diagnostic-only and
non-executable.

`operation_ready` is not execution. `provider_dispatch_ready` is not dispatch.
`physical_dispatch_ready` is not physical outcome proof.

## ALT Capital Admission

`pic alt bridge ecpt` reports now separate `accepted` from
`capital_admitted`. A proxy-only or negative-liquidity bridge can be accepted as
a syntactic report while `capital_admitted=false` and blockers remain explicit.
