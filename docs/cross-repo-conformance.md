# Cross-Repo Conformance

The v0.8 cross-repo loop is:

1. PIC Python emits CCR tasks, residuals, runtime capital witnesses, operation
   gates, MCP/A2A reports, SQOT reports, and BIT reports.
2. CCR imports them without settlement or provider execution.
3. CCR emits foundry dashboards, active cuts, allocation hints, provider state,
   availability reports, and phase acceleration reports.
4. PIC Python checks returned artifacts.
5. PIC-TS emits equivalent public JSON shapes for shared fixtures without
   requiring Python at runtime.

Shared fixtures live in `examples/asi_proxy_acceleration_bundle/`. Compare
required keys, status booleans, blockers, non-claims, residual kinds, and
rounded numeric coordinates. Exact runtime artifact IDs and paths are not
portable conformance fields.

Search terms: cross-repo conformance, CCR, PIC-TS parity, JSON schema,
runtime capital witness, phase acceleration report.
