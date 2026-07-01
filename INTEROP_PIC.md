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
