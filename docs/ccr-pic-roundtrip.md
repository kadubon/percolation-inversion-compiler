# CCR/PIC Roundtrip

v0.8.0 adds a CARA/operation roundtrip: PIC emits target checks, baseline
checks, runtime capital witnesses, MCP/A2A reports, SQOT protocol diagnostics,
BIT MEC frontier reports, and TRC operation-gate reports; CCR imports them as
candidate evidence and residual work. No import implies settlement or provider
execution.

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

For real-world operation candidates, PIC reports `operation_ready`,
`provider_dispatch_ready`, and `physical_dispatch_ready` separately. CCR still
requires a matching preflight, explicit operator approval, provider policy, and
observation verifier before any provider dispatch path can be considered.

For ECPT phase-response loops, PIC can emit
`pic.phase_response_control_step.v1`. CCR consumes that report with:

```bash
ccr foundry allocate --strategy phase-response --response-report phase_response.json --json
```

The allocation is advisory and does not promote settlement or execute providers.
