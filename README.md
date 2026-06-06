# Percolation Inversion Compiler

`percolation-inversion-compiler` is an ECPT active agent runtime and
production-oriented finite verifier-routing SDK for ECPT, BIT, TRC, and SQOT.
It turns paper-derived TeX, registry JSON, verifier evidence, agent outputs,
and packet candidate records into deterministic JSON: finite checker judgments,
proof obligations, residual ledgers, salience-queue schedules, typed trace
normal forms, frontier extraction records, packet edge witnesses, Psi
dashboards, bottleneck-inversion plans, runtime step reports, provenance
manifests, SBOMs, and portable JSON Schemas for AI agent integration.

In practical terms, the input is a finite artifact an agent may want to use: a
canonical theory source, packet candidate, issue/PR/repository metadata, agent
work product, trace, or verifier evidence envelope. The output answers five
questions: which finite certificates passed, which proof obligations remain,
which residual coordinates stay charged, which packets/obligations should be
scheduled next, and which ECPT ASI-proxy component is currently the bottleneck.
Agents can use that output as a routing layer before they call domain
simulators, frontier planners, live connectors, verifier adapters, or the
optional local runtime HTTP service.

The repository is not an ASI detector and does not assert that artificial
superintelligence has been achieved. Its narrower scientific role is to provide
a protocol-relative ASI-proxy phase-control toolkit: agents can ask which finite
certificates are accepted, which claims still need external evidence, and which
residual costs remain charged rather than hidden.

The three papers play complementary roles:

- ECPT models protocol-relative capability propagation, activation, queues,
  capacity, viability, and phase-control certificates. The active runtime ranks
  finite interventions and packet-edge construction steps for ASI-proxy targets.
- BIT supplies a witness calculus for unlockable potential: unit functors,
  stopped evidence sheaves, martingale deficiency audits, release duality,
  mechanism cubes, and certificate compiler graphs.
- TRC compiles cyber-physical observations into typed executable traces,
  tolerance/resource ledgers, risk gates, and frontier archives.
- SQOT models finite salience and attention-queue occupation: diagnostic
  reserve, quarantine/rollback, risk and verification-cost ledgers, safe
  ignorance, checker routes, and priority distortion under constrained
  operational budgets.

The implementation rule is strict: a registry is metadata, not evidence.
Registry entries must be projections of extractor/checker judgments. Declared
status is kept separate from checker-derived status, and no claim is promoted to
`settled` without the required certificate route. Non-finite theorem clauses,
external simulators, physical-domain witnesses, oracle claims, and unobserved
ASI claims remain explicit `ExternalProofObligation` records with residual
charges and failure modes.

Three direct ways to use it:

- Use as CLI: run `pic runtime step`, `pic runtime loop`, `pic ecpt plan`,
  `pic sqot schedule`, `pic ecology psi`, and `pic evidence verify`.
- Use as Python SDK: call `build_runtime_step`, `run_runtime_loop`, and
  `runtime_health` with portable `RuntimeState` and `RuntimeStepInput` JSON.
- Run local HTTP service: start `pic runtime service --host 127.0.0.1 --port
  8765 --profile production` and call `/runtime/step`, `/runtime/loop`,
  `/ecology/ingest`, `/evidence/verify`, and `/health`.
  In production set `PIC_RUNTIME_TOKEN` and use `Authorization: Bearer ...`.

What this gives an agent:

- a certificate compiler for ECPT/BIT/TRC artifacts;
- proof obligation and residual ledger records suitable for planning logs;
- typed trace normal forms and trace-normal-form checks for TRC frontiers;
- frontier extraction and audit reports for protocol-relative claims;
- fail-closed production readiness checks for external verifier routing;
- active ECPT ASI-proxy phase-control plans with ranked finite interventions;
- ECPT packet ecology ingestion, edge witnesses, Psi dashboards, and bottleneck plans;
- SQOT salience scheduling for packet, obligation, and verifier queues;
- an ECPT active runtime that composes packet ecology, SQOT scheduling,
  bottleneck planning, verifier routing, and residual ledger preservation;
