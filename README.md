# Percolation Inversion Compiler

`percolation-inversion-compiler` is an ECPT collective phase certificate
runtime and production-oriented finite verifier-routing SDK for ECPT, BIT, TRC,
and SQOT. It does not model ASI-proxy progress as one agent rewriting itself,
fine-tuning itself, or changing model weights. It models the ECPT core: a fixed
population of agents produces many finite capability packets under declared
constraints; those packets become available, verified, receiver-valid, liquid,
queue-admissible, execution-available but not executed, and composable enough to
percolate toward a protocol-relative target basin.

The package turns paper-derived TeX, registry JSON, verifier evidence, agent
outputs, action results, evidence-store refs, and packet candidate records into
deterministic JSON: finite checker judgments, proof obligations, residual
ledgers, salience-queue schedules, typed trace normal forms, frontier extraction
records, verified packet promotion reports, semantic packet-edge certificates,
Psi dashboards with SQOT and hazard components, autocatalytic closure
witnesses, execution-available path certificates, hidden-capability-injection
reports, collective phase certificates, bottleneck-inversion plans, runtime
event logs, finite acceleration certificates, provenance manifests, SBOMs, and
portable JSON Schemas for AI agent integration.

Search terms: certificate compiler, proof obligations, residual ledgers, typed
trace normal forms, frontier extraction, AI agent integration,
protocol-relative ASI-proxy phase-control.

In practical terms, the input is a finite artifact an agent may want to use: a
canonical theory source, packet candidate, issue/PR/repository metadata, agent
work product, trace, or verifier evidence envelope. The output answers five
questions: which finite certificates passed, which proof obligations remain,
which residual coordinates stay charged, which packets can become reusable
verified packet capital, which semantic edges are accepted, which
packets/obligations should be scheduled next, which ECPT ASI-proxy component is
currently the bottleneck, and whether a candidate runtime path improves on a
resource-matched baseline.
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
  finite interventions, packet-edge construction, verified packet promotion,
  and acceleration-certificate checks for ASI-proxy targets.
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

- Use as CLI: run `pic runtime step`, `pic runtime population-step`,
  `pic runtime collective-certify`, `pic runtime resolve-evidence`,
  `pic runtime execute-task`, `pic runtime execute-routes`, `pic runtime
  run-agent-loop`, `pic runtime store init|append|load|export`, `pic runtime
  apply-results`, `pic runtime compare`, `pic runtime certify-acceleration`,
  `pic ecology closures`, `pic ecology execution-paths`, `pic ecology
  hidden-injection-check`, `pic ecology paths`, `pic ecology verify-edge`, `pic
  ecpt plan`, `pic sqot schedule`, and `pic evidence verify`.
- Use as Python SDK: call `build_runtime_step`, `resolve_step_evidence`,
  `execute_runtime_task`, `execute_route_batch`, `run_agent_loop_with_store`,
  `apply_action_results`, `compare_runtime_runs`, `certify_runtime_acceleration`,
  and `runtime_health` with portable runtime JSON.
- Run local HTTP service: start `pic runtime service --host 127.0.0.1 --port
  8765 --profile production` and call `/runtime/step`, `/runtime/loop`,
  `/runtime/result/apply`, `/runtime/evidence/resolve`, `/runtime/compare`,
  `/runtime/certify-acceleration`, `/runtime/task/execute`,
  `/runtime/routes/execute`, `/runtime/store/append`, `/runtime/store/load`,
  `/runtime/run-agent-loop`, `/runtime/population/step`,
  `/runtime/collective/certify`, `/ecology/closures`,
  `/ecology/execution-paths`, `/ecology/hidden-injection-check`,
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
- evidence-store backed verifier-envelope resolution;
- production packet promotion policy tied to route, edge, rollback, authority,
  hash, receiver, and residual obligations;
- verified packet promotion, packet rejection, and semantic edge certificates;
- `QS` and `HZ` Psi components for SQOT reserve and hazard/authority load;
- fixed-population and no-self-rewrite ledgers for ECPT collective phase claims;
- accepted autocatalytic closure witnesses and execution-available path
  certificates;
- hidden-capability-injection checks against a protocol frame digest;
- collective phase certificates that require closure, execution availability,
  threshold-crossed Psi, resource-matched baseline, SQOT reserve, and hazard
  checks;
- accepted packet paths into ECPT basin contracts;
- allowlisted autonomous runtime execution and route execution;
- SQLite-backed runtime stores for event logs and packet-capital accumulation;
- closed-loop event logs and action-result application for repeated agent runs;
- finite acceleration certificates comparing candidate runs to
  resource-envelope-matched baselines;
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
- a claim that self-rewriting or model-weight changes are required for ECPT
  phase progress;
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
uv run pic ecology paths --registry ecology-registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology verify-edge --registry examples/ecology_packets.json --certificate examples/edge_relation_certificate.json
uv run pic ecology loop --state examples/ecology_loop_state.json --agent-output "SQOT reserve packet for ECPT active phase-control."
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input_with_evidence.json --profile production --output runtime-step.json
uv run pic runtime resolve-evidence --input examples/runtime_step_input_with_evidence.json --profile production
uv run pic runtime execute-task --state examples/runtime_state.json --task examples/runtime_agent_task.json --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime execute-routes --requests examples/runtime_route_requests.json --evidence-store evidence-store --profile development
uv run pic runtime store init --store runtime.sqlite
uv run pic runtime store append --store runtime.sqlite --state examples/runtime_state.json
uv run pic runtime run-agent-loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --store runtime-loop.sqlite --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime apply-results --state examples/runtime_state.json --report runtime-step.json --results examples/runtime_action_results.json --output runtime-next-state.json
uv run pic runtime compare --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json
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
uv run pic runtime resolve-evidence --input examples\runtime_step_input_with_evidence.json --profile production
uv run pic runtime compare --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json --threshold examples\runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json
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
- [ECPT collective phase runtime](docs/collective-phase-runtime.md)
- [ECPT closed-loop runtime](docs/runtime-closed-loop.md)
- [Local runtime HTTP service](docs/runtime-service.md)
- [Runtime executor](docs/runtime-executor.md)
- [Runtime store](docs/runtime-store.md)
- [ECPT acceleration score](docs/ecpt-acceleration-score.md)
- [Finite acceleration certificates](docs/acceleration-certificates.md)
- [Resource-matched benchmarks](docs/resource-matched-benchmarks.md)
- [Edge relation verifiers](docs/edge-relation-verifiers.md)
- [Verified packet promotion](docs/packet-promotion.md)
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
