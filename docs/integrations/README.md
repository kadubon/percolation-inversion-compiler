# Integration Examples

This page indexes the main ways to use Percolation Inversion Compiler (PIC)
without making any one deployment surface the center of the project.

## What PIC Is

Percolation Inversion Compiler is a general AI agent output checker and runtime
verification layer. PIC is not specific to GitHub Actions.

## Choose An Integration Surface

| Surface | Use when | Start with |
| --- | --- | --- |
| CLI | You want to check one AI-generated text or file locally. | `pic agent intake` |
| Python SDK | You are building an agent runtime or orchestration system. | `run_agent_intake` |
| GitHub Actions | You want a read-only PR or workflow artifact checker. | `examples/github_action_agent_output_check/` |
| Runtime service | You want local-first HTTP integration. | `pic runtime service` |
| External intake | You want to ingest web/feed/repository/message content as candidates. | `pic agent communication-guide` |
| Agent messages | You want to inspect agent-to-agent packet exchange. | `pic agent message contract` |
| ALT foundry | You want to check reusable abstraction capital. | `pic alt admit` |
| Optional adoption sidecar | You need operator-facing handoff text without workflow gating. | `pic adoption request` |
| Canonical readiness sidecar | You need pip-safe ECPT/BIT/TRC/SQOT/ALT implementation coverage. | `pic audit canonical-readiness` |
| Packet exchange sidecar | You need data-only packet export, inspect, merge, or lineage. | `pic packet inspect` |
| Phase dashboard sidecar | You need observation-only phase metrics. | `pic phase dashboard` |
| Phase Ecology Lab | You need windowed multi-packet graph, closure, path, and threshold diagnostics. | `pic phase lab init` |
| Agent autonomy audit | You need to verify approval/adoption is not gating core agent work. | `pic agent autonomy-audit` |

## Safety Contract

- Raw text is candidate information.
- External input is candidate information.
- Agent messages are candidate information.
- GitHub Actions reports are audit artifacts, not truth certificates.
- `settled=false` is expected when obligations remain unresolved.
- Residuals must be preserved.
- Do not claim real ASI.
- Optional sidecars do not gate `pic agent check`, `pic phase plan`, or `pic agent accelerate`.
- Canonical readiness is snapshot-derived metadata and does not replace local
  TeX fidelity audits.
- `percolation-inversion-compiler[agent-full]` adds connector, identity, and local service
  dependencies without requiring the science/OT/LP research extras.
- Localized Markdown is display-only; JSON schemas and keys stay stable for ports.
- Packet exchange and dashboards are diagnostic-only and do not promote packets.
- Phase Lab effective graphs separate accepted contribution from candidate-only
  volume and do not execute stored content.

## Recommended Reading Order For Agents

1. `AGENTS.md`
2. `docs/for-agents.md`
3. `docs/integrations/README.md`
4. `docs/integrations/github-actions.md` only if CI integration is needed
5. `docs/agent-external-communication.md` only if external intake is needed
6. `docs/alt.md` only if abstraction-capital checking is needed
7. `docs/operator-adoption.md` only if operator handoff is needed
8. `docs/integrations/packet-exchange.md` only if packet handoff is needed
9. `docs/phase-dashboard.md` only if dashboard observation is needed
10. `docs/phase-ecology-lab.md` when windowed graph/closure/path diagnostics matter
11. `docs/canonical-implementation-readiness.md` when installed canonical coverage matters
12. `docs/i18n-and-portability.md` when localized Markdown or cross-language ports matter
