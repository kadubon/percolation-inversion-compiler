# PIC/CCR Interoperability

PIC is the checker/compiler layer. CCR is the runtime/orchestration layer. PIC
emits deterministic JSON and JSONL reports that CCR can import as candidate
tasks, residuals, capital witnesses, operation gates, and phase diagnostics.

The boundary is explicit:

- PIC `accepted=true` does not imply CCR `settled=true`.
- `capital_admitted=true` is lower-bound evidence, not settlement.
- `provider_dispatch_ready` is not dispatch.
- `physical_dispatch_ready` is not physical outcome proof.
- Safe command hints are data for operators, not authority.
- MCP descriptors and A2A handoffs are untrusted until checked.

Use `examples/asi_proxy_acceleration_bundle/` for v0.8 target/baseline/capital,
MCP/A2A, SQOT, BIT, TRC, preflight, and foundry fixture shapes.

Use `examples/asi_proxy_loop_bundle/` for the v0.9 agent-operable loop. It adds
target/baseline, capital witnesses, loop state, active cuts, interval
acceleration, token admissibility, extraction pipeline, MCP/A2A gate binding,
observation residuals, and performance report examples. These are importable
fixtures, not authority to dispatch providers or execute real-world actions.
