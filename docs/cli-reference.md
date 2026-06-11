# CLI Reference

This page holds the full command inventory so the README can stay short. Commands emit deterministic JSON unless a command is explicitly starting a service.

## Installation

```powershell
uv sync --all-extras --dev
```

## Agent Shortcuts

```powershell
uv run pic agent explain
uv run pic agent manifest
uv run pic agent guide --profile development
uv run pic agent communication-guide --profile development --no-allow-live-connectors
uv run pic agent network-readiness --profile development --no-allow-live-connectors
uv run pic agent readiness --profile production
uv run pic agent doctor --profile development
uv run pic agent doctor --profile production
uv run pic agent intake --text "Candidate packet: route evidence and preserve residuals." --profile development
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development --output intake-report.json
uv run pic agent next --intake-report intake-report.json --profile development
uv run pic agent inbox init --inbox inbox.json
uv run pic agent message create --sender agent:alice --text "Candidate packet: preserve residuals." --output message.json
uv run pic agent message contract --message message.json
uv run pic agent message verify --message message.json --profile development
uv run pic agent message verify --message message.json --profile production --identity-context identity-context.json
uv run pic agent inbox append --inbox inbox.json --message message.json
uv run pic agent inbox export --inbox inbox.json
uv run pic agent message ingest --message examples/agent_network/agent_message.json
uv run pic agent message ingest --message examples/agent_network/agent_message.json --profile production --identity-context identity-context.json
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile production --identity-context identity-context.json
```

These commands do not perform network access or arbitrary shell execution. They orient agents, run a minimal runtime step, and preserve residual ledgers.

