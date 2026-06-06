# Architecture

Percolation Inversion Compiler is a JSON-first finite certificate toolkit. Its
main design rule is that registries, metadata, and publication capsules are
projections of checker/extractor judgments, not independent evidence.

## Layers

- `core`: statuses, ledgers, validity domains, obligations, structured checker
  contexts, judgments, dependency DAGs, proof obligations, projection audits,
  theory audit reports, and portable schemas.
- `io`: TeX and machine-readable registry extraction, canonical DOI checksum
  validation, JSON/YAML loading, and schema emission.
- `bit`: finite witness calculus for unit-typed unlockable potential.
- `ecpt`: finite capability hypergraph, activation, queue/capacity, settlement,
  and mean-field certificate records.
- `trc`: typed cyber-physical process frontier records, tolerance/resource
  ledgers, executable trace normal forms, and stratified frontier compilation.

## Agent-Facing Contract

Agent integrations should consume deterministic JSON and keep the following
fields separate:

- `declared_status`: what an external source or registry says;
- `derived_status`: what the checker derives from finite obligations;
- `proof_obligations`: what remains unverified or domain-specific;
- `residual_ledger`: what is charged rather than erased.

Main frontier records require accepted executable trace normal forms. Records
without those traces are diagnostic or partial, not main operational claims.
Strict projection audits compare stable registry fields against extractor
judgments, while still treating registry-declared status as metadata rather than
checker-derived evidence.

`AgentConnectorSpec` is the stable handoff record for autonomous-agent
libraries. It exposes capabilities, capability routing, input/output contracts,
safe failure behavior, status policy, and residual policy. Agents should route
work to `pic check`, `pic audit theory`, `pic compile`, or domain adapters based
on that explicit contract rather than inferring success from labels.

External obligations are exposed as verifier contracts through the theory audit
catalog and `pic explain external <item-id>`. The route describes the adapter
boundary; it is not an endorsement of the claim. Missing or rejected verifier
hooks keep diagnostic/provisional handling and preserve residual coordinates.
For users without TeX, bundled derived snapshots expose the same coverage
counts, item-id mappings, and external route contracts without vendoring paper
source files.
`pic doctor` combines schema, snapshot, adapter-route, optional-dependency, and
canonical-TeX checks into one JSON readiness report for CI and agent runners.

## Checker Discipline

Boolean helpers remain for compatibility, but finite checker implementations
return `CheckResult` records with status, reasons, missing obligations, and
residual ledgers. `CertificateDAG` evaluation is topological and exposes cycles,
missing predecessors, expired obligations, and unresolved external proof
obligations instead of silently promoting claims.

Theorem-level certificate records now wrap lower-level finite witnesses:

- BIT stopped evidence sheaves, selective CUP, and martingale deficiency
  certificates reuse gluing, unit-functor, and block-residual checkers.
- ECPT finite phase-control, activation threshold, and settlement-return RAF
  certificates split finite acceptance from thermodynamic or external
  obligations.
- TRC leaves physical, latent, hybrid, oracle, and submodular clauses behind
  `ExternalProofObligation` and `ExternalVerifierHook` records.

## Portability

The implementation keeps algorithmic kernels small and explicit so other
languages can port them. Optional scientific libraries are adapters, not hidden
requirements for the core data model.

Public JSON must not rely on Python-specific identity or ordering. Sets and
tuples are represented through JSON Schema as arrays, enums are strings, and
callers should sort arrays when deterministic comparisons matter.
