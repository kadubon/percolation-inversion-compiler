# Quickstart

This page shows the shortest paths to useful deterministic JSON. Use PyPI for
practical agent-output checks, installed-package workflow checks, snapshots, and
schemas. Clone the repository when you need the root `examples/...` tree,
canonical-source audits, fixtures, or release checks.

## Agent Quickstart

Use this path when an autonomous agent or coding agent needs to orient itself and run a minimal residual-preserving intake without assembling runtime records manually.

After PyPI installation:

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent runbook --profile development
pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent accelerate --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent check --text "Candidate packet: route evidence and preserve residuals." --profile development
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic agent guide --profile development
pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
```

For source fixtures, canonical audits, and development checks, clone the source
checkout first:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
```

On macOS/Linux, install `uv` with:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If the standalone installer is unsuitable:

```powershell
python -m pip install uv
```

Then run source-checkout commands:

```powershell
uv run pic agent explain
uv run pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent runbook --profile development
uv run pic phase plan --compact --profile development
uv run pic phase runbook --profile development
uv run pic agent guide --profile development
uv run pic agent readiness --profile development
uv run pic agent doctor --profile development
uv run pic agent check --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
```

For production packet promotion, derive identity context first:

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text "Signed packet candidate." --profile production --identity-context identity-context.json
```

The intake output preserves `residual_ledger`, `missing_obligations`, and `settled=false` unless scoped finite verifier rules actually settle the relevant obligations.

To move from minimal intake to the full feature path, save the report and ask for next actions:

```powershell
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development --output intake-report.json
uv run pic agent next --intake-report intake-report.json --profile development
```

When the next question is “what should the agent verify or repair next?”, run:

```powershell
uv run pic phase plan --compact --profile development
uv run pic phase plan --request examples/phase_acceleration/phase_acceleration_request.json --compact
uv run pic agent accelerate --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
```

Read these phase planner fields first:

- `phase_gap_vector.limiting_components`
- `top_bottlenecks`
- `safe_commands`
- `cannot_promote_because`
- `candidate_only_reasons`
- `settled_blockers`

The planner is recommendation-only. It does not execute commands, promote
candidate packets, or prove real ASI or physical outcomes.
When using a `PhaseAccelerationRequest` file, pass it with `--request` and do
not combine it with `--state`, `--input`, `--runtime-report`, `--text`, or
`--text-file`. Production/adversarial runs need accepted identity context to
remove identity-readiness blockers, but `settled=false` remains correct while
route, residual, or phase-gap obligations remain.

## Phase Ecology Lab Quickstart

Use this path when the task is to compare local report windows, build an
effective packet graph, inspect closure/path diagnostics, or generate a
protocol-relative threshold certificate candidate:

```powershell
uv run pic phase lab init --output-dir pic-phase-lab
uv run pic phase lab ingest --store pic-phase-lab --report examples/phase_lab/runtime_report_1.json
uv run pic phase lab observe --store pic-phase-lab --window latest
uv run pic phase lab graph --store pic-phase-lab --output effective_graph.json
uv run pic phase lab closure --store pic-phase-lab
uv run pic phase lab executable-paths --store pic-phase-lab
uv run pic phase lab certify --store pic-phase-lab --threshold examples/thresholds/asi_proxy_development.json
uv run pic bit diagnose --graph effective_graph.json
uv run pic sqot diagnose-queue --graph effective_graph.json
uv run pic alt ecpt-lift --packets examples/packet_exchange/packet_envelope.example.json --graph effective_graph.json
uv run pic trc trace-adapter --input examples/trc_adapter/tool_trace_input.example.json
```

Phase Lab ingest treats report and packet files as inert data. The derived BIT,
SQOT, ALT lift, TRC, threshold, and certificate outputs are diagnostic and
preserve residual blockers; they do not execute packet content or make
`settled=true` claims by themselves.

## Networked Intake Quickstart

Use this path to inspect bounded live defaults and exercise broad intake and agent-to-agent
exchange with offline fixtures. Add `--no-allow-live-connectors` when a local-only dry run is
required:

```powershell
uv run pic agent communication-guide --profile development
uv run pic agent network-readiness --profile development
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic agent relay-readiness --profile development
uv run pic agent message send --inbox inbox.json --sender agent:alice --text "Candidate packet: preserve residuals."
uv run pic agent message receive --inbox inbox.json
uv run pic agent message ingest --message examples/agent_network/agent_message.json
```

Live HTTP(S), GitHub, Zenodo, and arXiv intake are allowed by default for explicit sources and
remain bounded/candidate-only. External content remains packet candidates until verifier,
semantic edge, identity, rollback, and residual policies pass.

## 1. Install

For PyPI runtime use:

```powershell
python -m pip install percolation-inversion-compiler
```

For the repository fixtures, tests, canonical-source audits, and release checks:

```powershell
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
```

## 2. Inspect Theory Snapshots

Snapshots are small derived metadata artifacts. They are not the canonical papers and they are not evidence, but they let a first-time user inspect available theory coverage and verifier routes.

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact ecpt
uv run pic snapshot show --artifact sqot
uv run pic snapshot show --artifact alt
uv run pic snapshot routes
```

ALT can be exercised without canonical TeX:

```powershell
uv run pic alt certify-liquidity --certificate examples/alt/liquidity_certificate.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic alt foundry-dashboard --state examples/alt/foundry_state.json
uv run pic alt negative-certify --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt check-cara --certificate examples/alt/alt_cara_certificate.json
```

The positive path tests lower-bound surplus, transport, root/finality,
telemetry, lifecycle, and hazard evidence. The negative path keeps stale or
unsafe tokens as scoped deprecation/resurrection work rather than silently
counting them as reusable capital.

## 3. Run One Runtime Step

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
```

Read these fields first:

- `accepted`: the JSON shape and finite checks did not reject the report.
- `operationally_usable`: the report can be used for routing under its profile.
- `settled`: remains false unless scoped verifier settlement rules discharge the required finite obligations.
- `missing_obligations`: obligations the agent must route or preserve.
- `residual_ledger`: debt that must not be hidden.
- `agent_tasks`: recommended next finite tasks.

## 4. Certify A Collective Phase Candidate

```powershell
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
```

The certificate is protocol-relative. Acceptance means the finite checks passed for the declared population, packet registry, basin, baseline, and threshold. It does not prove real ASI.

## 5. Check Signed Population Identity

Use this path when a production collective certificate should reject unsigned or Sybil-like populations.

```powershell
uv run pic identity verify --identity examples/identity/agent_identity_alice.json
uv run pic identity sybil-check --population examples/agent_population_signed.json
```

The result proves protocol-relative key control under the declared signature suite. It does not prove real-world legal identity or global uniqueness.

## 6. Run The Minimal Walkthrough

See [examples/walkthrough_collective_phase](../examples/walkthrough_collective_phase/README.md) for the same flow with command explanations.

## 7. Use Canonical TeX When Available

```powershell
$env:PIC_CANONICAL_TEX_DIR = "path\to\canonical\tex"
uv run pic check --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex" --canonical-key ecpt --strict-projection
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex" --canonical-key ecpt --strict-grammar
uv run pic audit canonical-suite --canonical-dir "$env:PIC_CANONICAL_TEX_DIR"
uv run pic audit fidelity --canonical-dir "$env:PIC_CANONICAL_TEX_DIR"
```

Canonical TeX is never vendored and is not required for installed-package
agent checking. Use local files or the DOI metadata workflow appropriate for
your environment when you need theory-fidelity audits and finite-upgrade
candidates.
