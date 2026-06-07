# Changelog

## v0.3.3 - 2026-06-07

- Adds ECPT collective phase certificates: fixed-population/no-self-rewrite
  ledgers, hidden-capability-injection reports, accepted autocatalytic closure
  witnesses, execution-available path certificates, packet lineage, and
  protocol frame digests.
- Strengthens Psi semantics so AC uses accepted closure witnesses and DE uses
  execution-available but not executed paths when available; cycle and edge
  density proxies remain diagnostic fallbacks with residual charges.
- Adds population runtime APIs, CLI, and service endpoints:
  `runtime population-step`, `runtime collective-certify`, `ecology closures`,
  `ecology execution-paths`, and `ecology hidden-injection-check`.
- Fixes closed-loop route/task reintegration so route execution batches and
  task results are persisted and can feed later packet promotion without
  silently settling residual external obligations.
- Extends SQLite runtime stores with additive tables for route batches,
  execution reports, population snapshots, and collective phase certificates.
- Updates README, docs, schemas, and examples around ECPT's core framing:
  ASI-proxy phase progress is collective packet percolation under constraints,
  not self-rewrite or model-weight change.

## v0.3.2 - 2026-06-07

- Reframes the runtime around ECPT collective capability percolation: ASI-proxy progress is packet availability, verification throughput, semantic edge composability, SQOT reserve, capacity/queue ledgers, and resource-matched basin movement rather than self-rewriting.
- Adds content-addressed evidence ref loading, profile-specific packet promotion policy, semantic edge relation verification, accepted packet paths, and `QS`/`HZ` Psi components for salience reserve and hazard/authority load.
- Adds resource-envelope matched acceleration certificates, acceleration experiment suites, allowlisted autonomous runtime task and route execution, and SQLite-backed runtime store records.
- Adds CLI and service surfaces for `runtime execute-task`, `runtime execute-routes`, `runtime run-agent-loop`, `runtime store`, `ecology paths`, and `ecology verify-edge`.
- Expands docs/examples for collective phase runtime, runtime executor, runtime store, edge relation verifiers, and resource-matched benchmarks while preserving explicit residual obligations for unobserved physical, oracle, simulator, and real ASI outcomes.

## v0.3.1 - 2026-06-06

- Closes the ECPT active agent runtime loop with action-result application, event logs, evidence resolution batches, verified packet promotion, and runtime run comparison.
- Adds finite `AccelerationCertificate` and `RuntimeComparisonReport` records so agents can compare baseline and candidate ASI-proxy phase-control runs without claiming unobserved ASI, physical, simulator, or oracle outcomes.
- Adds edge witness certificates, capability basin contracts, packet promotion reports, packet rejection records, and basin reachability reports for stricter packet-capital and false-liquidity control.
- Extends SQOT integration so stale, hash-invalid, unsafe-route, authority-invalid, and rollback-missing packets are quarantined and cannot make runtime output operationally usable.
- Adds `pic runtime resolve-evidence`, `pic runtime apply-results`, `pic runtime compare`, and `pic runtime certify-acceleration`, plus matching local HTTP service endpoints.

## v0.3.0 - 2026-06-06

- Adds the ECPT active agent runtime with stable `RuntimeState`, `RuntimeStepInput`, `RuntimeStepReport`, `AgentTask`, `RouteExecutionRequest`, `ActionCommit`, `PhaseAccelerationScore`, and runtime health records.
- Adds `pic runtime step`, `pic runtime loop`, `pic runtime health`, `pic runtime export-openapi`, and optional `pic runtime service` for local-first CLI, SDK, and HTTP agent integration.
- Composes packet ingestion, edge witnesses, Psi dashboards, bottleneck inversion, ECPT phase-control planning, SQOT scheduling, verifier route requests, and residual ledger preservation into one deterministic active loop.
- Adds production service policy: loopback default, bearer auth through `PIC_RUNTIME_TOKEN`, explicit opt-in for live connectors, and diagnostic JSON errors.
- Expands examples and docs for ECPT ASI-proxy phase-control workflows while keeping planning output fail-closed and never treating unobserved ASI, physical, simulator, or oracle outcomes as settled.

## v0.2.4 - 2026-06-06

- Adds SQOT support with canonical Zenodo DOI metadata, strict TeX grammar acceptance for SQOT axiom/assumption declarations, and a derived non-vendored coverage snapshot with unsupported and partial counts at zero.
- Adds the SQOT salience scheduler for finite attention occupation, diagnostic reserve, risk and verification-cost ledgers, quarantine, rollback, and safe queue decisions for packet, obligation, and verifier work.
- Adds the ECPT packet ecology runtime with packet ingestion, edge witnesses, Psi dashboards, verification-throughput metrics, bottleneck-inversion plans, and closed-loop agent iteration commands.
- Adds optional live connector ingestion for GitHub, Zenodo, and arXiv metadata behind fail-closed diagnostic packet ingestion reports.
- Expands docs, examples, schemas, citation metadata, NOTICE, and release checks for ECPT/BIT/TRC/SQOT agent-facing ASI-proxy phase-control workflows.

## v0.2.3 - 2026-06-06

- Adds the ECPT active phase-control runtime with `PhaseControlState`, `ASIProxyTargetContract`, ranked `PhaseControlAction` candidates, `PhaseControlPlan`, and `PhaseControlRunReport`.
- Adds `pic ecpt plan`, `pic ecpt simulate`, and `pic ecpt route-obligations` for autonomous-agent ASI-proxy phase-control workflows.
- Adds deterministic ECPT contract adapters for bridge reserve, trace diagnostics, ecology/ontology abstraction, economics/policy envelopes, proxy-target grounding, and speculative-channel repair.
- Keeps planner output proxy-active and fail-closed: plans can be operationally useful for routing, but unresolved external obligations remain charged and planning alone never settles unobserved ASI claims.

## v0.2.2 - 2026-06-06

- Adds settlement scope semantics to verifier resolutions and route bindings so finite replay/contract scope is separated from residual physical, oracle, policy, or domain obligations.
- Adds route-scoped production doctor checks and `pic routes explain` for agent-selected verifier route sets.
- Adds GitHub artifact-attestation metadata support in provenance manifests and `pic provenance verify --require-attestation`.
- Adds CycloneDX SBOM generation through `pic sbom create --format cyclonedx`.
- Adds strict TeX grammar diagnostics and `pic parse audit` so unknown theorem-like shapes and malformed MR macros are not silently ignored.

## v0.2.1 - 2026-06-06

- Adds canonical-to-implementation discharge route bindings for external verifier routes.
- Adds production evidence policy checks for replayable content hashes and provenance-bound hooks.
- Adds deterministic provenance manifests, schema digest output, SBOM generation, and production doctor provenance support.
- Expands verifier SDK docs for agent-facing ASI-proxy phase-control workflows without claiming unobserved physical or ASI proof.

## v0.2.0 - 2026-06-06

- Adds fail-closed status, ledger, frontier, and TRC compile behavior for agent-facing use.
- Adds evidence provenance records and deterministic external-verifier envelope checks.
- Adds production readiness profiles, SHA-256 canonical manifests, and hardened citation validation.
- Keeps ASI language protocol-relative: the project accelerates ASI-proxy phase-control workflows without claiming to prove unobserved ASI or physical claims.

## v0.1.0 - 2026-06-06

- Initial Apache-2.0 public release with ECPT/BIT/TRC finite certificate tooling, derived snapshots, schemas, CLI, CI, and security workflow.
