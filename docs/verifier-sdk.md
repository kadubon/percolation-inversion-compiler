# Verifier SDK

The verifier SDK connects paper-derived external obligations to replayable
finite evidence. It is not a physical oracle. It is a certificate boundary that
lets agents distinguish finite value checks, replay checks, contract-enforced
routes, and obligations that still require external domain evidence.

## Route Bindings

Use:

```powershell
uv run pic snapshot routes
uv run pic routes bindings
uv run pic routes explain --route adapters.domain.verify_trc_telemetry_calibration
```

`AdapterRouteSpec` describes a route contract. `DischargeRouteBinding` states how
a canonical paper route maps to an implemented route and which
`discharge_level` applies:

- `finite_value_check`: bounded finite tables or numeric envelopes are checked.
- `replay_check`: a finite trace or event log is replayed.
- `contract_enforced`: the envelope and required fields are enforced, but a
  route-specific domain witness may still be needed.
- `external_domain_required`: the package can route and charge residuals, but it
  cannot settle the domain claim by itself.

v0.2.2 makes settlement scope explicit. `VerifierResolution.settled_scope`
lists the finite scope that the route actually discharged.
`finite_scope_usable` can be true even when `settled` is false; this happens for
replay and contract routes whose finite envelope is useful but whose continuous
physics, oracle, policy, or domain witness remains in
`residual_external_obligations`. A route is globally `settled` only when the
accepted resolution leaves no residual external obligations.

## Evidence Flow

Production evidence should follow this path:

```powershell
uv run pic evidence verify --envelope examples\evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples\evidence_envelope.json --obligations examples\external_obligations.json --profile production
```

The first command emits `VerifierResolution`. The second command converts an
accepted resolution into a provenance-bound `ExternalVerifierHook` and checks the
hook against the listed `ExternalProofObligation` records.

Legacy hooks without `resolution_id`, `resolution_digest`,
`evidence_envelope_id`, and `evidence_artifact_ids` remain readable, but they do
not settle accepted obligations. This prevents a self-declared hook from
bypassing evidence provenance.

## Agent Policy

Agents should only use a verifier result operationally when:

- `accepted` is true;
- `finite_scope_usable` is true for the finite route segment they intend to use;
- `missing_evidence_kind` is empty;
- `settled` is true only if they need the whole route to be discharged;
- `residual_external_obligations` is preserved when `settled` is false;
- `domain_witness_required` is false before claiming global settlement;
- the residual ledger is preserved in downstream planning state.

This lets agents use the OSS to accelerate ASI-proxy phase-control workflows
without claiming that unobserved physical, oracle, simulator, or ASI facts have
been proved.
