# Agent Instructions

## Repository Purpose

This repository is an AI agent runtime verification and ECPT collective phase acceleration module. It manages capability packets, evidence, verifier routes, residual ledgers, SQOT queues, ALT abstraction-liquidity certificates, identity/Sybil checks, and collective phase certificates.

It is not an ASI detector, a real ASI proof system, or a self-modifying AI system. It does not require self-rewrite, fine-tuning, or model-weight changes.

v0.4.1 is the PyPI distribution snapshot with a beta API surface. The PyPI
package is enough for `pic agent explain`, `pic demo installed-smoke`,
`pic demo bootstrap`, `pic agent intake --text "..."`, `pic snapshot list`, and
`pic schema --all --output-dir schemas`. Full practical use is clone
recommended: commands that reference the root `examples/...` tree, canonical
TeX audits, development fixtures, and release engineering checks require this
repository checkout.

## Install Modes

Installed package path:

```powershell
python -m pip install percolation-inversion-compiler
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
uv run pic agent guide --profile development
uv run pic agent readiness --profile production
uv run pic identity explain-profile --profile research
uv run pic agent communication-guide --profile development --no-allow-live-connectors
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
- Keep live connectors disabled unless both request and runtime config explicitly opt in.
- For general intake, live HTTP(S) requires source/request, intake policy, and runtime/service
  config to opt in; one true flag is not enough.
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

For networked workflows, run `uv run pic agent communication-guide --profile development --no-allow-live-connectors` before enabling live connectors. General intake supports local HTML, RSS/Atom, JSON feed, NDJSON, bounded HTTP(S), and agent-message inboxes. Live web access remains explicit opt-in and fail-closed. Production/adversarial agent-message verification requires an accepted identity context; otherwise messages remain diagnostic packet candidates.

## How To Patch This Repo

- Prefer small, schema-preserving changes.
- Add tests for new record fields, schema exports, and CLI outputs.
- Do not remove public schemas.
- Keep development mode usable without identity context.
- Keep production mode stricter but diagnostic and residual-preserving.
