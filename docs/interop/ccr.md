# CCR Interop

PIC emits three CCR-facing shapes:

- `ccr.task.v0.1` JSONL for schedulable work;
- `ccr.residual.v0.1` JSONL for residual ledgers;
- diagnostic reports for ALT/ECPT, SQOT, TRC, and BIT adapters.

The interop schemas under `schemas/interop/` are intentionally minimal. They
validate the PIC side of the contract while CCR remains the normative runtime
schema owner.

## Authority Boundary

`constraints.allowed_commands` is always empty in PIC-emitted CCR tasks. Any
PIC command appears only in `extensions.x_pic_safe_command_hints` and
`pic_interop.recommended_pic_commands`.

This distinction is required because a command hint is evidence for scheduling,
not permission to execute.
