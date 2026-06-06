# External Obligations

External obligations are the explicit boundary between finite certificate
checking and claims that require domain evidence, simulators, physical traces,
or oracle-like witnesses. They are not failures of extraction, and they are not
accepted evidence by themselves.

Every external obligation in the canonical ECPT/TRC audit carries:

- `obligation_category`: a deterministic category derived from the paper item.
- `verifier_route`: the adapter boundary an agent may call.
- `verifier_contract`: input/output/promotion rules for that route.
- `accepted_evidence_kind`: finite evidence classes the route may consume.
- `residual_policy`: how residual charges remain until discharge.
- `safe_default`: the result an agent should use when no verifier is accepted.
- `failure_modes`: concrete reasons that prevent settled promotion.

## Current Canonical Categories

ECPT has 30 external obligations:

| Category | Count | Meaning |
| --- | ---: | --- |
| `ecpt-bridge-reserve` | 6 | ALT/SQOT/liquidity bridge and capsule projection obligations. |
| `ecpt-ecology-ontology` | 3 | Domain semantics, abstraction soundness, and ontology-extension evidence. |
| `ecpt-economics-policy` | 6 | Execution availability, friction, EVSI, and counterfactual policy evidence. |
| `ecpt-generator-limit` | 5 | Generator calibration, Markov/Bellman, and macroscopic limit envelopes. |
| `ecpt-proxy-target` | 3 | Proxy bundle and protocol-relative target grounding. |
| `ecpt-speculative-channel` | 4 | Speculative channel, repair route, and sparse-synergy evidence. |
| `ecpt-trace-diagnostic` | 1 | Auxiliary trace-complex diagnostic projection evidence. |
| `numerical-envelope` | 2 | Light-tail or growth-bound finite envelope evidence. |

TRC has 32 external obligations:

| Category | Count | Meaning |
| --- | ---: | --- |
| `archive-domain-cover` | 5 | Archive distortion, refinement, and progressive-fidelity cover evidence. |
| `assume-guarantee-contract` | 3 | Contract libraries and composition soundness evidence. |
| `distributionally-robust-metric` | 1 | Ground metric and dual distributionally robust witness evidence. |
| `latent-oracle-model` | 5 | Latent operators, atlases, oracle, and submodular witness evidence. |
| `numerical-envelope` | 2 | Contraction, logarithmic norm, and additive residual bounds. |
| `observation-partition` | 3 | Constructed partition and purification transition evidence. |
| `physical-hybrid-system` | 6 | Physical null-channel and hybrid buffer/envelope evidence. |
| `redesign-response` | 3 | Topology redesign and response interval evidence. |
| `telemetry-calibration` | 4 | Telemetry-updated kernels and online-regime calibration evidence. |

## Agent Routing

Agents should inspect external obligations before operational use:

```powershell
uv run pic audit theory --source "path\to\Typed Reality Compilation.tex" --canonical-key trc
uv run pic explain external def:null-channel-routing
uv run pic routes explain --route trc.adapters.physical_hybrid.verify_envelope
```

An unresolved verifier hook must return diagnostic or provisional handling. It
may preserve evidence, route to a domain adapter, or return a partial frontier;
it must not convert an external physical, oracle, or ASI-related claim into
`settled` without accepted finite evidence and checker-derived status.

See `examples/external_verifier_hook.json` for a language-neutral unresolved
hook shape.

## Route Availability

`pic snapshot routes` emits `AdapterRouteSpec` records, and `pic routes bindings`
emits the reviewed `DischargeRouteBinding` records that connect canonical
paper routes to implemented adapter contracts. In v0.2.4, canonical ECPT/TRC/SQOT
external routes are no longer left as opaque `unavailable` entries. Each route
has a fail-closed binding and one of these discharge levels:

- `finite_value_check`: finite numeric, telemetry, archive, or generator
  evidence can be checked by the package.
- `replay_check`: finite replay evidence can be checked, while continuous
  physical-domain claims remain residual obligations.
- `contract_enforced`: the SDK checks envelope shape, provenance, safe default,
  and non-promotion rules, but keeps a named domain witness unresolved.
- `external_domain_required`: the route is bound to an adapter contract, but an
  external domain witness or oracle-style evidence remains necessary.

Optional OSS routes also return diagnostic results when their dependency is
absent. Contract-enforced and external-domain routes can be operationally useful
for agent routing, but they do not make the underlying external claim `settled`
unless a finite accepted `VerifierResolution` with provenance discharges the
matching obligation.

`DischargeRouteBinding.settlement_scope` names the finite part of the route that
the package can discharge. `residual_external_obligation_refs` names the
external domain evidence that remains. For `replay_check` and
`contract_enforced` routes, agents may use `finite_scope_usable` while still
carrying those residual obligations forward.

The ECPT active runtime uses the same route catalog. Bridge reserve, trace
diagnostic, ecology/ontology abstraction, economics/policy, proxy-target, and
speculative-channel categories are bound to deterministic contract adapters.
These adapters check finite envelope content and residual bounds where possible;
they keep proxy grounding, ontology extension, policy counterfactual, channel
repair, and cross-theory proof obligations explicit when domain evidence is not
finite.

## Evidence Envelopes

Adapters consume `VerifierEvidenceEnvelope` records: route id, obligation ids,
evidence kinds, evidence references, deterministic flag, residual coordinates,
and `EvidenceArtifact` provenance. Each artifact carries SHA-256
identity, schema digest, producer identity, verifier identity, verifier version,
timestamp, and optional signature or attestation references. A resolver returns
`VerifierResolution` with accepted/rejected obligation ids, settled scope,
finite-scope usability, residual external obligations, and residual ledger
entries. Agent connectors should log both records so downstream planning can
preserve the missing evidence boundary.

The production evidence profile is stricter than development: metadata-only
artifacts with `content_ref: null` are diagnostic unless an optional attestation
adapter has verified the attestation. Legacy `ExternalVerifierHook` records are
still readable, but an accepted hook must reference an accepted
`VerifierResolution` by `resolution_id`, `resolution_digest`,
`evidence_envelope_id`, and `evidence_artifact_ids` before it can discharge an
external certificate obligation.
