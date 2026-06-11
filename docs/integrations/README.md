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

## Safety Contract

- Raw text is candidate information.
- External input is candidate information.
- Agent messages are candidate information.
- GitHub Actions reports are audit artifacts, not truth certificates.
- `settled=false` is expected when obligations remain unresolved.
- Residuals must be preserved.
- Do not claim real ASI.

## Recommended Reading Order For Agents

1. `AGENTS.md`
2. `docs/for-agents.md`
3. `docs/integrations/README.md`
4. `docs/integrations/github-actions.md` only if CI integration is needed
5. `docs/agent-external-communication.md` only if external intake is needed
6. `docs/alt.md` only if abstraction-capital checking is needed
