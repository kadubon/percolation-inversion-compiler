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
- `operationally_usable` is true;
- `settled` is true;
- `missing_evidence_kind` is empty;
- the `discharge_level` is not `external_domain_required`;
- the residual ledger is preserved in downstream planning state.

This lets agents use the OSS to accelerate ASI-proxy phase-control workflows
without claiming that unobserved physical, oracle, simulator, or ASI facts have
been proved.
