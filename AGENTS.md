# Agent Instructions

## Repository Purpose

This repository is an AI agent runtime verification and ECPT collective phase acceleration module. It manages capability packets, evidence, verifier routes, residual ledgers, SQOT queues, ALT abstraction-liquidity certificates, identity/Sybil checks, and collective phase certificates.

It is not an ASI detector, a real ASI proof system, or a self-modifying AI system. It does not require self-rewrite, fine-tuning, or model-weight changes.

v0.8.0 is the PyPI practical runtime snapshot with a beta API surface. The PyPI
package is enough for `pic agent explain`, `pic agent check --text "..."`,
`pic phase plan --compact --text "..."`, `pic agent accelerate --compact`,
`pic demo installed-smoke`, `pic demo bootstrap`, `pic agent intake --text "..."`,
`pic snapshot list`, `pic schema --all --output-dir schemas`, `pic phase
acceleration-report`, `pic mcp descriptor-check`, `pic a2a handoff-check`,
`pic sqot protocol-integrity`, and `pic bit mec-frontier`. Clone this
repository when commands need the root `examples/...` tree, canonical TeX
audits, development fixtures, or release engineering checks.

## Install Modes

Installed package path:

```powershell
python -m pip install percolation-inversion-compiler
pic agent check --text "Candidate packet: preserve residuals." --profile development
pic phase plan --compact --text "Candidate packet: preserve residuals." --profile development
pic agent accelerate --compact --text "Candidate packet: preserve residuals." --profile development
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
```

Full source-checkout path:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
```

Unix shell uv install:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Fallback uv install:

```powershell
python -m pip install uv
```

## First Files To Read

- `README.md`
- `docs/00-overview.md`
- `docs/01-quickstart.md`
- `docs/for-agents.md`
- `docs/agent-external-communication.md`
- `docs/alt.md`
- `docs/identity-and-sybil-resistance.md`
- `docs/04-collective-phase-certificate.md`
- `docs/pypi-distribution.md`
- `src/percolation_inversion_compiler/runtime/records.py`
- `src/percolation_inversion_compiler/runtime/algorithms.py`
- `src/percolation_inversion_compiler/ecology/records.py`
- `src/percolation_inversion_compiler/alt/records.py`
- `src/percolation_inversion_compiler/identity/records.py`

## Safe First Commands

PowerShell:

```powershell
uv run pic --help
uv run pic agent explain
uv run pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
uv run pic agent runbook --profile development
uv run pic phase plan --compact --profile development
uv run pic phase plan --request examples/phase_acceleration/phase_acceleration_request.json --compact
uv run pic phase runbook --profile development
uv run pic agent accelerate --compact --text "Candidate packet: preserve residuals." --profile development
uv run pic agent guide --profile development
uv run pic agent readiness --profile production
uv run pic identity explain-profile --profile research
uv run pic agent communication-guide --profile development
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic alt negative-certify --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt refresh-baseline --certificate examples/alt/baseline_refresh_certificate.json
uv run pic alt check-cara --certificate examples/alt/alt_cara_certificate.json
uv run pic alt foundry-dashboard --state examples/alt/foundry_state.json
uv run pic agent message contract --message examples/agent_network/agent_message.json
uv run pic agent message ingest --message examples/agent_network/agent_message.json
uv run pic runtime health --state examples/runtime_state.json --profile development
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile development
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production --identity-context identity-context.json
```

Installed package smoke commands:

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
pic agent runbook --profile development
pic phase plan --compact --text "Candidate packet: preserve residuals." --profile development
pic agent accelerate --compact --text "Candidate packet: preserve residuals." --profile development
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
pic agent guide --profile development
pic agent intake --text "Candidate packet: preserve residuals." --profile development
pic snapshot list
pic schema --type AgentIntakeReport
```

GitHub Actions agent-output checker example:

- Inspect `docs/integrations/github-actions.md` before copying the workflow.
- The example lives at `examples/github_action_agent_output_check/pic-agent-output-check.yml`.
- It is read-only and artifact-only; do not use `pull_request_target`, write permissions, PR comments, live connectors, or shell execution of agent text in the minimal workflow.

## Integration Surfaces

Do not infer that PIC is GitHub Actions-only. GitHub Actions is one copyable CI
pattern. The fastest general entrypoint is still `pic agent intake`, and
programmatic integration should start with
`percolation_inversion_compiler.agent.run_agent_intake`.
For first-time humans, CI jobs, and first-time agents, run
`pic agent check --compact` before full intake. It emits the short practical
contract: `accepted`, `workflow_usable`, `settled`, unresolved obligations,
residual summary, next safe actions, schema refs, and safety invariants. Use
`pic agent runbook` when an agent needs deterministic command/schema/field
guidance without execution authority.
Use `pic phase plan --compact` or `pic agent accelerate --compact` after the
first check when the agent needs ranked phase gaps, bottlenecks, candidate-only
reasons, and promotion blockers. These commands return recommendation-only JSON
and do not execute routes, shells, network connectors, or repository mutation.
When using `pic phase plan --request`, treat the request file as the runtime
input source; do not also pass `--state`, `--input`, `--runtime-report`,
`--text`, or `--text-file`. `--profile` and `--identity-context` are explicit
operator overrides.

External intake, agent-to-agent message checks, and ALT foundry admission are
separate workflows from basic output checking. Start with
`docs/integrations/README.md`, then inspect
`examples/cli_agent_output_check/README.md`,
`examples/python_sdk_agent_output_check/README.md`, or
`examples/github_action_agent_output_check/README.md` depending on the
deployment surface.