## Snapshot And Theory Inspection

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact ecpt
uv run pic snapshot show --artifact bit
uv run pic snapshot show --artifact trc
uv run pic snapshot show --artifact sqot
uv run pic snapshot show --artifact alt
uv run pic snapshot routes
uv run pic snapshot verify --artifact ecpt
uv run pic snapshot verify --artifact bit
uv run pic snapshot verify --artifact trc
uv run pic snapshot verify --artifact sqot
uv run pic snapshot verify --artifact alt
```

## Canonical TeX Audit

```powershell
$env:PIC_CANONICAL_TEX_DIR = "path\to\canonical\tex"
uv run pic extract --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex"
uv run pic check --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex" --canonical-key ecpt --strict-projection --derive-status
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex" --canonical-key ecpt --strict-grammar
uv run pic coverage --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex"
uv run pic parse audit --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --strict-grammar
uv run pic sqot audit --source "$env:PIC_CANONICAL_TEX_DIR\Salience-Queue Occupation Theory.tex" --strict-grammar
uv run pic alt audit --source "$env:PIC_CANONICAL_TEX_DIR\Abstraction Liquidity Theory.tex" --strict-grammar
```

## ALT Abstraction Liquidity

```powershell
uv run pic alt tokenize --trace examples/alt/trace.json
uv run pic alt check-token --token examples/alt/token_candidate.json
uv run pic alt check-transport --certificate examples/alt/transport_certificate.json
uv run pic alt certify-liquidity --certificate examples/alt/liquidity_certificate.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic alt negative-certify --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt deprecate --token-id alt-token:demo --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt resurrect --deprecation examples/alt/deprecation_record.json --packet examples/alt/admission_packet.json --override-failure-mode stale
uv run pic alt refresh-baseline --certificate examples/alt/baseline_refresh_certificate.json
uv run pic alt reproduction-report --certificate examples/alt/reproduction_certificate.json
uv run pic alt check-cara --certificate examples/alt/alt_cara_certificate.json
uv run pic alt foundry-dashboard --state examples/alt/foundry_state.json
uv run pic alt bridge-runtime --report examples/alt/runtime_bridge_report.json --state examples/runtime_state.json
```

## Schemas, Provenance, SBOM, Doctor

```powershell
uv run pic schema --type TheoryAuditReport
uv run pic schema --all --output-dir schemas
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
uv run pic sbom create --format pic --output pic-sbom.json
uv run pic sbom create --format cyclonedx --output cyclonedx.sbom.json
uv run pic doctor --fail-on never
uv run pic doctor --profile production --provenance provenance.json --fail-on fail
```

## Routes And Evidence

```powershell
uv run pic routes bindings
uv run pic routes explain --route adapters.domain.verify_trc_telemetry_calibration
uv run pic routes explain --route ecpt.adapters.proxy.verify_target_contract
uv run pic evidence verify --envelope examples/evidence_envelope.json
uv run pic evidence verify --envelope examples/evidence_envelope.json --profile production
uv run pic evidence discharge --envelope examples/evidence_envelope.json --obligations examples/external_obligations.json --profile production
uv run pic explain external def:null-channel-routing --from-snapshot
```

## Identity And Sybil Resistance

```powershell
uv run pic identity explain-profile --profile development
uv run pic identity explain-profile --profile production
uv run pic identity verify --identity examples/identity/agent_identity_alice.json
uv run pic identity verify-attestation --attestation examples/identity/packet_attestation.json --identities examples/identity/agent_identities.json
uv run pic identity sybil-check --population examples/agent_population_signed.json
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic identity sybil-check --population examples/identity/sybil_population_duplicate_key.json
uv run pic identity sybil-check --population examples/identity/sybil_population_clone_fanout.json
```

## ECPT Active Planning

```powershell
uv run pic ecpt plan --state examples/ecpt_phase_control_state.json --target examples/ecpt_asi_proxy_target.json --budget examples/ecpt_phase_control_budget.json --profile production
uv run pic ecpt simulate --state examples/ecpt_phase_control_state.json --actions examples/ecpt_phase_control_actions.json
uv run pic ecpt route-obligations --audit examples/theory_audit_summary.json
```

## SQOT Scheduling

```powershell
uv run pic sqot schedule --packets examples/sqot_queue.json --profile production
```

## Packet Ecology

```powershell
uv run pic ecology ingest --source examples/ecology_packets.json --kind local
uv run pic ecology policy explain --profile local_only
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology policy explain --profile production_network
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic ecology ingest-general --source examples/agent_network/packets.ndjson --kind ndjson
uv run pic ecology ingest-general --source examples/agent_network/inbox.json --kind agent-inbox
uv run pic ecology discover-web --source examples/agent_network/page.html
uv run pic ecology ingest-general --source https://example.org --kind web-page --allow-live-connectors
uv run pic ecology intake-audit --report examples/agent_network/general_intake_report.example.json
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic ecology build-edges --packets examples/ecology_packets.json --output ecology-registry.json
uv run pic ecology psi --registry ecology-registry.json --threshold examples/ecology_threshold.json --output ecology-psi.json
uv run pic ecology plan --registry ecology-registry.json --psi ecology-psi.json --profile production
uv run pic ecology paths --registry ecology-registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology closures --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology execution-paths --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology hidden-injection-check --registry examples/collective_packet_registry.json --events examples/walkthrough_collective_phase/empty-events.json --protocol examples/collective_protocol_frame.json
uv run pic ecology verify-edge --registry examples/ecology_packets.json --certificate examples/edge_relation_certificate.json
uv run pic ecology loop --state examples/ecology_loop_state.json --agent-output "SQOT reserve packet for ECPT active phase-control."
```

## Runtime

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production --identity-context identity-context.json
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input_with_evidence.json --profile production --output runtime-step.json
uv run pic runtime loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --max-steps 2 --profile production
uv run pic runtime resolve-evidence --input examples/runtime_step_input_with_evidence.json --profile production
uv run pic runtime execute-task --state examples/runtime_state.json --task examples/runtime_agent_task.json --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime execute-routes --requests examples/runtime_route_requests.json --evidence-store evidence-store --profile development
uv run pic runtime run-agent-loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --store runtime-loop.sqlite --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime apply-results --state examples/runtime_state.json --report runtime-step.json --results examples/runtime_action_results.json --output runtime-next-state.json
uv run pic runtime compare --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json --threshold examples/runtime_threshold.json
uv run pic runtime certify-acceleration --baseline examples/runtime_baseline_run.json --candidate examples/runtime_candidate_run.json
uv run pic runtime population-step --population examples/agent_population.json --inputs examples/runtime_loop_inputs.jsonl --profile production
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
uv run pic runtime collective-certify --profile production --population examples/agent_population_signed.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
uv run pic runtime health --state examples/runtime_state.json --profile production
uv run pic runtime export-openapi --output runtime-openapi.json
uv run pic runtime service --host 127.0.0.1 --port 8765 --profile production
```

## Runtime Store

```powershell
uv run pic runtime store init --store runtime.sqlite
uv run pic runtime store append --store runtime.sqlite --state examples/runtime_state.json
uv run pic runtime store load --store runtime.sqlite
uv run pic runtime store export --store runtime.sqlite --output runtime-store.json
```

## TRC Frontier Compilation And Demo

```powershell
uv run pic compile --records examples/frontier_records.json
uv run pic compile --records examples/minimal_invalid_main_frontier.json
uv run pic compile --records examples/minimal_invalid_main_frontier.json --fail-on invalid-main-trace
uv run pic demo datacenter
```

## Fixture Smoke Tests

```powershell
uv run pic check --source tests/fixtures/minimal_claims.tex --strict-projection --derive-status
uv run pic audit theory --source tests/fixtures/minimal_claims.tex --fail-on projection
uv run pic parse audit --source tests/fixtures/minimal_claims.tex --strict-grammar
uv run pic schema --all --output-dir schemas
```
