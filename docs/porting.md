# Porting Guide

Percolation Inversion Compiler is designed as a JSON-first certificate toolkit.
Other implementations should treat Python classes as reference constructors for
portable schemas, not as the normative wire format.

## Stable Contracts

- Emit schemas with `pic schema --all --output-dir <dir>`.
- Use `pic snapshot list` and `pic snapshot show --artifact <key>` when the
  port does not have local canonical TeX sources.
- Use `pic doctor` as the reference operational readiness report for CI and
  agent-runner startup checks.
- Use string enum values for statuses and coverage states.
- Encode tuples as arrays and finite sets as arrays with deterministic sorting
  at API boundaries.
- Preserve `declared_status` and `derived_status` as separate fields.
- Preserve `accepted`, `finite_checks_passed`, `operationally_usable`, and
  `settled` as distinct booleans. `accepted` alone is not enough for autonomous
  operational use.
- Preserve `workflow_usable` where it exists. It means the JSON is useful for
  the next safe workflow step; it is not a synonym for `settled`.
- Preserve `finite_scope_usable`, `settled_scope`,
  `residual_external_obligations`, and `domain_witness_required` on
  `VerifierResolution`. A replay or contract route may expose useful finite
  scope while still being globally unsettled.
- Never promote a registry status to `settled` without checker-derived
  obligations.
- Keep non-finite, simulator-dependent, physical-domain, or oracle-dependent
  claims as `ExternalProofObligation` records with residual charges.
- Preserve `ExternalVerifierHook` as a result channel, not a trusted authority.
  A hook can settle only the obligation IDs it explicitly accepts; unknown,
  rejected, or omitted IDs remain diagnostic.
- Preserve external obligation category, verifier route, accepted evidence kind,
  residual policy, safe default, and failure modes as plain JSON fields.
- Validate `examples/portability_conformance/manifest.json` and each referenced
  output against its named schema before claiming conformance with the Python
  reference implementation.
- Run `pic portability verify --manifest examples/portability_conformance/manifest.json`
  as the reference conformance check. The manifest includes schema names,
  expected outputs, SHA-256 checksums, semantic invariants, and negative
  examples that must fail with the declared status.

## Adapter Boundary

Optional packages such as NetworkX, Pint, SciPy, HiGHS, and POT may accelerate
finite algorithms. They must not change public schemas or hide proof
obligations. If an adapter cannot supply a finite certificate, return an
external obligation rather than a settled result.

## Agent Integration

Agents should consume deterministic JSON outputs from `pic check`, `pic audit
theory`, `pic agent check`, `pic phase plan`, `pic runtime step`,
`pic compile`, and `pic demo datacenter`. The agent-facing invariant is
that every accepted operational output has an explicit checker route, residual
ledger, and failure mode.

Recommended connector behavior:

- Call `pic schema --all` at integration time and validate inputs before routing
  them to an autonomous workflow.
- Treat `safe_failure_behavior` in `AgentConnectorSpec` as binding. Diagnostic
  output with proof obligations is a successful safe failure, not an exception.
- Never rewrite `declared_status` into `derived_status`; only checker results may
  derive status.
- Treat `pic explain external <item-id>` as the portable adapter contract for
  unresolved physical, oracle, simulator, or domain-specific obligations.
- Treat `pic routes explain --route <route-id>` as the portable route binding
  contract for settlement scope, discharge level, required evidence kind, and
  residual external obligations.
- Treat `TheorySnapshot`, `SnapshotCatalog`, `AdapterRouteSpec`,
  `EvidenceArtifact`, `VerifierEvidenceEnvelope`, `VerifierResolution`, and
  `OperationalReadinessReport` as stable wire contracts.
- Treat `AgentCheckReport`, `RuntimeStepReport`, `SalienceScheduleReport`,
  `AgentMessageDeliveryReport`, `AgentRelayReadinessReport`,
  `ALTAdmissionDecision`, `CollectivePhaseCertificate`,
  `PhaseControlAuditSummary`, `FrontierDebtReport`,
  `BottleneckWitnessReport`, `ValueBridgeReport`, `PhaseAccelerationPlan`,
  `PhaseGapVector`, `BottleneckCandidate`, `SafePhaseAction`,
  `PhaseAccelerationBenchmarkReport`, and `TheoryFidelityReport`
  as the minimum portability conformance pack for first ports.
- For practical agent integrations, implement the compact `pic agent check`
  payload shape even if the port stores the full nested `AgentCheckReport`
  internally. The compact fields are the stable first-read fields for CI and
  agents.
- For phase planning, implement the compact `pic phase plan --compact` payload
  shape. Candidate-only external intake, agent messages, proxy-only ALT output,
  and missing production identity must not reduce phase gaps or clear
  `settled_blockers`.
- Preserve default-live communication semantics: explicit sources are live-capable by default,
  `--no-allow-live-connectors` or `allow_live_connectors=false` is the opt-out, and external
  intake remains candidate-only until downstream verifier, identity, nonce, rollback, semantic
  edge, and residual policies pass.

## Provenance And SBOM Ports

Ports should implement the hash-based `ProvenanceManifest` verifier before
accepting schema bundles, snapshots, examples, or release metadata. If
attestation is required, validate `AttestationRecord` subject names and
SHA-256 subject digests against the manifest entries, and then delegate full
Sigstore or platform attestation verification to the host runtime.

`SBOMManifest` preserves the PIC-SBOM compatibility format. Release assets also
include CycloneDX JSON. A port does not need to generate byte-identical Python
dependency inventories, but it should keep component names, versions, licenses,
and package URLs deterministic.

## Strict TeX Parsing

`StrictTexParseReport` and `TexGrammarDiagnostic` are fail-closed parser
contracts. Ports should not silently ignore unknown theorem-like environments,
malformed MR macros, duplicate labels, orphan labels, or multi-line label parse
failures when strict grammar mode is requested.
