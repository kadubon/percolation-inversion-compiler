# Tutorial

This tutorial uses local fixtures so it can run without vendoring the canonical
TeX sources.

## 1. Install

```powershell
uv sync --all-extras --dev
```

## 2. Check a Minimal Registry

```powershell
uv run pic check --source tests\fixtures\minimal_claims.tex --strict-projection --derive-status
```

Expected behavior:

- the registry projection is accepted;
- declared status is not promoted;
- the derived status summary remains checker-derived.

## 2a. Use Snapshots Without TeX

Users who do not have the canonical TeX files can still inspect the derived
coverage and external-obligation contracts:

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact trc
uv run pic explain external def:null-channel-routing --from-snapshot
uv run pic snapshot routes
uv run pic snapshot verify --artifact trc
uv run pic routes bindings
uv run pic routes explain --route adapters.domain.verify_trc_telemetry_calibration
uv run pic evidence verify --envelope examples/evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples/evidence_envelope.json --obligations examples/external_obligations.json --profile production
uv run pic doctor --fail-on never
uv run pic doctor --profile production --fail-on never
```

Snapshots contain DOI/checksum attribution, coverage counts, item-id mappings,
and external verifier contracts. They do not include TeX or PDF content.
`pic doctor` reports whether schemas, snapshots, adapter routes, optional
dependencies, and canonical TeX metadata are operationally ready.

## 3. Emit Schemas

```powershell
uv run pic schema --all --output-dir schemas
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
uv run pic doctor --profile production --provenance provenance.json --fail-on fail
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --provenance provenance.json --fail-on fail
uv run pic sbom create --format cyclonedx --output cyclonedx.sbom.json
```

The bundle includes core records such as `Judgment`, `ObligationSet`,
`TheoryAuditReport`, `ExternalVerifierHook`, theorem-level BIT/ECPT
certificates, `DischargeRouteBinding`, `EvidencePolicy`,
`ProvenanceManifest`, and `AgentConnectorSpec`.

## 4. Audit Theory Coverage

```powershell
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --fail-on projection
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --strict-grammar --fail-on projection
uv run pic parse audit --source tests\fixtures\minimal_claims.tex --strict-grammar
```

For canonical paper audits, set `PIC_CANONICAL_TEX_DIR` to a local directory that
contains the TeX files. The repository does not vendor those files.

## 5. Run the Datacenter Demo

```powershell
uv run pic demo datacenter
```

The demo emits a TRC compile result with main, diagnostic, relaxed, and partial
frontier records. Main-frontier records require accepted executable trace normal
forms; a self-declared trace flag is not enough.

## 6. Run ECPT Active Phase-Control

```powershell
uv run pic ecpt plan --state examples\ecpt_phase_control_state.json --target examples\ecpt_asi_proxy_target.json --budget examples\ecpt_phase_control_budget.json --profile production
uv run pic ecpt simulate --state examples\ecpt_phase_control_state.json --actions examples\ecpt_phase_control_actions.json
uv run pic routes explain --route ecpt.adapters.proxy.verify_target_contract
```

Read `finite_proxy_gain_total`, `selected_actions`,
`required_evidence_routes`, `missing_obligations`, and `residual_ledger`. The
plan helps an agent choose which finite ECPT action to evaluate next. It does
not prove the unobserved ASI target or discharge domain obligations by itself.

## 7. Run the Active Agent Runtime

The v0.3.1 runtime composes ECPT planning, packet ecology, SQOT scheduling,
verifier routing, packet promotion, and finite acceleration comparison into one
agent-facing loop:

```powershell
uv run pic runtime step --state examples\runtime_state.json --input examples\runtime_step_input.json --profile production
uv run pic runtime step --state examples\runtime_state.json --input examples\runtime_step_input_with_evidence.json --profile production --output runtime-step.json
uv run pic runtime resolve-evidence --input examples\runtime_step_input_with_evidence.json --profile production
uv run pic runtime apply-results --state examples\runtime_state.json --report runtime-step.json --results examples\runtime_action_results.json --output runtime-next-state.json
uv run pic runtime compare --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json --threshold examples\runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json
uv run pic runtime loop --state examples\runtime_state.json --inputs examples\runtime_loop_inputs.jsonl --max-steps 2 --profile production
uv run pic runtime health --state examples\runtime_state.json --profile production
uv run pic runtime export-openapi --output runtime-openapi.json
```

Read `agent_tasks`, `route_execution_requests`, `promotion_report`,
`evidence_resolution_batch`, `phase_acceleration_score`, `missing_obligations`,
and `residual_ledger`. Runtime output can rank protocol-relative ASI-proxy work
for an agent, but it keeps `settled=false` until verifier evidence discharges
the relevant finite route. Use `AccelerationCertificate` only as a finite
baseline-comparison result, not as proof of unobserved ASI.

The optional service is local-first:

```powershell
$env:PIC_RUNTIME_TOKEN = "replace-with-local-token"
uv run pic runtime service --host 127.0.0.1 --port 8765 --profile production
```

Production service requests must include `Authorization: Bearer
<PIC_RUNTIME_TOKEN>`.

## 8. Read Coverage

```powershell
uv run pic coverage --source tests\fixtures\minimal_claims.tex
uv run pic explain coverage def:no-status
```

Coverage statuses distinguish finite constructive algorithms, finite checkers,
portable schemas, external proof obligations, and unsupported items. Canonical
coverage should keep `unsupported` at zero.

## 9. Route External Obligations

For canonical sources, external items can be explained as verifier contracts:

```powershell
uv run pic explain external def:null-channel-routing
```

The output is a `TheoryImplementationRecord` with an obligation category,
verifier route, accepted evidence kinds, residual policy, safe default, and
failure modes. `pic routes explain --route <route-id>` adds the
`DischargeRouteBinding`, settlement scope, residual external obligations, and
required evidence kinds. Agent integrations should use these records to decide
whether to call a domain adapter or keep a diagnostic/partial result.

When TeX is unavailable, add `--from-snapshot` to read the bundled derived
metadata instead.

## 10. Verify Evidence Envelopes

```powershell
uv run pic evidence verify --envelope examples\evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples\evidence_envelope.json --obligations examples\external_obligations.json --profile production
```

The example demonstrates the verifier SDK boundary. The envelope is
accepted only when the route id, evidence kind, SHA-256 digest shape, schema
digest shape, producer identity, verifier identity, verifier version, and
determinism checks pass. Production mode also rejects metadata-only evidence
without a replayable `content_ref` or verified attestation. The discharge command
emits a provenance-bound `ExternalVerifierHook`; legacy hooks without resolution
provenance remain diagnostic.

`VerifierResolution.settled_scope` names the finite scope that was discharged.
For replay or contract-enforced routes, `finite_scope_usable` may be true while
`settled` remains false and `residual_external_obligations` carries the
continuous, oracle, policy, or domain witness that still has to be routed.
