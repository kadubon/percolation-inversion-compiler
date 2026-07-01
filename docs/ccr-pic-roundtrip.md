# CCR/PIC Roundtrip

The roundtrip boundary is:

1. PIC emits deterministic CCR task or residual JSONL.
2. CCR imports the JSONL as candidate work.
3. CCR schedules, leases, stores, and preserves residuals.
4. PIC can later check packets or phase reports again.

PIC never grants execution authority to CCR. CCR never treats PIC
`accepted=true` as settlement unless all residual and verifier gates have been
closed.

Useful commands:

```bash
pic phase plan --compact --emit ccr-tasks > tasks.jsonl
pic phase gap --compact --emit ccr-residuals > residuals.jsonl
ccr task import --file tasks.jsonl --provider pic --json
ccr residual import --file residuals.jsonl --provider pic --json
ccr phase report --json
```

The examples in `examples/interop/pic_to_ccr_roundtrip/` use fixed timestamps so
their output is stable.
