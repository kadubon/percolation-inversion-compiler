# Mathematical Contracts

This project implements finite, checkable fragments of ECPT, BIT, and TRC. It
does not claim automatic proof of non-finite theorems or unobserved physical
claims.

## Core

- Finite orders expose reflexivity, antisymmetry, closure-based comparison,
  antichain extraction, and dominance witnesses.
- Algebra records expose finite monoid, semiring, and functor-law checks.
- Certificate families expose construction, verification, settlement, expiry,
  refresh, and non-promotion rules.
- Calibration certificates expose split, DKW, e-process, Good-Turing, and
  martingale-block residual ledgers.

## BIT

BIT records report potential only through protocol objects, intervention laws,
unit functors, stopped evidence sheaves, and certificate compiler graphs.
Unseen-frontier, Sinkhorn, CEGAR, and martingale outputs must include finite
residuals or missing obligations.

The theorem-level BIT certificates are finite interfaces, not informal labels:

- `StoppedEvidenceSheafCertificate` requires a common probability-space,
  stopping-time, ledger interface, finite pullback/gluing witness, and no missing
  local sections.
- `SelectiveCUPCertificate` requires vector-compatible family checks, unit audit
  coverage for required reported coordinates, and explicit selection charges.
- `MartingaleDeficiencyCertificate` computes a charged lower mass from finite
  block bounds and rejects floors that exceed the audited residual tolerance.

## ECPT

ECPT records treat capability propagation as protocol-relative. Activation,
reachable mass, queues, capacity, viability, and settlement are finite
certificates. Thermodynamic, mean-field, and ontology-extension clauses remain
finite envelopes or external obligations unless a concrete checker is supplied.

`FinitePhaseControlCertificate`, `ActivationThresholdCertificate`, and
`SettlementReturnRAFCertificate` separate finite witnesses from limit or
domain-dependent claims. If thermodynamic obligations, settlement event
obligations, or generator-calibration obligations remain, the checker returns
diagnostic status with missing obligations instead of promoting the claim.

## TRC

TRC main-frontier records require a full executable trace normal form. The trace
checker validates word normalization, transition proofs, causal schedules,
lifecycle freshness, resource flow/calendar feasibility, escrows, and residual
future-freedom vectors when present. A self-declared trace flag is not evidence.

TRC external areas include physical null-channel transfer, latent operators,
hybrid residual propagation, telemetry-updated kernels, and submodular redesign
oracles. These require `ExternalVerifierHook` records or remain unresolved
`ExternalProofObligation` entries with residual coordinates and failure modes.
The audit catalog assigns each unresolved item a verifier category, accepted
evidence kind, residual policy, and safe default so an agent can route the
obligation without treating the route itself as evidence.

Snapshot records preserve those contracts as derived finite metadata. They are
not additional axioms: a snapshot can guide adapter routing, while canonical TeX
audits and finite checkers remain the source of extracted judgments.
