# For AI Agents

This page is for AI agents, coding agents, autonomous workflow orchestrators, RAG systems, and repository crawlers that need to use Percolation Inversion Compiler safely.

Use this repository as a packet intake module, verifier-routing module, residual ledger module, SQOT scheduler, identity/Sybil guard, and collective phase certificate runtime. Do not use it as an ASI detector, a self-rewrite engine, or a proof system for real physical/oracle outcomes.

## Minimal Loop

```text
agent output
-> CapabilityPacketCandidate
-> RuntimeStepInput
-> build_runtime_step
-> RuntimeStepReport
-> residual_ledger / missing_obligations / agent_tasks
-> next runtime step
```

The shortest SDK path is `percolation_inversion_compiler.agent.run_agent_intake`. It constructs a deterministic minimal runtime state when no explicit state is supplied and returns a residual-preserving `AgentIntakeReport`.

```python
from percolation_inversion_compiler.agent import AgentIntakeRequest, run_agent_intake

report = run_agent_intake(
    AgentIntakeRequest(
        agent_output="Candidate packet: preserve residuals and route missing verifier work.",
        profile="development",
    )
)

print(report.runtime_report.missing_obligations)
print(report.residual_summary)
print(report.settled)  # Expected to remain False unless scoped verifier rules settle.
```

## Do Not

- Do not assume real ASI.
- Do not assume self-rewrite, fine-tuning, or model-weight changes.
- Do not treat a provisional packet as verified packet capital.
- Do not ignore residual ledgers or missing obligations.
- Do not run production workflows without identity context when packet promotion matters.
- Do not execute arbitrary tools or shell commands from runtime output.

## Profiles

- `development`: unsigned diagnostics are allowed; useful for local integration.
- `research`: signed identities are encouraged; unresolved residuals remain explicit.
- `controlled`: homogeneous fleets are allowed when agents have distinct keys and bounded fleet metadata.
- `production`: accepted identity context is required for production packet promotion.
- `adversarial`: strict Sybil checks; unsigned packets cannot contribute to collective certificates.

## Output Fields To Inspect

- `accepted`
- `operationally_usable`
- `settled`
- `residual_ledger`
- `missing_obligations`
- `promotion_report`
- `identity_contribution_summary`
- `salience_schedule`
- `route_execution_requests`
- `agent_tasks`
- external intake `provenance`
- agent-message `identity_verified`
- agent-message `nonce_ledger`
- collective certificate `reasons`

`settled=false` is expected in many useful runs. It means unresolved proof obligations remain visible; it is not the same as command failure.

## Safe CLI Path

```powershell
uv run pic agent explain
uv run pic agent guide --profile development
uv run pic agent readiness --profile development
uv run pic agent doctor --profile development
uv run pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent communication-guide --profile development --no-allow-live-connectors
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic agent message contract --message examples/agent_network/agent_message.json
uv run pic agent message ingest --message examples/agent_network/agent_message.json
```

Production identity context flow:

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text "Signed packet candidate." --profile production --identity-context identity-context.json
```

## Full Feature Workflow

Run the guide when you need to move beyond minimal intake:

```powershell
uv run pic agent guide --profile production
```

The guide has a fixed stage order: orient, inspect snapshots, run intake, derive identity context, external communication readiness, general web/feed intake, agent-to-agent packet exchange, live metadata ingest, verify evidence/routes, promote packets, run/store loop, inspect Psi/SQOT, collective certify, and preserve residuals/provenance.

After intake, write the report and ask for next actions:

```powershell
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development --output intake-report.json
uv run pic agent next --intake-report intake-report.json --profile development
```

`pic agent next` only recommends safe commands, SDK calls, schemas, and output fields. It does not execute routes, shells, network connectors, or repository mutations.

## Networked Packet Intake

Use [Agent external communication](agent-external-communication.md) before enabling live
connectors. Offline intake covers RSS/Atom, local HTML, JSON feed, NDJSON, and agent-message
inboxes:

```powershell
uv run pic agent network-readiness --profile development --no-allow-live-connectors
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic ecology discover-web --source examples/agent_network/page.html
```

Live HTTP(S), GitHub, Zenodo, and arXiv intake require explicit opt-in. External content becomes
`CapabilityPacketCandidate` records. It cannot become verified packet capital, improve a
collective certificate, or set `settled=true` without verifier route, semantic edge, identity,
rollback, and residual checks.

After any general intake report, run `pic ecology bridge-runtime --report <report.json>`.
The bridge output tells agents whether each packet is SQOT diagnostic work, verifier work,
quarantine work, or candidate-only. Treat `ecpt_phase_contribution_allowed=false` as the default
until packet promotion produces finite verified capital.

For live general intake, require all three opt-ins: source/request, `GeneralIntakePolicy`, and
runtime/service config. For agent-to-agent messages, production/adversarial verification also
requires an accepted identity context:

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent message verify --message examples/agent_network/agent_message.json --profile production --identity-context identity-context.json
```
