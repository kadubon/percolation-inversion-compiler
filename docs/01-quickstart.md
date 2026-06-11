# Quickstart

This page shows the shortest path from a fresh checkout to useful deterministic JSON. It does not require local TeX files.

## Agent Quickstart

Use this path when an autonomous agent or coding agent needs to orient itself and run a minimal residual-preserving intake without assembling runtime records manually.

```powershell
uv run pic agent explain
uv run pic agent guide --profile development
uv run pic agent readiness --profile development
uv run pic agent doctor --profile development
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

## Networked Intake Quickstart

Use this path before enabling live connectors. It exercises broad intake and agent-to-agent
exchange with offline fixtures:

```powershell
uv run pic agent communication-guide --profile development --no-allow-live-connectors
uv run pic agent network-readiness --profile development --no-allow-live-connectors
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic agent message ingest --message examples/agent_network/agent_message.json
```

Live HTTP(S), GitHub, Zenodo, and arXiv intake require `--allow-live-connectors`.
External content remains packet candidates until verifier, semantic edge, identity, rollback,
and residual policies pass.

## 1. Install

```powershell
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
```

Canonical TeX is never vendored. Use local files or the DOI metadata workflow appropriate for your environment.
