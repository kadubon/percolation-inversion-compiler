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
```

An unresolved verifier hook must return diagnostic or provisional handling. It
may preserve evidence, route to a domain adapter, or return a partial frontier;
it must not convert an external physical, oracle, or ASI-related claim into
`settled` without accepted finite evidence and checker-derived status.

See `examples/external_verifier_hook.json` for a language-neutral unresolved
hook shape.

## Route Availability

`pic snapshot routes` emits `AdapterRouteSpec` records. A route can be:

- `implemented`: available in the lean core with finite inputs.
- `optional`: available only when the relevant optional OSS extra is installed.
- `unavailable`: a domain adapter contract exists, but the package does not
  claim to implement that domain verifier.

Unavailable routes return a diagnostic `VerifierResolution`. Optional routes
also return diagnostic results when their dependency is absent. Neither case may
promote an external obligation to `settled`.

## Evidence Envelopes

Adapters consume `VerifierEvidenceEnvelope` records: route id, obligation ids,
evidence kinds, evidence references, deterministic flag, and residual
coordinates. A resolver returns `VerifierResolution` with accepted/rejected
obligation ids and residual ledger entries. Agent connectors should log both
records so downstream planning can preserve the missing evidence boundary.
