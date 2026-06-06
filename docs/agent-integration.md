# Agent Integration

Percolation Inversion Compiler is intended to be called by autonomous agents as a
deterministic certificate service. The service does not tell an agent that a
physical or ASI claim is true. It tells the agent which finite certificates are
accepted, which proof obligations remain, and which residual ledger coordinates
must be charged.

## Stable Calls

Use these commands as integration boundaries:

```powershell
uv run pic check --source tests\fixtures\minimal_claims.tex --strict-projection --derive-status
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --fail-on projection
uv run pic schema --type AgentConnectorSpec
uv run pic schema --all --output-dir schemas
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
uv run pic routes bindings
uv run pic routes explain --route adapters.domain.verify_trc_telemetry_calibration
uv run pic routes explain --route ecpt.adapters.proxy.verify_target_contract
uv run pic ecpt plan --state examples\ecpt_phase_control_state.json --target examples\ecpt_asi_proxy_target.json --budget examples\ecpt_phase_control_budget.json --profile production
uv run pic ecpt simulate --state examples\ecpt_phase_control_state.json --actions examples\ecpt_phase_control_actions.json
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --provenance provenance.json --fail-on fail
uv run pic evidence verify --envelope examples\evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples\evidence_envelope.json --obligations examples\external_obligations.json --profile production
uv run pic demo datacenter
uv run pic explain external def:null-channel-routing
uv run pic doctor --fail-on warn
```

The JSON outputs are designed for language-neutral consumers:

- statuses are strings;
- finite sets and tuples are arrays at schema boundaries;
- proof obligations and residual ledgers are explicit objects;
- failure modes are strings intended for routing and policy checks.

## Connector Policy

An agent connector should implement this policy:

1. Validate input JSON against the emitted schema bundle.
2. Run `pic doctor` in the execution environment before operational use.
3. Run a checker command before using registry or frontier records.
4. Treat `declared_status` as metadata and `derived_status` as checker output.
5. Inspect `finite_checks_passed`, `finite_scope_usable`,
   `operationally_usable`, `settled`, `settled_scope`, and
   `residual_external_obligations`; `accepted` alone is not an operational
   approval.
6. Refuse main operational actions when `missing_obligations` is nonempty.
7. Route external proof obligations through `DischargeRouteBinding`,
   `VerifierEvidenceEnvelope`, `VerifierResolution`, and then a
   provenance-bound `ExternalVerifierHook`.
8. Preserve residual ledgers in logs and downstream planning records.
9. For ECPT active planning, treat `PhaseControlPlan.selected_actions` as
   ranked finite recommendations and route every `missing_obligations` entry
   before main operational execution.

## Routing Recipe

For each audit report:

1. Read `coverage_delta`; fail CI or agent planning when `unsupported_total` is
   nonzero.
2. Read `external_obligation_category_summary`; choose adapter families by
   category, not by informal label text.
3. For every external item, call `pic explain external <item-id>` and validate
   the result against `TheoryImplementationRecord.schema.json`.
4. For every intended verifier route, call `pic routes explain --route
   <route-id>` and preserve `settled_scope` and
   `residual_external_obligations`.
5. Call the domain adapter only when it can produce an accepted
   `VerifierResolution` with evidence artifact ids and a resolution digest.
   Convert it to an `ExternalVerifierHook` only after that provenance exists.
6. Keep the safe default when the hook is missing, rejected, nondeterministic, or
   outside the advertised verifier contract.

Minimal unresolved hook shape:

```json
{
  "hook_id": "example-null-channel-verifier",
  "verifier_route": "trc.adapters.physical_hybrid.verify_envelope",
  "obligation_ids": ["obligation:def:null-channel-routing"],
  "accepted_obligation_ids": [],
  "rejected_obligation_ids": [],
  "safe_default": "return-diagnostic-with-unresolved-obligations",
  "residual_coordinates": {
    "null-channel-unverified": 1.0
  },
  "provenance_policy": "legacy-hook-no-resolution-provenance"
}
```

This unresolved hook is intentionally diagnostic. An accepted hook must include
`resolution_id`, `resolution_digest`, `evidence_envelope_id`, and
`evidence_artifact_ids` from an accepted `VerifierResolution`.

## Safe Failure

Diagnostic output is not a crash. It is the expected safe result when evidence is
missing, a domain verifier is absent, a trace is stale, or a physical assumption
has not been certified. Agents should keep the diagnostic record and either ask
for more evidence, run a domain adapter, or return a partial frontier.

## Evidence Envelopes

External verifier input should use `VerifierEvidenceEnvelope` with
`EvidenceArtifact` records. Agents should require SHA-256 digests, schema
digests, producer identity, verifier identity, verifier version, timestamp, and
deterministic execution before treating an adapter result as a discharged
obligation. Missing or mismatched evidence keeps the result diagnostic and keeps
the residual charged.

In the `production` evidence profile, metadata-only artifacts are rejected.
Every artifact must either point to replayable `content_ref` whose SHA-256 digest
matches, or be handled by a future crypto/attestation adapter. The core package
does not accept a bare digest as production evidence.

Release provenance can be verified with a local SHA-256 manifest. GitHub
artifact-attested releases can additionally require attestation metadata:

```powershell
uv run pic provenance verify --manifest release-provenance.json --require-attestation
```

## ASI-Proxy Framing

The intended use is protocol-relative ASI-proxy phase-control research. Agents
can use the package to organize capability, bottleneck, and cyber-physical
frontier evidence. They must not treat it as evidence for unobserved ASI,
unconditional phase transition claims, or uncertified simulator output.

In v0.2.3, `pic ecpt plan` makes this workflow active: it ranks finite
interventions that can increase a protocol-relative ASI-proxy target under hard
gates, resource budgets, route bindings, and residual charges. The plan remains
diagnostic or provisional until verifier evidence discharges the relevant
external obligations.
