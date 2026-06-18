# Percolation Inversion Compiler

`percolation-inversion-compiler` is an AI agent runtime for external knowledge intake, finite certificates, proof obligations, residual ledgers, and reusable abstraction capital. It helps agents turn web, repository, evidence, and agent-output inputs into checked capability packet candidates, verifier routes, SQOT salience queues, ALT abstraction-liquidity certificates, and ECPT collective capability phase reports. The goal is protocol-relative **ASI-proxy collective phase** acceleration through verified packet percolation, not self-rewrite, fine-tuning, or model-weight change.

The abbreviations refer to the five source theories used by the repository: **ECPT** is Executable Capability Percolation Theory, the collective capability-packet phase model; **BIT** is Bottleneck Inversion Theory, the witness calculus for unlockable potential and frontier extraction; **TRC** is Typed Reality Compilation, the typed trace and tolerance-ledger compiler for cyber-physical frontiers; **SQOT** is Salience-Queue Occupation Theory, the salience scheduling and attention-occupation layer; and **ALT** is Abstraction Liquidity Theory, the reusable abstraction capital and foundry valuation layer.

Search terms: ECPT, BIT, TRC, SQOT, ALT, abstraction liquidity, reusable abstraction capital, ASI-proxy collective phase, protocol-relative ASI-proxy phase-control, certificate compiler, proof obligations, residual ledgers, salience queue, packet ecology, semantic edge verification, typed trace normal forms, frontier extraction, AI agent integration, verifier SDK.

New to PIC? Start with the [GitHub Wiki](https://github.com/kadubon/percolation-inversion-compiler/wiki) for a plain-language guide to what PIC does, why AI agent output is treated as candidate work, getting started, use cases, core concepts, and agent-safe interpretation of `accepted=true` and `settled=false`.

Distribution status: v0.4.1 is a stable distribution snapshot with a beta API
surface. Install the core package from PyPI with `pip install
percolation-inversion-compiler`; use `pip install
"percolation-inversion-compiler[identity,connectors,server]"` when you need
cryptographic identity checks, explicit opt-in live intake, or the optional
local HTTP service. The PyPI package is intended for curated demo smoke checks,
bundled snapshots, schema export, library import, and basic CLI/runtime
verification. Clone the repository for full practical use: commands that
reference `examples/...`, canonical TeX audits, live development fixtures, and
release engineering require a source checkout.

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

The runtime is fail-closed: planning can recommend finite ASI-proxy actions, but `settled` remains false unless scoped verifier rules discharge the required finite obligations. In production, signed identities and Sybil-resistance ledgers can prevent duplicate-key, clone-fanout, revoked, expired, or unsigned agent populations from producing accepted collective certificates. Residual external obligations remain explicit.

v0.4.1 keeps ALT abstraction-liquidity foundry support so external knowledge and agent traces can become reusable abstraction-token candidates, then certified abstraction capital only after lower-bound surplus, transport, root-of-trust, telemetry, lifecycle, and hazard checks pass. ALT also adds negative-liquidity, deprecation/resurrection, baseline refresh, reproduction diagnostics, and ALT-CARA acceleration certificates so stale or unsafe abstraction claims remain repairable residual work rather than silent capital. Use `development`, `research`, `controlled`, `federated`, `production`, or `adversarial` profiles to choose how communication policy, cryptographic identities, homogeneous fleets, signed packet issuers, and Sybil-resistance ledgers affect packet promotion and collective certificates.

Core contract: registry is metadata, not evidence. Use `pic doctor` and structured checker outputs to distinguish declared status, finite certificate results, proof obligations, and residual ledgers.

## For AI Agents

Start with [AGENTS.md](AGENTS.md) and [For AI agents](docs/for-agents.md). The fastest safe route is:

```powershell
uv run pic agent explain
uv run pic agent guide --profile development
uv run pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
```

Production packet promotion requires identity context:

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text "Signed packet candidate." --profile production --identity-context identity-context.json
```

Residuals are expected and must be preserved. `settled=false` is not command failure; it means unresolved obligations remain explicit.

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

Start with [For AI agents](docs/for-agents.md). For the full integration map,
see [Integration Examples](docs/integrations/README.md). For the CI pattern, see
[GitHub Actions integration](docs/integrations/github-actions.md) and the
[copyable example workflow](examples/github_action_agent_output_check/README.md).

For networked collective-phase workflows, inspect the communication guide first. General web,
feed, and agent-to-agent intake are default-off for live network access; external content becomes
packet candidates only. Live intake requires three aligned opt-ins: the source/request flag,
the intake policy, and the runtime or service config. Reports preserve sanitized provenance
(`provenance`, `web_fetch_reports`, content SHA-256, redirect and robots/rate diagnostics)
without exposing local absolute paths, cookies, tokens, or query secrets.

```powershell
uv run pic agent communication-guide --profile development --no-allow-live-connectors
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic agent message contract --message examples/agent_network/agent_message.json
```

For production agent-to-agent messages, derive an accepted identity context first and pass it
to message verification. Without that context, signed messages remain diagnostic candidates.
Raw external packet volume, including candidate-only closure or execution-path records, does
not improve positive Psi components or collective certificates until downstream promotion checks
accept the packet as finite-scope capital.

## Quickstart

### Path A: Pip Install For Immediate Runtime Smoke

Use this when an agent has no source checkout and needs to verify the installed
package, inspect schemas/snapshots, or run the bundled curated demo.

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
```

### Path B: Clone For Full Practical Use

Use this when you want fixture-backed commands, `examples/...`, canonical-source
audits, full research workflows, release checks, or local development.

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