- a finite `phase_acceleration_score` for ranking ASI-proxy phase-control
  actions under explicit evidence and residual policies;
- SHA-256 evidence provenance envelopes for verifier adapters;
- canonical-to-implementation discharge route bindings with settlement scope;
- deterministic schema/provenance manifests and SBOM-ready release assets;
- derived non-vendored snapshots for users who do not have the TeX sources;
- schema bundles for ports to Rust, TypeScript, Julia, Go, or other runtimes.

What it does not give an agent:

- automatic proof of unobserved physical or ASI claims;
- permission to treat `declared_status` as evidence;
- silent conversion of external simulator/oracle output into `settled` status.

Canonical sources:

- Takahashi, K. (2026). *Executable Capability Percolation Theory*. Zenodo.
  <https://doi.org/10.5281/zenodo.20535654>
- Takahashi, K. (2026). *Bottleneck Inversion Theory: Machine-Readable Witness
  Calculus for Unlockable Potential*. Zenodo.
  <https://doi.org/10.5281/zenodo.20545356>
- Takahashi, K. (2026). *Typed Reality Compilation: Operational Tolerance
  Allocation for Resource-Efficient Cyber-Physical Frontier Compilation*. Zenodo.
  <https://doi.org/10.5281/zenodo.20554083>
- Takahashi, K. (2026). *Salience-Queue Occupation Theory*. Zenodo.
  <https://doi.org/10.5281/zenodo.20526451>

## Install

```powershell
uv sync --all-extras --dev
```

## CLI

