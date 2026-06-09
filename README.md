# Percolation Inversion Compiler

`percolation-inversion-compiler` is a production-oriented finite verifier-routing and ECPT collective phase runtime for AI agents. It compiles capability packet candidates, verifier evidence, semantic edge checks, SQOT salience queues, residual ledgers, and runtime events into deterministic JSON so agents can evaluate an **ASI-proxy collective phase** under declared protocols. ECPT phase progress here is collective packet percolation: it does not require self-rewriting, fine-tuning, or model-weight changes.

The abbreviations refer to the four source theories used by the repository: **ECPT** is Executable Capability Percolation Theory, the collective capability-packet phase model; **BIT** is Bottleneck Inversion Theory, the witness calculus for unlockable potential and frontier extraction; **TRC** is Typed Reality Compilation, the typed trace and tolerance-ledger compiler for cyber-physical frontiers; and **SQOT** is Salience-Queue Occupation Theory, the salience scheduling and attention-occupation layer.

Search terms: ECPT, BIT, TRC, SQOT, ASI-proxy collective phase, protocol-relative ASI-proxy phase-control, certificate compiler, proof obligations, residual ledgers, salience queue, packet ecology, semantic edge verification, typed trace normal forms, frontier extraction, AI agent integration, verifier SDK.

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
| 5 | **SQOT salience queue** | A priority schedule that preserves diagnostic reserve and quarantines stale, unsafe, or hash-invalid packets. |
| 6 | **Psi dashboard** | Protocol-relative collective phase components for availability, closure, execution paths, queues, hazards, and basin reachability. |
| 7 | **Bottleneck / phase tasks** | Ranked finite tasks for verifier routing, packet repair, edge construction, and phase-control planning. |
| 8 | **Action results** | Execution reports and route resolutions that are applied back into the runtime state. |
| 9 | **Runtime store** | Persistent event logs, verified packets, route batches, packet lineage, and residual ledgers. |
| 10 | **Collective phase certificate** | A fail-closed certificate over fixed population, no self-rewrite, no hidden injection, closure, execution availability, Psi thresholds, and resource-matched baseline. |

The runtime is fail-closed: planning can recommend finite ASI-proxy actions, but `settled` remains false unless scoped verifier rules discharge the required finite obligations. In production, signed identities and Sybil-resistance ledgers can prevent duplicate-key, clone-fanout, revoked, expired, or unsigned agent populations from producing accepted collective certificates. Residual external obligations remain explicit.

Core contract: registry is metadata, not evidence. Use `pic doctor` and structured checker outputs to distinguish declared status, finite certificate results, proof obligations, and residual ledgers.

## Quickstart

Install the development environment:

```powershell
uv sync --all-extras --dev
```

### 1. Inspect Bundled Theory Snapshots

Use this path when you do not have the canonical TeX sources locally.

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact ecpt
uv run pic snapshot show --artifact sqot
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
- Researchers studying ECPT, BIT, TRC, SQOT, finite certificate compilers, collective capability percolation, frontier extraction, and protocol-relative phase-control.
- Tool and runtime maintainers building portable Python, Rust, TypeScript, Go, Julia, or service-based implementations around stable JSON Schemas.

## Documentation Map

- Start here: [Overview](docs/00-overview.md), [Quickstart](docs/01-quickstart.md), [Tutorial](docs/tutorial.md)
- Runtime: [Runtime](docs/runtime.md), [Closed-loop runtime](docs/runtime-closed-loop.md), [Population runtime](docs/population-runtime.md), [Runtime service](docs/runtime-service.md), [Runtime executor](docs/runtime-executor.md), [Runtime store](docs/runtime-store.md)
- Collective phase: [Collective phase runtime](docs/collective-phase-runtime.md), [Collective phase certificate](docs/04-collective-phase-certificate.md), [No-self-rewrite ledger](docs/no-self-rewrite-ledger.md), [Safety boundary](docs/11-safety-boundary.md)
- Packet ecology: [Packet ecology runtime](docs/ecpt-packet-ecology-runtime.md), [Edge relation verifiers](docs/edge-relation-verifiers.md), [Packet promotion](docs/packet-promotion.md), [SQOT salience scheduler](docs/sqot.md)
- Verification and operations: [Identity and Sybil resistance](docs/identity-and-sybil-resistance.md), [External obligations](docs/external-obligations.md), [Verifier SDK](docs/verifier-sdk.md), [Production readiness](docs/production-readiness.md), [Provenance and SBOM](docs/provenance-and-sbom.md), [CLI reference](docs/cli-reference.md)
- Theory and portability: [Architecture](docs/architecture.md), [Mathematical contracts](docs/mathematical-contracts.md), [Theory coverage](docs/theory-coverage.md), [Porting guide](docs/porting.md), [Benchmarks](docs/benchmarks.md)
- Walkthrough: [Collective phase walkthrough](examples/walkthrough_collective_phase/README.md)

## Canonical Sources

Repository/software concept DOI: <https://doi.org/10.5281/zenodo.20569166>

- Takahashi, K. (2026). *Executable Capability Percolation Theory*. Zenodo. <https://doi.org/10.5281/zenodo.20535654>
- Takahashi, K. (2026). *Bottleneck Inversion Theory: Machine-Readable Witness Calculus for Unlockable Potential*. Zenodo. <https://doi.org/10.5281/zenodo.20545356>
- Takahashi, K. (2026). *Typed Reality Compilation: Operational Tolerance Allocation for Resource-Efficient Cyber-Physical Frontier Compilation*. Zenodo. <https://doi.org/10.5281/zenodo.20554083>
- Takahashi, K. (2026). *Salience-Queue Occupation Theory*. Zenodo. <https://doi.org/10.5281/zenodo.20526451>

## Development Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
```

## License

Code in this repository is licensed under Apache-2.0. The cited Zenodo papers are licensed CC-BY-4.0 by their publisher metadata and are not vendored here.
