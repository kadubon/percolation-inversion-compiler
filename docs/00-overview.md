# Overview

Percolation Inversion Compiler is a finite certificate and verifier-routing runtime for ECPT, BIT, TRC, and SQOT. It helps an engineer or AI agent decide which protocol-relative capability packets are usable, which semantic edges are accepted, which obligations remain unresolved, and which bottleneck should be handled next.

The central ECPT interpretation used by this repository is collective phase progress. A fixed population of agents can generate many finite capability packets under declared constraints. Those packets become more useful when they are evidence-bound, receiver-compatible, queue-admissible, execution-available but not executed, and composable into accepted paths or closure witnesses. This does not require self-rewriting, fine-tuning, or model-weight changes.

## Inputs

- Theory snapshots or canonical TeX sources.
- Capability packet candidates from local files, agent output, repositories, or connector fixtures.
- Verifier evidence envelopes and content-addressed evidence refs.
- Runtime state, action results, route execution batches, and SQOT queue records.
- Basin contracts, resource baselines, thresholds, and protocol frame digests.

## Outputs

- Deterministic JSON checker judgments.
- Proof obligations and residual ledgers.
- Semantic edge certificates and packet-promotion reports.
- SQOT salience schedules and quarantine decisions.
- Psi dashboards for finite collective-phase proxies.
- Bottleneck tasks and phase-control recommendations.
- Runtime event logs, persistent store snapshots, and collective phase certificates.

## Safety Boundary

The package does not prove real ASI or unobserved physical/oracle outcomes. It provides protocol-relative ASI-proxy checks and routing records. A result can be useful for an agent even when `settled=false`, because unresolved obligations remain explicit and machine-readable.

## Primary Concepts

- **Capability packet**: a finite reusable artifact with provenance, evidence refs, route requirements, receiver context, and residual charges.
- **Verified packet capital**: a packet promoted only after required route, hash, receiver, authority, rollback, semantic edge, and residual policies pass.
- **Semantic edge**: a checked relation such as theorem-to-code, code-to-test, obligation-to-verifier, execution-path, rollback-support, liquidity-transfer, or autocatalytic-regeneration.
- **SQOT salience queue**: a finite scheduling layer that accounts for diagnostic reserve, stale packets, hazards, cost, and residual reduction.
- **Psi dashboard**: a vector of finite proxy components including graph availability, dependency/execution availability, autocatalytic closure, verification throughput, queue state, hazard load, and basin reachability.
- **Collective phase certificate**: a protocol-relative certificate that checks fixed population, no self-rewrite, no hidden injection, closure, execution availability, Psi thresholds, SQOT reserve, hazard/authority checks, and resource-matched baseline.

## Reading Order

1. [Quickstart](01-quickstart.md)
2. [Collective phase certificate](04-collective-phase-certificate.md)
3. [Safety boundary](11-safety-boundary.md)
4. [CLI reference](cli-reference.md)
5. [Agent integration](agent-integration.md)