Unix shell:

```sh
uv run pic --help
uv run pic agent explain
uv run pic agent guide --profile development
uv run pic agent readiness --profile production
uv run pic identity explain-profile --profile research
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic alt negative-certify --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt refresh-baseline --certificate examples/alt/baseline_refresh_certificate.json
uv run pic alt check-cara --certificate examples/alt/alt_cara_certificate.json
uv run pic alt foundry-dashboard --state examples/alt/foundry_state.json
uv run pic runtime health --state examples/runtime_state.json --profile development
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile development
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production --identity-context identity-context.json
```

## Python API Entrypoints

- `percolation_inversion_compiler.agent.run_agent_intake`
- `percolation_inversion_compiler.agent.accelerate_agent_phase`
- `percolation_inversion_compiler.acceleration.build_phase_acceleration_plan`
- `percolation_inversion_compiler.agent.build_agent_workflow_guide`
- `percolation_inversion_compiler.agent.agent_feature_readiness`
- `percolation_inversion_compiler.agent.recommend_agent_next_actions`
- `percolation_inversion_compiler.agent.build_agent_communication_guide`
- `percolation_inversion_compiler.agent.minimal_runtime_state`
- `percolation_inversion_compiler.agent.minimal_runtime_step_input`
- `percolation_inversion_compiler.runtime.build_runtime_step`
- `percolation_inversion_compiler.runtime.derive_runtime_identity_context`
- `percolation_inversion_compiler.runtime.runtime_health`
- `percolation_inversion_compiler.identity.sybil_policy_for_profile`
- `percolation_inversion_compiler.ecology.build_psi_dashboard`
- `percolation_inversion_compiler.ecology.ingest_general_source`
- `percolation_inversion_compiler.ecology.verify_agent_message`
- `percolation_inversion_compiler.alt.admit_alt_packet`
- `percolation_inversion_compiler.alt.check_liquidity_certificate`
- `percolation_inversion_compiler.alt.compute_foundry_dashboard`

## Safety Invariants

- Do not promote `declared_status` to evidence.
- Do not treat missing obligations as success.
- Do not treat `settled=false` as failure.
- Do not claim real ASI.
- Do not execute arbitrary shell commands.
- Preserve residual ledgers.
- Production profile requires stronger identity and packet issuer context.
- Accepted production identity context removes only identity-readiness blockers; it does not
  promote unresolved route, residual, or phase-gap work to `settled`.
- Keep live connectors bounded and candidate-only by default when an explicit source is supplied.
- Use `--no-allow-live-connectors` for local-only dry runs.
- For general intake, live HTTP(S) requires an explicit source and live-enabled intake/runtime
  policy. It never grants background crawling, shell execution, or downstream promotion.
- Treat web/feed/agent-message input as packet candidates, not verified packet capital.
- Treat ALT abstraction tokens as candidates until liquidity, transport, root, telemetry,
  lifecycle, and hazard checks pass.
- Treat negative ALT liquidity, deprecation, resurrection, baseline refresh, and reproduction
  reports as scoped lineage-preserving controls. They do not erase residual obligations or
  create real-world ASI evidence.
- Inspect `provenance`, `web_fetch_reports`, `residual_ledger`, `identity_verified`, and
  `nonce_ledger` before using external communication output downstream.
- Use `pic ecology bridge-runtime --report <report.json>` to classify external candidates into
  SQOT diagnostic/verifier/quarantine work. Raw external packet volume is not accepted ECPT
  phase progress.

## Full Feature Path

Use `uv run pic agent guide --profile development` to get the deterministic workflow. The fixed stage order is orient, inspect snapshots, run intake, derive identity context, external communication readiness, general web/feed intake, agent-to-agent packet exchange, live metadata ingest, verify evidence/routes, promote packets, run/store loop, inspect Psi/SQOT, ALT abstraction-liquidity admission, collective certify, and preserve residuals/provenance.

Use `uv run pic agent next --intake-report intake-report.json --profile production` after a runtime intake to decide which safe commands, SDK calls, schemas, and output fields to inspect next. These recommendations are not execution grants.

For networked workflows, run `uv run pic agent communication-guide --profile development`.
General intake supports local HTML, RSS/Atom, JSON feed, NDJSON, bounded HTTP(S), and
agent-message inboxes. Live web access is enabled for explicit sources by default and remains
candidate-only; use `--no-allow-live-connectors` for local-only dry runs. Production/adversarial
agent-message verification requires an accepted identity context; otherwise messages remain
diagnostic packet candidates.

## How To Patch This Repo

- Prefer small, schema-preserving changes.
- Add tests for new record fields, schema exports, and CLI outputs.
- Do not remove public schemas.
- Keep development mode usable without identity context.
- Keep production mode stricter but diagnostic and residual-preserving.

## v0.9 Agent Loop Addendum

Use `pic token extract-pipeline`, `pic token admissibility`, `pic trc
observation-window`, `pic trc resource-flow`, `pic performance report`, and
`pic cache invalidation` as finite local checks before handing work to CCR.
Token extraction is not settlement. Token admissibility is not capital
admission. Safe commands are hints, not authority. Cache hits are valid only
under schema, dependency, profile, authority, and hazard hashes.

For the smallest searchable cross-repo fixture set, use
`examples/asi_proxy_loop_bundle/`. It is local-only and non-executing.
