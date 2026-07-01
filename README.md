# Percolation Inversion Compiler

`percolation-inversion-compiler` is an AI agent runtime for external knowledge intake, finite certificates, proof obligations, residual ledgers, and reusable abstraction capital. It helps agents turn web, repository, evidence, and agent-output inputs into checked capability packet candidates, verifier routes, SQOT salience queues, ALT abstraction-liquidity certificates, and ECPT collective capability phase reports. The goal is protocol-relative **ASI-proxy collective phase** acceleration through verified packet percolation, not self-rewrite, fine-tuning, or model-weight change.

The abbreviations refer to the five source theories used by the repository: **ECPT** is Executable Capability Percolation Theory, the collective capability-packet phase model; **BIT** is Bottleneck Inversion Theory, the witness calculus for unlockable potential and frontier extraction; **TRC** is Typed Reality Compilation, the typed trace and tolerance-ledger compiler for cyber-physical frontiers; **SQOT** is Salience-Queue Occupation Theory, the salience scheduling and attention-occupation layer; and **ALT** is Abstraction Liquidity Theory, the reusable abstraction capital and foundry valuation layer.

Search terms: ECPT, BIT, TRC, SQOT, ALT, abstraction liquidity, reusable abstraction capital, ASI-proxy collective phase, protocol-relative ASI-proxy phase-control, phase acceleration planner, bottleneck ranking, certificate compiler, proof obligations, residual ledgers, salience queue, packet ecology, semantic edge verification, typed trace normal forms, frontier extraction, AI agent integration, verifier SDK, Collective Capability Runtime, CCR, multi-agent runtime, task leasing, blackboard events, provider import.

