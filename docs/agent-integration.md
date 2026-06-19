# Agent Integration

Percolation Inversion Compiler is intended to be called by autonomous agents as a
deterministic certificate service. The service does not tell an agent that a
physical or ASI claim is true. It tells the agent which finite certificates are
accepted, which proof obligations remain, and which residual ledger coordinates
must be charged.

## Stable Calls

Use these commands as integration boundaries:

```powershell
pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
pic agent runbook --profile development
pic agent check --text "Candidate packet: preserve residuals." --profile development
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
uv run pic sqot schedule --packets examples\sqot_queue.json --profile production
uv run pic ecology build-edges --packets examples\ecology_packets.json --output ecology-registry.json
uv run pic ecology ingest-general --source examples\agent_network\feed.xml --kind rss
uv run pic ecology ingest-general --source examples\agent_network\page.html --kind web-page
uv run pic ecology discover-web --source examples\agent_network\page.html
uv run pic agent message ingest --message examples\agent_network\agent_message.json
uv run pic ecology psi --registry ecology-registry.json --threshold examples\ecology_threshold.json --output ecology-psi.json
uv run pic ecology plan --registry ecology-registry.json --psi ecology-psi.json --profile production
uv run pic ecology loop --state examples\ecology_loop_state.json --agent-output "SQOT reserve packet for ECPT active phase-control."
uv run pic runtime step --state examples\runtime_state.json --input examples\runtime_step_input.json --profile production
uv run pic runtime resolve-evidence --input examples\runtime_step_input_with_evidence.json --profile production
uv run pic runtime apply-results --state examples\runtime_state.json --report runtime-step.json --results examples\runtime_action_results.json --output runtime-next-state.json
uv run pic runtime compare --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json --threshold examples\runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples\runtime_baseline_run.json --candidate examples\runtime_candidate_run.json
uv run pic runtime population-step --population examples\agent_population.json --inputs examples\runtime_loop_inputs.jsonl --profile production
uv run pic runtime collective-certify --population examples\agent_population.json --state examples\collective_runtime_state.json --basin examples\ecpt_basin_contract.json --baseline examples\runtime_baseline_run.json --threshold examples\runtime_threshold.json
uv run pic runtime loop --state examples\runtime_state.json --inputs examples\runtime_loop_inputs.jsonl --max-steps 2 --profile production
uv run pic runtime health --state examples\runtime_state.json --profile production
uv run pic runtime export-openapi --output runtime-openapi.json
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --provenance provenance.json --fail-on fail
uv run pic evidence verify --envelope examples\evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples\evidence_envelope.json --obligations examples\external_obligations.json --profile production
uv run pic demo datacenter
uv run pic explain external def:null-channel-routing
uv run pic doctor --fail-on warn
uv run pic portability verify --manifest examples\portability_conformance\manifest.json
uv run pic audit fidelity --canonical-dir "$env:PIC_CANONICAL_TEX_DIR"
```

The JSON outputs are designed for language-neutral consumers:

- statuses are strings;
- finite sets and tuples are arrays at schema boundaries;
- proof obligations and residual ledgers are explicit objects;
- failure modes are strings intended for routing and policy checks.

For installed-package use, `pic agent check --compact` is the preferred first
command. It returns short practical JSON with checked outputs, unresolved
obligations, residual summary, schema refs, next safe actions, and
`workflow_usable`. Use full `pic agent check` when the agent needs the nested
`AgentCheckReport`, and use `pic agent runbook` when the agent needs
deterministic next commands, schemas, and fields to inspect. These fields
preserve `operationally_usable` and `settled` semantics from the underlying
runtime report.

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
10. For v0.4.2 active runtime, submit observations through `RuntimeStepInput`,
    let the runtime rebuild packet edges, update Psi, run SQOT scheduling,
    rank ECPT phase-control tasks, and preserve residual ledgers without
    settling unresolved proof obligations. Prefer typed
    `phase_control_audit`, `frontier_debt_report`, and
    `bottleneck_witness_reports`; keep reading `phase_control_summary`,
    `frontier_debt_summary`, and `bottleneck_witness_tasks` for backward
    compatibility.
11. Resolve evidence envelopes, promote only verified packets, apply
    `RuntimeActionResult` records, and compare runtime runs before treating a
    candidate strategy as finite ASI-proxy acceleration.
12. For collective phase claims, run `pic runtime population-step` and
    `pic runtime collective-certify`; require fixed population, no self-rewrite,
    no hidden packet injection, accepted closure witnesses, execution-available
    paths, and a resource-matched baseline.
13. For external communication, run `pic agent communication-guide` and prefer
    offline fixtures for first runs. Live connectors are bounded and candidate-only
    by default when an explicit source is supplied; use `--no-allow-live-connectors`
    for local-only dry runs. Treat general web, feed, and peer-agent messages as
    packet candidates until downstream checks accept finite scope.

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

In v0.4.2, the workflow is closed-loop at the runtime and population levels.
`pic runtime step`
converts agent output into packets, builds edge witnesses, updates Psi, ranks
bottleneck and ECPT phase-control tasks, schedules work through SQOT, emits
verifier route requests, resolves inline evidence, promotes verified packet
capital, and returns `phase_acceleration_score` plus theory-facing summaries for
ECPT, BIT, and TRC. `pic runtime apply-results`
feeds task outcomes back into the event log and registry. `pic runtime compare`
and `pic runtime certify-acceleration` compare a candidate run to a
resource-matched baseline. These outputs accelerate protocol-relative
ASI-proxy phase-control evaluation and routing; they remain diagnostic or
provisional until verifier evidence discharges the relevant external
obligations.

For collective ECPT acceleration, do not optimize for packet count alone. Use
`pic ecology verify-edge` to check semantic packet relations, `pic ecology
paths` to confirm accepted packet paths into a basin contract, `pic runtime
execute-task` or `pic runtime run-agent-loop` to run only allowlisted actions,
and `pic runtime store` to preserve event logs and packet capital across
iterations. The runtime treats self-declared agent text and executor results as
observations until evidence routes and edge relation checks accept them.

`pic runtime collective-certify` adds the ECPT collective claim boundary:
ASI-proxy phase progress is a fixed-population packet percolation certificate,
not a self-rewrite certificate. A candidate certificate must show accepted
autocatalytic closure, execution availability without execution, bounded false
liquidity, bounded verifier backlog, SQOT reserve, non-rejecting hazard checks,
and no hidden capability injection.

## SDK and Service Paths

Agents that run in Python should call `build_runtime_step`,
`resolve_step_evidence`, `apply_action_results`, `compare_runtime_runs`,
`certify_runtime_acceleration`, `run_runtime_loop`, and `runtime_health`
directly. Agents written in other languages should use the schema bundle plus
either deterministic CLI JSON or the optional local HTTP service.

Production HTTP service usage requires `PIC_RUNTIME_TOKEN` bearer auth:

```powershell
$env:PIC_RUNTIME_TOKEN = "replace-with-local-token"
uv run pic runtime service --host 127.0.0.1 --port 8765 --profile production
```

The service remains local-first and does not use live connectors unless both
the service and the request explicitly allow them.