TeX-free quickstart:

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact sqot
uv run pic snapshot show --artifact trc
uv run pic snapshot routes
uv run pic routes bindings
uv run pic ecpt plan --state examples/ecpt_phase_control_state.json --target examples/ecpt_asi_proxy_target.json --budget examples/ecpt_phase_control_budget.json --profile production
uv run pic ecpt simulate --state examples/ecpt_phase_control_state.json --actions examples/ecpt_phase_control_actions.json
uv run pic sqot schedule --packets examples/sqot_queue.json --profile production
uv run pic ecology build-edges --packets examples/ecology_packets.json --output ecology-registry.json
uv run pic ecology psi --registry ecology-registry.json --threshold examples/ecology_threshold.json --output ecology-psi.json
uv run pic ecology plan --registry ecology-registry.json --psi ecology-psi.json --profile production
uv run pic ecology loop --state examples/ecology_loop_state.json --agent-output "SQOT reserve packet for ECPT active phase-control."
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
uv run pic runtime loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --max-steps 2 --profile production
uv run pic runtime health --state examples/runtime_state.json --profile production
uv run pic runtime export-openapi --output runtime-openapi.json
uv run pic explain external def:null-channel-routing --from-snapshot
uv run pic snapshot verify --artifact trc
uv run pic snapshot verify --artifact sqot
uv run pic evidence verify --envelope examples/evidence_envelope.json
uv run pic evidence verify --envelope examples/evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples/evidence_envelope.json --obligations examples/external_obligations.json --profile production
uv run pic routes explain --route adapters.domain.verify_trc_telemetry_calibration
uv run pic doctor --fail-on never
uv run pic doctor --profile production --fail-on never
uv run pic demo datacenter
```

Canonical TeX audit:

```powershell
$env:PIC_CANONICAL_TEX_DIR = "path\to\canonical\tex"
uv run pic extract --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex"
uv run pic check --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex" --canonical-key ecpt --strict-projection
uv run pic validate --registry registry.json
uv run pic coverage --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex"
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --canonical-key trc
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --canonical-key trc --strict-grammar
uv run pic parse audit --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --strict-grammar
uv run pic sqot audit --source "$env:PIC_CANONICAL_TEX_DIR\Salience-Queue Occupation Theory.tex" --strict-grammar
uv run pic schema --type TheoryAuditReport
uv run pic schema --all --output-dir schemas
uv run pic check --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --strict-projection --derive-status
uv run pic demo datacenter
uv run pic explain coverage def:null-channel-routing
uv run pic explain external def:null-channel-routing
uv run pic explain ecpt
```

Agent connector path:

```powershell
uv run pic schema --all --output-dir schemas
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
uv run pic doctor --profile production --provenance provenance.json --fail-on fail
uv run pic snapshot routes
uv run pic routes bindings
uv run pic routes explain --route adapters.domain.verify_trc_telemetry_calibration
uv run pic routes explain --route ecpt.adapters.proxy.verify_target_contract
uv run pic ecpt plan --state examples\ecpt_phase_control_state.json --target examples\ecpt_asi_proxy_target.json --budget examples\ecpt_phase_control_budget.json --profile production
uv run pic sqot schedule --packets examples\sqot_queue.json --profile production
uv run pic ecology build-edges --packets examples\ecology_packets.json --output ecology-registry.json
uv run pic ecology psi --registry ecology-registry.json --threshold examples\ecology_threshold.json --output ecology-psi.json
uv run pic ecology plan --registry ecology-registry.json --psi ecology-psi.json --profile production
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --provenance provenance.json --fail-on fail
uv run pic doctor --fail-on warn
uv run pic evidence verify --envelope examples\evidence_envelope.json --profile production
uv run pic validate --registry examples\minimal_registry.json
uv run pic runtime step --state examples\runtime_state.json --input examples\runtime_step_input.json --profile production
uv run pic runtime loop --state examples\runtime_state.json --inputs examples\runtime_loop_inputs.jsonl --max-steps 2 --profile production
uv run pic runtime service --host 127.0.0.1 --port 8765 --profile production
uv run pic compile --records examples\frontier_records.json
uv run pic sbom create --format cyclonedx --output cyclonedx.sbom.json
```

For fixture-only smoke tests:

```powershell
uv run pic check --source tests\fixtures\minimal_claims.tex --strict-projection --derive-status
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --fail-on projection
uv run pic parse audit --source tests\fixtures\minimal_claims.tex --strict-grammar
uv run pic schema --all --output-dir schemas
```

## Development Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
```

The package is designed for agent-facing JSON workflows. Registry entries are
metadata projections, not evidence; checked outputs distinguish declared status,
derived status, proof obligations, and residual ledgers.

## Documentation

- [Architecture](docs/architecture.md)
- [Mathematical contracts](docs/mathematical-contracts.md)
- [ECPT active agent runtime](docs/runtime.md)
- [Local runtime HTTP service](docs/runtime-service.md)
- [ECPT acceleration score](docs/ecpt-acceleration-score.md)
- [ECPT active phase-control runtime](docs/ecpt-phase-control-runtime.md)
- [SQOT salience scheduler](docs/sqot.md)
- [ECPT packet ecology runtime](docs/ecpt-packet-ecology-runtime.md)
- [Live connectors](docs/live-connectors.md)
- [Agent closed-loop runtime](docs/agent-closed-loop-runtime.md)
- [Benchmarks](docs/benchmarks.md)
- [Theory coverage](docs/theory-coverage.md)
- [External obligations](docs/external-obligations.md)
- [Agent integration](docs/agent-integration.md)
- [Verifier SDK](docs/verifier-sdk.md)
- [Production readiness](docs/production-readiness.md)
- [Provenance and SBOM](docs/provenance-and-sbom.md)
- [Tutorial](docs/tutorial.md)
- [Porting guide](docs/porting.md)

## License

Code in this repository is licensed under Apache-2.0. The cited Zenodo papers are
licensed CC-BY-4.0 by their publisher metadata and are not vendored here.