New to PIC? Start with the [GitHub Wiki](https://github.com/kadubon/percolation-inversion-compiler/wiki) for a plain-language guide to what PIC does, why AI agent output is treated as candidate work, getting started, use cases, core concepts, and agent-safe interpretation of `accepted=true` and `settled=false`.

Related OSS: [Collective Capability Runtime](https://github.com/kadubon/collective-capability-runtime) is the companion open-source Python runtime for coordinating multi-agent tasks, leases, blackboard events, packet distillation, provider imports, residual tracking, and release audits. Use PIC when you need packet-level checks, verifier routing, schemas, Phase Ecology Lab diagnostics, or protocol-relative certificate candidates. Use CCR when you need an auditable local runtime that coordinates many agents and can import PIC-compatible reports without treating them as automatic settlement or execution authority.

Distribution status: v0.7.0 is a practical runtime snapshot with a beta API
surface. Install the core package from PyPI with `pip install
percolation-inversion-compiler`; use `pip install
"percolation-inversion-compiler[identity,connectors,server]"` when you need
cryptographic identity checks, live HTTP/feed intake, or the optional
local HTTP service. The PyPI package is intended for practical agent output checking,
bundled snapshots, schema export, library import, curated installed workflows,
and CLI/runtime verification. Clone the repository for canonical TeX audits,
commands that reference the root `examples/...` tree, live development
fixtures, and release engineering.

Common-language glossary: capability packet = checked reusable work item;
residual ledger = explicit unresolved-work ledger; SQOT = finite attention/task
scheduler; ALT = reusable abstraction value checker; ECPT = workflow graph and
collective phase-control model; BIT = bottleneck/witness calculus; TRC = typed
trace and real-world frontier compiler; phase acceleration planner = ranked
safe next-step planner for verified work reuse and bottleneck removal. See
[Glossary](docs/glossary.md).

## What It Does Not Do

- It does not prove real ASI, physical, simulator, oracle, or policy outcomes.
- It does not execute unsafe actions or grant authority to mutate repositories, shells, networks, or models.
- It does not require or model self-rewrite, fine-tuning, or model-weight updates.
- It does not treat a declared `agent_id` as proof of identity or global uniqueness.
- It does not treat registry metadata, declared status, queue priority, or agent text as evidence.
- It does not silently promote unresolved external obligations to `settled`.

## Core Workflow

| Step | Runtime object | What the agent gets |
| --- | --- | --- |
| 1 | **Fixed agent population** | A declared population, policy digest, model digest, route allowlist, optional cryptographic identity attestations, Sybil-resistance ledger, and no-self-rewrite ledger. |
| 2 | **Packet candidates** | Finite capability packets from agent output, local files, fixtures, repositories, or verifier evidence. |
| 3 | **Evidence + semantic edge checks** | Hash/provenance checks and typed relations such as theorem-to-code, code-to-test, rollback-support, and execution-path. |
| 4 | **Verified packet capital** | Reusable packets promoted only after route, receiver, rollback, authority, edge, and residual policies pass. |
| 5 | **ALT abstraction liquidity** | Trace and external-intake candidates become reusable abstraction capital only after certified lower-bound surplus, transport, root-of-trust, telemetry, lifecycle, and hazard checks pass. |
| 6 | **SQOT salience queue** | A priority schedule that preserves diagnostic reserve and quarantines stale, unsafe, uncertified, or hash-invalid packets. |
| 7 | **Psi dashboard** | Protocol-relative collective phase components for availability, closure, execution paths, queues, hazards, liquidity, and basin reachability. |
| 8 | **Bottleneck / phase tasks** | Ranked finite tasks for verifier routing, packet repair, edge construction, abstraction certification, and phase-control planning. |
| 9 | **Action results** | Execution reports, ALT admission decisions, and route resolutions that are applied back into the runtime state. |
| 10 | **Runtime store** | Persistent event logs, verified packets, route batches, abstraction capital lineage, and residual ledgers. |
| 11 | **Collective phase certificate** | A fail-closed certificate over fixed population, no self-rewrite, no hidden injection, closure, execution availability, Psi thresholds, certified liquidity, and resource-matched baseline. |
| 12 | **Phase acceleration plan** | Recommendation-only JSON that ranks phase gaps, bottlenecks, safe commands, schemas, candidate-only reasons, and settlement blockers. |

The runtime is fail-closed: planning can recommend finite ASI-proxy actions, but `settled` remains false unless scoped verifier rules discharge the required finite obligations. In production, signed identities and Sybil-resistance ledgers can prevent duplicate-key, clone-fanout, revoked, expired, or unsigned agent populations from producing accepted collective certificates. Residual external obligations remain explicit.

v0.7.0 adds CCR-oriented interop and TRC operation gate checks: agents can
normalize traces, check finite operation blockers, emit packet candidates, export
phase/BIT/SQOT/ALT residual work to CCR, and run a local PIC-to-CCR benchmark
bundle without treating candidate plans as execution authority. It also blocks
expired or fixture-only authority envelopes from operation readiness and
separates ALT `accepted` from `capital_admitted`.

v0.5.0 adds the Phase Ecology Lab for windowed multi-packet diagnostics: effective packet graphs, closure, execution-available paths, BIT bottleneck inversion, SQOT queue obstruction, ALT-to-ECPT lift, TRC typed trace adapters, and threshold/certificate candidates. These surfaces are diagnostic, non-executing, protocol-relative, and residual-preserving.

For the v0.6.0 contract audit, OS-independent pip notes, and residual obligation boundary, see [docs/v060-audit.md](docs/v060-audit.md).

v0.5.0 preserves the v0.4.4 ALT abstraction-liquidity foundry support so external knowledge and agent traces can become reusable abstraction-token candidates, then certified abstraction capital only after lower-bound surplus, calibrated proxy or causal value evidence, transport, root-of-trust, telemetry, lifecycle, and hazard checks pass. ALT also adds negative-liquidity, deprecation/resurrection, baseline refresh, reproduction diagnostics, and ALT-CARA acceleration certificates so stale or unsafe abstraction claims remain repairable residual work rather than silent capital. Use `development`, `research`, `controlled`, `federated`, `production`, or `adversarial` profiles to choose how communication policy, cryptographic identities, homogeneous fleets, signed packet issuers, and Sybil-resistance ledgers affect packet promotion and collective certificates.

Core contract: registry is metadata, not evidence. Use `pic doctor` and structured checker outputs to distinguish declared status, finite certificate results, proof obligations, and residual ledgers.

The intended ASI-proxy effect is operational: many agents repeatedly exchange
bounded candidate work, preserve residuals, verify reusable packets, and route
bottlenecks through finite checks. PIC can make that networked workflow
machine-readable and auditable; it does not guarantee that a real ASI phase,
physical event, or oracle-truth transition has occurred.

## For AI Agents

Start with [AGENTS.md](AGENTS.md) and [For AI agents](docs/for-agents.md). The fastest safe route is:

```powershell
uv run pic agent explain
uv run pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent runbook --profile development
uv run pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent accelerate --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent guide --profile development
uv run pic agent check --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic phase lab init --output-dir pic-phase-lab
uv run pic phase lab ingest --store pic-phase-lab --report examples/phase_lab/runtime_report_1.json
uv run pic phase lab observe --store pic-phase-lab --window latest
uv run pic phase lab graph --store pic-phase-lab
uv run pic phase lab closure --store pic-phase-lab
uv run pic phase lab executable-paths --store pic-phase-lab
uv run pic phase lab certify --store pic-phase-lab --threshold examples/thresholds/asi_proxy_development.json
```

## Optional Sidecars

These commands help operators, maintainers, and agent frameworks inspect PIC
adoption, canonical implementation readiness, packet exchange, benchmarks, and
phase metrics. They do not gate the main workflow and do not change `settled`
semantics.

```powershell
pic adoption request --format markdown
pic adoption packet --format markdown
pic audit canonical-readiness --profile development --format json
pic phase benchmark-suite --profile development --format json
pic packet inspect --packet packet.json
pic phase dashboard --profile development --format json
pic phase lab graph --store pic-phase-lab --output effective_graph.json
pic bit diagnose --graph effective_graph.json
pic sqot diagnose-queue --graph effective_graph.json
pic trc trace-adapter --input examples/trc_adapter/tool_trace_input.example.json
pic trc operation-gate --trace trace_nf.json --provider-profile provider_profile.json
```

Command choice:

- Use `pic agent check --compact` when a human, CI job, or first-time agent needs the shortest practical JSON contract.
- Use `pic agent runbook` when an agent needs deterministic next commands, schemas, and fields to inspect.
- Use `pic phase plan --compact` or `pic agent accelerate --compact` when an agent needs ranked phase gaps, bottlenecks, safe next commands, and promotion blockers.
- Use `pic trc operation-gate` when an agent needs a non-executing TRC preflight with authority freshness, side-effect, provider-dispatch, and physical-dispatch gates.
- Use `pic agent intake` or `pic runtime step` when the caller needs the full nested runtime report.
- Use `pic audit canonical-readiness` from pip when an agent needs canonical ECPT/BIT/TRC/SQOT/ALT implementation coverage without local TeX files.
- Use `pic audit fidelity` from a source checkout when canonical TeX theory-fidelity and finite-upgrade candidates matter.

Production packet promotion requires identity context:

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text "Signed packet candidate." --profile production --identity-context identity-context.json
```

Residuals are expected and must be preserved. `settled=false` is not command failure; it means unresolved obligations remain explicit.

TRC operation reports are diagnostic by default. `operation_ready=true` is not
execution, `provider_dispatch_ready=true` is not dispatch, and
`physical_dispatch_ready=true` is not physical outcome proof. Expired or
fixture-only authority envelopes, including
`expires_at: 1970-01-01T00:00:00Z`, block operation readiness unless explicitly
represented as a dry-run fixture, and dry-run fixtures remain non-executable. ALT bridge
reports also distinguish `accepted` from `capital_admitted`; proxy-only or
negative evidence can be accepted as a report while contributing no safe capital.

## Integration Examples

PIC is not limited to GitHub Actions. It is a general AI agent output checker
that can be used as a local CLI tool, a Python SDK, a read-only CI checker, a
local runtime service, an external knowledge intake layer, an agent-to-agent
message checker, or an ALT abstraction-capital foundry.

- CLI: run `pic agent intake` on AI-generated text before reuse.
- Python SDK: call `run_agent_intake` inside an agent runtime.
- GitHub Actions: copy a read-only workflow that uploads a residual-preserving JSON artifact.
- Runtime service: expose local-first runtime checks through the optional service layer.
- External intake: treat web, feed, repository, and message inputs as candidate packets.
- Agent-to-agent messages: inspect signatures, nonces, identity context, and residuals.
- ALT foundry: check whether traces or outputs can become reusable abstraction capital.
- Phase acceleration planner: rank finite bottlenecks and safe next actions without executing them.

Start with [For AI agents](docs/for-agents.md). For the full integration map,
see [Integration Examples](docs/integrations/README.md). For the CI pattern, see
[GitHub Actions integration](docs/integrations/github-actions.md) and the
[copyable example workflow](examples/github_action_agent_output_check/README.md).

For networked collective-phase workflows, inspect the communication guide first. General web,
feed, and agent-to-agent intake are live-capable by default when an explicit source is supplied;
external content becomes packet candidates only. Use `--no-allow-live-connectors` for local-only
dry runs. Reports preserve sanitized provenance
(`provenance`, `web_fetch_reports`, content SHA-256, redirect and robots/rate diagnostics)
without exposing local absolute paths, cookies, tokens, or query secrets.

```powershell
uv run pic agent communication-guide --profile development
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic agent message contract --message examples/agent_network/agent_message.json
uv run pic agent message send --inbox inbox.json --sender agent:alice --text "Candidate packet: preserve residuals."
uv run pic agent message receive --inbox inbox.json
```

For production agent-to-agent messages, derive an accepted identity context first and pass it
to message verification. Without that context, signed messages remain diagnostic candidates.
Raw external packet volume, including candidate-only closure or execution-path records, does
not improve positive Psi components or collective certificates until downstream promotion checks
accept the packet as finite-scope capital.

## Phase Acceleration Planner

The phase planner is the practical bridge from the theory reports to agent
action. It reads existing runtime output and adjacent ALT/SQOT/external-intake
reports, then returns a deterministic `PhaseAccelerationPlan` with:

- `phase_gap_vector`: finite Psi component gaps against thresholds.
- `bottlenecks`: ranked verifier, packet repair, SQOT queue, ALT capital, identity, and residual-ledger work.
- `safe_commands` and `sdk_calls`: next commands and APIs to inspect, not authority to execute.
- `cannot_promote_because`, `candidate_only_reasons`, and `settled_blockers`: why the current state is useful but not settled.

```powershell
uv run pic phase plan --compact --profile development
uv run pic phase plan --request examples/phase_acceleration/phase_acceleration_request.json --compact
uv run pic phase gap --compact --profile development
uv run pic phase runbook --profile development
uv run pic phase benchmark --profile development
uv run pic phase benchmark-suite --profile development --format json
uv run pic phase dashboard --profile development --format json
uv run pic schema --type PhaseAccelerationPlan
```

For first-time agents, `pic agent check --compact` is still the first command.
Run `pic phase plan --compact` next when the agent must choose finite bottleneck
work. The planner can help a network of agents preserve reusable work and route
verification, but it does not prove real ASI, physical outcomes, or oracle truth.
With `--request`, use a self-contained `PhaseAccelerationRequest` file and do
not also pass `--state`, `--input`, `--runtime-report`, `--text`, or
`--text-file`; `--profile` and `--identity-context` are explicit operator
overrides. In production/adversarial profiles, accepted identity context removes
only the identity-readiness blocker. `settled=false` remains correct while
residual obligations, route work, or phase gaps remain.

## Quickstart

### Path A: Pip Install For Immediate Practical Checks

Use this when an agent has no source checkout and needs to verify the installed
package, check agent output, inspect schemas/snapshots, or run the bundled
curated workflow.

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic agent autonomy-audit --profile development --format json
pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent runbook --profile development
pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent accelerate --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent check --text "Candidate packet: route evidence and preserve residuals." --profile development
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
pic phase benchmark-suite --profile development --format json
pic phase dashboard --runtime-report pic-demo/runtime_step_report.json --profile development
pic packet inspect --packet pic-demo/packet_envelope.json
pic packet merge --packets pic-demo/packet_envelope.json --output pic-demo/merged-packets.json
pic packet lineage --packet pic-demo/merged-packets.json
pic phase observe --reports pic-demo/phase_dashboard.json --output pic-demo/observation.json
pic audit canonical-readiness --profile development --format json
```

For connector, identity, and local runtime-service dependencies without the
science/OT/LP research stack:

```powershell
python -m pip install "percolation-inversion-compiler[agent-full]"
pic agent network-readiness --profile development
pic agent communication-guide --profile development
```

### Path B: Clone For Canonical Audits And Development

Use this when you want fixture-backed commands, `examples/...`,
canonical-source audits, full research workflows, release checks, or local
development.

Install `uv` if it is not already available. Official install commands:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If the standalone installer is not suitable, use the PyPI fallback:

```powershell
python -m pip install uv
```

Then clone and sync the full repository:

```powershell
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
```

After cloning, use `uv run pic ...` for commands that reference `examples/...`.

### 1. Inspect Bundled Theory Snapshots

Use this path when you do not have the canonical TeX sources locally.

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact ecpt
uv run pic snapshot show --artifact sqot
uv run pic snapshot show --artifact alt
uv run pic snapshot routes
uv run pic audit canonical-readiness --profile development --format json
```

### 2. Run One Runtime Step

This produces packet ingestion, SQOT scheduling, Psi components, bottleneck tasks, missing obligations, and residual ledgers.

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
```

### 3. Certify A Collective Phase Candidate

This checks fixed population, no self-rewrite, no hidden capability injection, accepted closure witnesses, execution-available paths, Psi thresholds, SQOT reserve, hazard/authority checks, and resource-matched baseline conditions.

```powershell
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
```

For a complete command inventory, see [CLI reference](docs/cli-reference.md).

## Who Should Use This?

- AI agent integrators who need deterministic JSON for verifier routing, packet promotion, residual-ledger preservation, and fail-closed runtime loops.
- Researchers studying ECPT, BIT, TRC, SQOT, ALT, finite certificate compilers, abstraction liquidity, collective capability percolation, frontier extraction, and protocol-relative phase-control.
- Tool and runtime maintainers building portable Python, Rust, TypeScript, Go, Julia, or service-based implementations around stable JSON Schemas.

## Documentation Map

- Start here: [Overview](docs/00-overview.md), [Quickstart](docs/01-quickstart.md), [For AI agents](docs/for-agents.md), [Agent external communication](docs/agent-external-communication.md), [Tutorial](docs/tutorial.md)
- Runtime: [Runtime](docs/runtime.md), [Closed-loop runtime](docs/runtime-closed-loop.md), [Population runtime](docs/population-runtime.md), [Runtime service](docs/runtime-service.md), [Runtime executor](docs/runtime-executor.md), [Runtime store](docs/runtime-store.md)
- Collective phase: [Collective phase runtime](docs/collective-phase-runtime.md), [Collective phase certificate](docs/04-collective-phase-certificate.md), [No-self-rewrite ledger](docs/no-self-rewrite-ledger.md), [Safety boundary](docs/11-safety-boundary.md)
- Packet ecology: [Packet ecology runtime](docs/ecpt-packet-ecology-runtime.md), [Edge relation verifiers](docs/edge-relation-verifiers.md), [Packet promotion](docs/packet-promotion.md), [SQOT salience scheduler](docs/sqot.md), [ALT abstraction liquidity](docs/alt.md)
- Verification and operations: [Identity and Sybil resistance](docs/identity-and-sybil-resistance.md), [External obligations](docs/external-obligations.md), [Verifier SDK](docs/verifier-sdk.md), [Production readiness](docs/production-readiness.md), [PyPI distribution](docs/pypi-distribution.md), [Provenance and SBOM](docs/provenance-and-sbom.md), [CLI reference](docs/cli-reference.md)
- Theory and portability: [Architecture](docs/architecture.md), [Mathematical contracts](docs/mathematical-contracts.md), [Theory coverage](docs/theory-coverage.md), [Porting guide](docs/porting.md), [Benchmarks](docs/benchmarks.md)
- Walkthrough: [Collective phase walkthrough](examples/walkthrough_collective_phase/README.md)

## Canonical Sources

Repository/software concept DOI: <https://doi.org/10.5281/zenodo.20569166>

- Takahashi, K. (2026). *Executable Capability Percolation Theory*. Zenodo. <https://doi.org/10.5281/zenodo.20535654>
- Takahashi, K. (2026). *Bottleneck Inversion Theory: Machine-Readable Witness Calculus for Unlockable Potential*. Zenodo. <https://doi.org/10.5281/zenodo.20545356>
- Takahashi, K. (2026). *Typed Reality Compilation: Operational Tolerance Allocation for Resource-Efficient Cyber-Physical Frontier Compilation*. Zenodo. <https://doi.org/10.5281/zenodo.20554083>
- Takahashi, K. (2026). *Salience-Queue Occupation Theory*. Zenodo. <https://doi.org/10.5281/zenodo.20526451>
- Takahashi, K. (2026). *Abstraction Liquidity Theory*. Zenodo. <https://doi.org/10.5281/zenodo.20476200>

## Development Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
```

## License

Code in this repository is licensed under Apache-2.0. The cited Zenodo papers are licensed CC-BY-4.0 by their publisher metadata and are not vendored here.
