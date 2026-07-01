# MCP And A2A Safety

PIC v0.8 emits structured MCP and A2A reports instead of boolean placeholders.
Descriptors, calls, cards, and handoffs are candidate evidence until checked.
They do not grant delegated tool authority or settlement.

Use:

```bash
pic mcp descriptor-check --descriptor descriptor.json --profile development
pic mcp invocation-preflight --descriptor descriptor.json --call call.json --profile development
pic a2a card-check --card card.json --profile development
pic a2a handoff-check --handoff handoff.json --profile development
```

MCP reports preserve descriptor hash, version, canonical tool name, side-effect
class, auth scope, egress policy, budgets, schema hashes, provenance/signature
requirements, rug-pull blockers, and argument-escalation blockers. A2A reports
preserve identity, endpoint provenance, task schema, declared authority, nonce,
idempotency key, and the non-claim that handoff evidence is not settlement.

Search terms: MCP descriptor report, MCP invocation preflight, A2A agent card,
A2A handoff, tool safety, delegated authority.
