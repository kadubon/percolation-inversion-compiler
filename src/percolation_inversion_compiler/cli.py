"""Command-line interface for Percolation Inversion Compiler."""

from __future__ import annotations

import glob
import json
import os
import sys
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.acceleration import (
    PhaseAccelerationRequest,
    PhaseDashboardReport,
    build_phase_acceleration_benchmark,
    build_phase_acceleration_plan,
    build_phase_benchmark_suite,
    build_phase_dashboard,
    build_phase_observation,
    build_phase_trajectory,
    phase_acceleration_compact_payload,
    phase_acceleration_runbook,
    phase_benchmark_suite_markdown,
    phase_dashboard_markdown,
)
from percolation_inversion_compiler.adoption import (
    adoption_packet_markdown,
    build_agent_to_operator_request,
    build_operator_adoption_packet,
    operator_request_markdown,
)
from percolation_inversion_compiler.agent import (
    AgentIntakeReport,
    AgentIntakeRequest,
    accelerate_agent_phase,
    agent_autonomy_audit_markdown,
    agent_check_compact_payload,
    agent_feature_readiness,
    agent_manifest_payload,
    agent_network_readiness,
    agent_safety_invariants,
    build_agent_autonomy_audit,
    build_agent_communication_guide,
    build_agent_runbook,
    build_agent_workflow_guide,
    minimal_runtime_state,
    minimal_runtime_step_input,
    recommend_agent_next_actions,
    run_agent_check,
    run_agent_intake,
)
from percolation_inversion_compiler.alt import (
    ALTCARACertificate,
    ALTDeprecationRecord,
    BaselineRefreshCertificate,
    ExecutableALTCertificatePacket,
    FoundryState,
    LiquidityCertificate,
    NegativeLiquidityCertificate,
    ProblemSolvingTrace,
    ReproductionMatrixCertificate,
    TransportCertificate,
    admit_alt_packet,
    bridge_alt_to_runtime,
    build_abstraction_token_from_trace,
    check_alt_cara_certificate,
    check_baseline_refresh_certificate,
    check_liquidity_certificate,
    check_negative_liquidity_certificate,
    check_token_admissibility,
    check_transport_certificate,
    compute_alt_capital_impact,
    compute_alt_reproduction_report,
    compute_foundry_dashboard,
    deprecate_alt_packet,
    predict_foundry_phase_control,
    recommend_foundry_actions,
    resurrect_alt_candidate,
    verify_alt_ecpt_lift,
    verify_alt_liquidity_to_paths,
    verify_receiver_liquidity_lift,
)
from percolation_inversion_compiler.bit_engine import (
    BottleneckInversionCandidate,
    BottleneckInversionReport,
    build_inversion_certificate,
    compare_observation_baseline,
    diagnose_bottlenecks,
    invert_bottlenecks,
    minimal_enabling_conditions_for_bottleneck,
)
from percolation_inversion_compiler.core import (
    ExternalProofObligation,
    VerifierEvidenceEnvelope,
    binding_for_route,
    check_external_verifier_hook,
    list_adapter_route_specs,
    list_discharge_route_bindings,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.core.live_policy import default_allow_live_connectors
from percolation_inversion_compiler.ecology import (
    AgentInboxRecord,
    AgentMessageEnvelope,
    AgentMessageVerificationContext,
    CapabilityBasinContract,
    EdgeRelationVerifierSpec,
    EdgeWitnessCertificate,
    GeneralIntakePolicy,
    GeneralIntakeReport,
    GeneralIntakeRuntimeBridgeReport,
    GeneralIntakeSource,
    PacketPromotionPolicy,
    PacketSourceKind,
    ProtocolFrameDigest,
    PsiDashboard,
    WebFetchPolicy,
    agent_relay_readiness_report,
    append_agent_message,
    audit_general_intake_report,
    bridge_general_intake_to_runtime,
    build_bottleneck_plan,
    build_edge_witnesses,
    build_packet_registry,
    build_psi_dashboard,
    check_agent_message_contract,
    check_no_hidden_capability_injection,
    closed_loop_iteration,
    create_agent_message,
    deliver_agent_message,
    discover_web_packets,
    find_accepted_paths_to_basin,
    find_autocatalytic_closures,
    find_execution_available_paths,
    general_intake_policy_for_profile,
    infer_live_kind,
    ingest_agent_output,
    ingest_general_source,
    ingest_live_source,
    ingest_local_file,
    read_agent_inbox,
    receive_agent_inbox,
    registry_from_json,
    verify_agent_message,
    verify_edge_relation,
    write_agent_inbox,
)
from percolation_inversion_compiler.ecpt import (
    ASIProxyTargetContract,
    PhaseControlAction,
    PhaseControlObjective,
    PhaseControlState,
    build_phase_control_plan,
    reachable_mass,
)
from percolation_inversion_compiler.identity import (
    AgentIdentityAttestation,
    CryptographicAgentIdentity,
    check_sybil_resistance,
    sybil_policy_for_profile,
    verify_agent_attestation,
    verify_agent_identity,
)
from percolation_inversion_compiler.interop import (
    a2a_agent_card_report,
    a2a_task_handoff_report,
    activation_construction_report,
    alt_ecpt_bridge_report,
    baseline_envelope_check,
    bit_certificate_compiler_report,
    bit_mec_frontier_report,
    bit_registry_report,
    bit_tasks_from_registry,
    capital_witness_report,
    ccr_residuals_from_phase_plan,
    ccr_tasks_from_phase_plan,
    cegar_simulation_barrier_report,
    deployment_admissibility_report,
    diagnose_sqot_queue_state,
    dynamic_regime_acceleration_report,
    jsonl_text,
    mcp_tool_descriptor_report,
    mcp_tool_invocation_preflight,
    operation_gate_report,
    path_law_response_policy_report,
    phase_acceleration_report,
    phase_response_control_step,
    probe_stop_report,
    sqot_protocol_integrity_report,
    sqot_resource_exchange_report,
    target_validity_check,
    trace_check_report,
    trace_normal_form_report,
    trace_packet_candidate,
)
from percolation_inversion_compiler.io import (
    audit_canonical_suite,
    audit_theory_source,
    build_canonical_implementation_readiness_report,
    build_operational_readiness_report,
    build_sbom_document,
    build_theory_fidelity_report,
    canonical_implementation_readiness_markdown,
    canonical_manifest,
    count_mr_records_by_category,
    create_provenance_manifest,
    extract_artifact,
    extract_theory_coverage,
    find_snapshot_item,
    list_theory_snapshots,
    load_theory_snapshot,
    registry_json_schema,
    schema_bundle,
    schema_bundle_digest,
    schema_by_type,
    strict_tex_parse_report,
    theory_audit_cli_payload,
    validate_canonical_source,
    validate_data,
    verify_portability_conformance,
    verify_provenance_manifest,
)
from percolation_inversion_compiler.io.provenance import ProvenanceManifest
from percolation_inversion_compiler.io.schema import load_data
from percolation_inversion_compiler.packet_exchange import (
    PacketExchangeEnvelope,
    PacketMergeReport,
    inspect_packet_exchange_envelope,
    merge_packet_exchange_envelopes,
    packet_exchange_envelope_from_runtime_report,
    packet_lineage_digest,
)
from percolation_inversion_compiler.phase_lab import (
    ASIProxyThresholdSpec,
    EffectivePacketGraph,
    PhaseLabStore,
    PhaseWindowObservation,
    build_collective_phase_certificate_candidate,
    build_effective_packet_graph,
    build_threshold_status,
    compare_phase_windows,
    detect_autocatalytic_closure,
    detect_execution_available_paths,
    export_phase_lab_store,
    ingest_phase_lab_directory,
    ingest_phase_lab_paths,
    init_phase_lab_store,
    observe_phase_window,
)
from percolation_inversion_compiler.runtime import (
    ActionCommitPolicy,
    AgentPopulationState,
    AgentRuntimeConfig,
    AgentTask,
    FileEvidenceEnvelopeStore,
    RouteExecutionRequest,
    RuntimeActionResult,
    RuntimeExecutorPolicy,
    RuntimeIdentityContext,
    RuntimeRunReport,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
    SQLiteRuntimeStore,
    apply_action_results,
    build_population_runtime_step,
    build_runtime_step,
    certify_collective_phase,
    certify_runtime_acceleration,
    compare_runtime_runs,
    create_runtime_app,
    derive_runtime_identity_context,
    execute_route_batch,
    execute_runtime_task,
    resolve_step_evidence,
    run_agent_loop_with_store,
    run_runtime_loop,
    run_runtime_service,
    runtime_health,
)
from percolation_inversion_compiler.sqot import (
    DiagnosticReservePolicy,
    SalienceQueueRecord,
    build_salience_schedule,
)
from percolation_inversion_compiler.sqot_controller import (
    build_quarantine_decisions,
    build_queue_rebalance_plan,
    check_diagnostic_reserve,
    diagnose_queue_occupation,
    diagnose_salience_obstruction,
)
from percolation_inversion_compiler.trc import (
    action_boundary_from_runtime_report,
    adapt_tool_trace_events,
    adapt_trc_trace,
    compile_frontier,
    datacenter_demo,
)

app = typer.Typer(
    help="Finite certificate compiler toolkit for ECPT, BIT, TRC, SQOT, and ALT.",
    invoke_without_command=True,
)
demo_app = typer.Typer(help="Run bundled finite examples.")
audit_app = typer.Typer(help="Run source and theory audits.")
snapshot_app = typer.Typer(help="Inspect bundled derived theory snapshots.")
evidence_app = typer.Typer(help="Verify external evidence envelopes.")
routes_app = typer.Typer(help="Inspect verifier route bindings.")
provenance_app = typer.Typer(help="Create and verify release provenance manifests.")
sbom_app = typer.Typer(help="Create deterministic release SBOM documents.")
parse_app = typer.Typer(help="Run strict TeX parser diagnostics.")
portability_app = typer.Typer(help="Verify cross-language portability conformance packs.")
adoption_app = typer.Typer(help="Generate optional operator-adoption sidecars.")
phase_app = typer.Typer(help="Plan deterministic protocol-relative phase acceleration.")
phase_lab_app = typer.Typer(help="Run local Phase Ecology Lab diagnostics.")
phase_closure_app = typer.Typer(help="Find and certify effective graph closure candidates.")
packet_app = typer.Typer(help="Inspect and merge data-only packet-exchange sidecars.")
alt_app = typer.Typer(help="Run ALT abstraction-liquidity foundry tools.")
alt_bridge_app = typer.Typer(help="Bridge ALT diagnostics into adjacent protocol reports.")
bit_app = typer.Typer(help="Run practical BIT bottleneck inversion diagnostics.")
ecpt_app = typer.Typer(help="Run ECPT active phase-control planning tools.")
sqot_app = typer.Typer(help="Run SQOT salience-queue scheduling tools.")
mcp_app = typer.Typer(help="Check MCP tool descriptors and invocation preflights.")
a2a_app = typer.Typer(help="Check A2A agent cards and task handoffs.")
ecology_app = typer.Typer(help="Run ECPT capability packet ecology tools.")
ecology_policy_app = typer.Typer(help="Explain bounded general-intake policy presets.")
runtime_app = typer.Typer(help="Run ECPT active agent runtime loops and local service.")
runtime_store_app = typer.Typer(help="Manage persistent runtime stores.")
identity_app = typer.Typer(help="Verify cryptographic agent identities and Sybil ledgers.")
agent_app = typer.Typer(help="Agent-facing shortcuts for PIC runtime integration.")
agent_inbox_app = typer.Typer(help="Manage local agent inbox/outbox records.")
agent_message_app = typer.Typer(help="Create, verify, and ingest agent message envelopes.")
trc_app = typer.Typer(help="Run TRC typed trace adapter diagnostics.")
app.add_typer(demo_app, name="demo")
app.add_typer(audit_app, name="audit")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(evidence_app, name="evidence")
app.add_typer(routes_app, name="routes")
app.add_typer(provenance_app, name="provenance")
app.add_typer(sbom_app, name="sbom")
app.add_typer(parse_app, name="parse")
app.add_typer(portability_app, name="portability")
app.add_typer(adoption_app, name="adoption")
app.add_typer(phase_app, name="phase")
phase_app.add_typer(phase_lab_app, name="lab")
phase_app.add_typer(phase_closure_app, name="closure")
app.add_typer(packet_app, name="packet")
app.add_typer(alt_app, name="alt")
alt_app.add_typer(alt_bridge_app, name="bridge")
app.add_typer(bit_app, name="bit")
app.add_typer(ecpt_app, name="ecpt")
app.add_typer(sqot_app, name="sqot")
app.add_typer(mcp_app, name="mcp")
app.add_typer(a2a_app, name="a2a")
app.add_typer(ecology_app, name="ecology")
ecology_app.add_typer(ecology_policy_app, name="policy")
app.add_typer(runtime_app, name="runtime")
runtime_app.add_typer(runtime_store_app, name="store")
app.add_typer(identity_app, name="identity")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_inbox_app, name="inbox")
agent_app.add_typer(agent_message_app, name="message")
app.add_typer(trc_app, name="trc")
console = Console()


def _dump(data: Any, output: Path | None = None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, default=str)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        console.print_json(text)


def _dump_text(text: str, output: Path | None = None) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        console.print(text, end="", markup=False)


def _dump_jsonl(items: list[dict[str, Any]], output: Path | None = None) -> None:
    text = jsonl_text(items)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except (BrokenPipeError, OSError):
            raise typer.Exit(0) from None


def _output_format(value: str) -> str:
    normalized = value.lower()
    if normalized not in {"json", "markdown"}:
        raise typer.BadParameter("--format must be json or markdown")
    return normalized


def _language(value: str) -> str:
    normalized = value.lower()
    if normalized not in {"en", "ja"}:
        raise typer.BadParameter("--language must be en or ja")
    return normalized


def _expand_repeated_paths(paths: list[Path] | None, option_name: str) -> list[Path]:
    expanded: list[Path] = []
    for path in paths or []:
        raw = str(path)
        if any(marker in raw for marker in "*?["):
            matches = sorted(glob.glob(raw, recursive=True), key=lambda item: item.lower())
            if not matches:
                raise typer.BadParameter(f"{option_name} pattern matched no files: {raw}")
            for match in matches:
                parsed = Path(match)
                if not parsed.is_file():
                    raise typer.BadParameter(f"{option_name} pattern matched a non-file: {match}")
                expanded.append(parsed)
            continue
        expanded.append(path)
    return expanded


DEMO_RESOURCE_PACKAGE = "percolation_inversion_compiler.data.demo"


def _demo_resource_text(name: str) -> str:
    return (files(DEMO_RESOURCE_PACKAGE) / name).read_text(encoding="utf-8")


def _demo_manifest() -> dict[str, Any]:
    data = json.loads(_demo_resource_text("manifest.json"))
    if not isinstance(data, dict):
        raise RuntimeError("installed demo manifest must be a JSON object")
    return data


def _demo_file_names() -> list[str]:
    manifest = _demo_manifest()
    names = ["manifest.json"]
    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str):
            continue
        parsed = Path(path)
        if parsed.name != path or parsed.is_absolute():
            raise RuntimeError(f"unsafe installed demo path {path!r}")
        names.append(path)
    return sorted(set(names))


def _copy_installed_demo(output_dir: Path, overwrite: bool) -> list[str]:
    if output_dir.exists() and not output_dir.is_dir():
        raise typer.BadParameter("--output-dir must be a directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name in _demo_file_names():
        target = output_dir / name
        if target.exists() and not overwrite:
            raise typer.BadParameter(
                f"{target} already exists; pass --overwrite to replace installed demo files"
            )
        target.write_bytes((files(DEMO_RESOURCE_PACKAGE) / name).read_bytes())
        written.append(name)
    return written


def _load_phase_state(path: Path) -> tuple[PhaseControlState, list[PhaseControlAction]]:
    data = load_data(path)
    raw_state = data.get("state", data)
    state = PhaseControlState.model_validate(raw_state)
    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list):
        raise typer.BadParameter("state file actions must be a list when present")
    actions = [PhaseControlAction.model_validate(item) for item in raw_actions]
    return state, actions


def _load_phase_actions(path: Path) -> list[PhaseControlAction]:
    data = load_data(path)
    raw_actions = data.get("actions", data.get("phase_control_actions"))
    if not isinstance(raw_actions, list):
        raise typer.BadParameter("actions file must contain an actions list")
    return [PhaseControlAction.model_validate(item) for item in raw_actions]


def _load_phase_objective(path: Path, budget_data: dict[str, Any]) -> PhaseControlObjective:
    data = load_data(path)
    if "objective" in data:
        raw_objective = data["objective"]
        if not isinstance(raw_objective, dict):
            raise typer.BadParameter("target file objective must be an object")
        merged = dict(raw_objective)
        for key in ["horizon", "residual_budget", "risk_tolerance", "route_preferences"]:
            if key in budget_data:
                merged[key] = budget_data[key]
        return PhaseControlObjective.model_validate(merged)
    raw_target = data.get("target", data)
    target = ASIProxyTargetContract.model_validate(raw_target)
    return PhaseControlObjective(
        objective_id=str(budget_data.get("objective_id", f"objective:{target.target_id}")),
        target=target,
        horizon=int(budget_data.get("horizon", 1)),
        residual_budget=float(budget_data.get("residual_budget", 0.0)),
        risk_tolerance=float(budget_data.get("risk_tolerance", 0.0)),
        route_preferences=list(budget_data.get("route_preferences", [])),
    )


def _load_salience_records(path: Path) -> list[SalienceQueueRecord]:
    data = load_data(path)
    raw_records = data.get("records", data.get("queue", data.get("packets", [])))
    if not isinstance(raw_records, list):
        raise typer.BadParameter("salience input must contain records, queue, or packets list")
    records: list[SalienceQueueRecord] = []
    for item in raw_records:
        if not isinstance(item, dict):
            raise typer.BadParameter("salience records must be JSON objects")
        if "record_id" in item:
            records.append(SalienceQueueRecord.model_validate(item))
            continue
        packet_id = str(item.get("packet_id", item.get("id", "packet")))
        records.append(
            SalienceQueueRecord(
                record_id=packet_id,
                item_type="packet",
                salience_class=str(item.get("salience_class", "packet")),
                expected_downstream_gain=float(item.get("expected_downstream_gain", 0.0)),
                residual_reduction=max(0.0, 1.0 - float(item.get("residual_charge", 1.0))),
                verification_cost=float(item.get("verification_cost", 0.0)),
                freshness=float(item.get("freshness", 1.0)),
                obligation_ids=[str(value) for value in item.get("obligation_ids", [])],
                verifier_routes=[str(value) for value in item.get("verifier_routes", [])],
            )
        )
    return records


def _threshold_from_file(path: Path) -> dict[str, float]:
    data = load_data(path)
    raw_threshold = data.get("threshold", data)
    if not isinstance(raw_threshold, dict):
        raise typer.BadParameter("threshold file must contain an object")
    return {str(key): float(value) for key, value in raw_threshold.items()}


def _packet_source_kind(value: str) -> PacketSourceKind:
    try:
        return PacketSourceKind(value)
    except ValueError as exc:
        available = ", ".join(item.value for item in PacketSourceKind)
        raise typer.BadParameter(f"source kind must be one of: {available}") from exc


def _load_general_intake_policy(
    path: Path | None,
    *,
    profile: str = "development",
    allow_live_connectors: bool = default_allow_live_connectors(),
) -> GeneralIntakePolicy:
    if path is None:
        preset = general_intake_policy_for_profile(profile)
        return preset.model_copy(
            update={
                "allow_live_connectors": allow_live_connectors,
                "web_policy": preset.web_policy.model_copy(
                    update={"allow_live_connectors": allow_live_connectors}
                ),
            }
        )
    data = load_data(path)
    raw = data.get("general_intake_policy", data.get("policy", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("general intake policy file must contain an object")
    parsed = GeneralIntakePolicy.model_validate(raw)
    return parsed.model_copy(
        update={
            "profile": profile or parsed.profile,
            "allow_live_connectors": allow_live_connectors,
            "web_policy": parsed.web_policy.model_copy(
                update={"allow_live_connectors": allow_live_connectors}
            ),
        }
    )


def _load_agent_message(path: Path) -> AgentMessageEnvelope:
    data = load_data(path)
    raw = data.get("agent_message", data.get("message", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("agent message file must contain an object")
    return AgentMessageEnvelope.model_validate(raw)


def _load_general_intake_report(path: Path) -> GeneralIntakeReport:
    data = load_data(path)
    raw = data.get("general_intake_report", data.get("report", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("general intake report file must contain an object")
    return GeneralIntakeReport.model_validate(raw)


def _read_text_or_literal(source: str) -> str:
    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return source


def _runtime_config(
    *,
    profile: str,
    allow_live_connectors: bool,
    action_commit_policy: str,
    attention_budget: float,
    risk_budget: float,
    max_tasks: int,
) -> AgentRuntimeConfig:
    try:
        policy = ActionCommitPolicy(action_commit_policy)
    except ValueError as exc:
        raise typer.BadParameter(
            "--action-commit-policy must be recommend_only, "
            "require_verifier_resolution, or allow_finite_scope_commit"
        ) from exc
    return AgentRuntimeConfig(
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        action_commit_policy=policy,
        attention_budget=attention_budget,
        risk_budget=risk_budget,
        max_tasks=max_tasks,
    )


def _load_runtime_state(path: Path) -> RuntimeState:
    data = load_data(path)
    raw = data.get("runtime_state", data.get("state", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("runtime state file must contain an object")
    return RuntimeState.model_validate(raw)


def _load_runtime_identity_context(path: Path) -> RuntimeIdentityContext:
    data = load_data(path)
    raw = data.get("identity_context", data.get("runtime_identity_context", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("identity context file must contain an object")
    return RuntimeIdentityContext.model_validate(raw)


def _load_agent_message_verification_context(
    path: Path | None,
) -> AgentMessageVerificationContext | None:
    if path is None:
        return None
    context = _load_runtime_identity_context(path)
    return AgentMessageVerificationContext(
        profile=str(context.identity_profile),
        accepted=context.accepted,
        accepted_agent_ids=context.accepted_agent_ids,
        accepted_public_key_ids=context.accepted_public_key_ids,
        reasons=context.reasons,
    )


def _state_with_identity_context(
    state: RuntimeState,
    context: RuntimeIdentityContext | None,
) -> RuntimeState:
    if context is None:
        return state
    return state.model_copy(
        update={
            "accepted_agent_ids": context.accepted_agent_ids,
            "accepted_public_key_ids": context.accepted_public_key_ids,
            "identity_mode": "cryptographic" if context.accepted else "diagnostic",
        }
    )


def _load_runtime_step_input(path: Path) -> RuntimeStepInput:
    data = load_data(path)
    raw = data.get("runtime_input", data.get("input", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("runtime input file must contain an object")
    return RuntimeStepInput.model_validate(raw)


def _load_agent_default_state(state: Path | None) -> RuntimeState:
    if state is not None:
        return _load_runtime_state(state)
    default_state = Path("examples") / "runtime_state.json"
    if default_state.exists():
        return _load_runtime_state(default_state)
    return minimal_runtime_state()


def _load_runtime_step_report(path: Path) -> RuntimeStepReport:
    data = load_data(path)
    raw = data.get("runtime_step_report", data.get("report", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("runtime report file must contain an object")
    if raw.get("schema_version") == "ccr.pic_runtime_export.v1":
        return _runtime_step_report_from_ccr_export(raw)
    return RuntimeStepReport.model_validate(raw)


def _runtime_step_report_from_ccr_export(raw: dict[str, Any]) -> RuntimeStepReport:
    """Convert a CCR PIC export into PIC's runtime-step report shape."""

    report_id = str(raw.get("report_id") or "ccr-runtime-export")
    reasons = [
        *[str(item) for item in raw.get("candidate_only_reasons", [])],
        *[str(item) for item in raw.get("settled_blockers", [])],
    ]
    residual_refs = [
        str(item.get("residual_id", item))
        for item in raw.get("residuals", [])
        if isinstance(item, dict)
    ]
    text = (
        f"CCR runtime export {report_id}: candidate-only report with "
        f"{len(residual_refs)} residuals."
    )
    report = build_runtime_step(minimal_runtime_state(), minimal_runtime_step_input(text))
    return report.model_copy(
        update={
            "accepted": bool(raw.get("accepted", False)),
            "missing_obligations": sorted(set([*residual_refs, *reasons])),
            "operationally_usable": True,
            "reasons": sorted(set([*report.reasons, *reasons])),
            "report_id": report_id,
            "settled": False,
        }
    )


def _load_packet_exchange_envelope(path: Path) -> PacketExchangeEnvelope:
    data = load_data(path)
    raw = data.get("packet_exchange_envelope", data.get("packet", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("packet file must contain an object")
    return PacketExchangeEnvelope.model_validate(raw)


def _load_packet_or_merge(path: Path) -> PacketExchangeEnvelope | PacketMergeReport:
    data = load_data(path)
    raw_merge = data.get("packet_merge_report", data.get("merge_report"))
    if isinstance(raw_merge, dict):
        return PacketMergeReport.model_validate(raw_merge)
    if "packets" in data and "input_packet_count" in data:
        return PacketMergeReport.model_validate(data)
    raw_packet = data.get("packet_exchange_envelope", data.get("packet", data))
    if not isinstance(raw_packet, dict):
        raise typer.BadParameter("packet lineage input must contain a packet or merge report")
    return PacketExchangeEnvelope.model_validate(raw_packet)


def _load_phase_dashboard_report(path: Path) -> PhaseDashboardReport:
    data = load_data(path)
    raw = data.get("phase_dashboard_report", data.get("dashboard", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("phase dashboard file must contain an object")
    return PhaseDashboardReport.model_validate(raw)


def _load_effective_graph(path: Path) -> EffectivePacketGraph:
    data = load_data(path)
    raw = data.get("effective_packet_graph", data.get("graph", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("effective graph file must contain an object")
    return EffectivePacketGraph.model_validate(raw)


def _load_asi_proxy_threshold(path: Path) -> ASIProxyThresholdSpec:
    data = load_data(path)
    raw = data.get("asi_proxy_threshold", data.get("threshold", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("ASI-proxy threshold file must contain an object")
    return ASIProxyThresholdSpec.model_validate(raw)


def _load_bottleneck_report(path: Path) -> BottleneckInversionReport:
    data = load_data(path)
    raw = data.get("bottleneck_inversion_report", data.get("report", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("BIT bottleneck report file must contain an object")
    return BottleneckInversionReport.model_validate(raw)


def _load_inversion_candidate(path: Path) -> BottleneckInversionCandidate:
    data = load_data(path)
    raw = data.get("inversion_candidate", data.get("candidate", data))
    if isinstance(raw, dict) and "inversion_candidates" in raw:
        report = BottleneckInversionReport.model_validate(raw)
        if not report.inversion_candidates:
            raise typer.BadParameter("BIT report contains no inversion candidates")
        return report.inversion_candidates[0]
    if not isinstance(raw, dict):
        raise typer.BadParameter("BIT candidate file must contain an object")
    return BottleneckInversionCandidate.model_validate(raw)


def _load_jsonl_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if not isinstance(item, dict):
            raise typer.BadParameter(f"JSONL event on line {line_number} must be an object")
        events.append(item)
    return events


def _phase_lab_graph(store_path: Path, window: str = "latest") -> EffectivePacketGraph:
    store = PhaseLabStore(store_path)
    if window == "all":
        events = store.load_all_events()
        source_window_id = "all"
    else:
        selected, events = store.load_events(window)
        source_window_id = selected.window_id
    return build_effective_packet_graph(
        events,
        graph_id=f"effective-graph:{source_window_id}",
        source_window_id=source_window_id,
    ).graph


def _phase_lab_observation(
    store_path: Path,
    window: str = "latest",
) -> tuple[PhaseWindowObservation, EffectivePacketGraph]:
    store = PhaseLabStore(store_path)
    selected, events = store.load_events(window)
    graph = build_effective_packet_graph(
        events,
        graph_id=f"effective-graph:{selected.window_id}",
        source_window_id=selected.window_id,
    ).graph
    return observe_phase_window(selected, events, graph), graph


def _load_phase_acceleration_request(
    *,
    request_path: Path | None,
    runtime_report_path: Path | None,
    state_path: Path | None,
    step_input_path: Path | None,
    text: str | None,
    text_file: Path | None,
    profile: str | None,
    identity_context_path: Path | None,
    allow_live_connectors: bool | None,
    compact: bool,
) -> PhaseAccelerationRequest:
    if text is not None and text_file is not None:
        raise typer.BadParameter("Use either --text or --text-file, not both")
    if request_path is not None:
        if any(
            value is not None
            for value in (runtime_report_path, state_path, step_input_path, text, text_file)
        ):
            raise typer.BadParameter(
                "Use --request by itself, optionally with --profile, --compact, "
                "--identity-context, or --allow-live-connectors/--no-allow-live-connectors"
            )
        data = load_data(request_path)
        raw = data.get("phase_acceleration_request", data.get("request", data))
        if not isinstance(raw, dict):
            raise typer.BadParameter("phase acceleration request file must contain an object")
        parsed = PhaseAccelerationRequest.model_validate(raw)
        active_profile = profile or parsed.profile
        identity_context = (
            None
            if identity_context_path is None
            else _load_runtime_identity_context(identity_context_path)
        )
        runtime_config = parsed.runtime_config
        step_input = parsed.step_input
        if profile is not None and runtime_config is not None:
            runtime_config = runtime_config.model_copy(update={"profile": active_profile})
        if allow_live_connectors is not None:
            runtime_config = (
                runtime_config.model_copy(update={"allow_live_connectors": allow_live_connectors})
                if runtime_config is not None
                else AgentRuntimeConfig(
                    profile=active_profile,
                    allow_live_connectors=allow_live_connectors,
                )
            )
            step_input = (
                None
                if step_input is None
                else step_input.model_copy(update={"allow_live_connectors": allow_live_connectors})
            )
        return parsed.model_copy(
            update={
                "profile": active_profile,
                "runtime_config": runtime_config,
                "step_input": step_input,
                "identity_context": identity_context or parsed.identity_context,
                "compact": compact,
            }
        )
    active_profile = profile or "development"
    live_connectors = True if allow_live_connectors is None else allow_live_connectors
    identity_context = (
        None
        if identity_context_path is None
        else _load_runtime_identity_context(identity_context_path)
    )
    runtime_report = (
        None if runtime_report_path is None else _load_runtime_step_report(runtime_report_path)
    )
    agent_output = text_file.read_text(encoding="utf-8") if text_file is not None else text
    state = None if runtime_report is not None else _load_agent_default_state(state_path)
    step_input = None
    if runtime_report is None:
        step_input = (
            _load_runtime_step_input(step_input_path)
            if step_input_path is not None
            else minimal_runtime_step_input(agent_output)
        )
        if agent_output is not None and step_input_path is not None:
            step_input = step_input.model_copy(update={"agent_output": agent_output})
        step_input = step_input.model_copy(update={"allow_live_connectors": live_connectors})
    return PhaseAccelerationRequest(
        request_id="phase-cli",
        profile=active_profile,
        state=state,
        step_input=step_input,
        runtime_config=AgentRuntimeConfig(
            profile=active_profile,
            allow_live_connectors=live_connectors,
        ),
        runtime_report=runtime_report,
        identity_context=identity_context,
        compact=compact,
    )


def _load_runtime_action_results(path: Path) -> list[RuntimeActionResult]:
    data = load_data(path)
    raw = data.get("results", data.get("runtime_action_results"))
    if not isinstance(raw, list):
        raise typer.BadParameter("runtime results file must contain a results list")
    return [RuntimeActionResult.model_validate(item) for item in raw]


def _load_agent_task(path: Path) -> AgentTask:
    data = load_data(path)
    raw = data.get("agent_task", data.get("task", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("agent task file must contain an object")
    return AgentTask.model_validate(raw)


def _load_route_execution_requests(path: Path) -> list[RouteExecutionRequest]:
    data = load_data(path)
    raw = data.get("requests", data.get("route_execution_requests"))
    if not isinstance(raw, list):
        raise typer.BadParameter("route execution file must contain a requests list")
    return [RouteExecutionRequest.model_validate(item) for item in raw]


def _load_runtime_executor_policy(
    path: Path | None,
    *,
    profile: str = "development",
) -> RuntimeExecutorPolicy:
    if path is None:
        return RuntimeExecutorPolicy(profile=profile)
    data = load_data(path)
    raw = data.get("executor_policy", data.get("policy", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("executor policy file must contain an object")
    return RuntimeExecutorPolicy.model_validate(raw)


def _load_runtime_run_report(path: Path) -> RuntimeRunReport:
    data = load_data(path)
    raw = data.get("runtime_run_report", data.get("run", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("runtime run file must contain an object")
    return RuntimeRunReport.model_validate(raw)


def _load_agent_population_state(path: Path) -> AgentPopulationState:
    data = load_data(path)
    raw = data.get("population", data.get("agent_population", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("population file must contain an object")
    return AgentPopulationState.model_validate(raw)


def _load_agent_identity(path: Path) -> CryptographicAgentIdentity:
    data = load_data(path)
    raw = data.get("identity", data.get("cryptographic_agent_identity", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("identity file must contain an object")
    return CryptographicAgentIdentity.model_validate(raw)


def _load_agent_identities(path: Path) -> list[CryptographicAgentIdentity]:
    data = load_data(path)
    raw = data.get("identities", data.get("cryptographic_agent_identities", data))
    if isinstance(raw, dict):
        return [CryptographicAgentIdentity.model_validate(raw)]
    if not isinstance(raw, list):
        raise typer.BadParameter("identities file must contain an identities list")
    return [CryptographicAgentIdentity.model_validate(item) for item in raw]


def _load_identity_attestation(path: Path) -> AgentIdentityAttestation:
    data = load_data(path)
    raw = data.get("attestation", data.get("agent_identity_attestation", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("attestation file must contain an object")
    return AgentIdentityAttestation.model_validate(raw)


def _load_runtime_inputs(path: Path) -> list[RuntimeStepInput]:
    if path.suffix.lower() == ".jsonl":
        inputs: list[RuntimeStepInput] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise typer.BadParameter(f"invalid JSONL line {line_number}: {exc}") from exc
            inputs.append(RuntimeStepInput.model_validate(data))
        return inputs
    data = load_data(path)
    raw_inputs = data.get("inputs", data.get("runtime_inputs"))
    if not isinstance(raw_inputs, list):
        raise typer.BadParameter("runtime loop JSON must contain an inputs list")
    return [RuntimeStepInput.model_validate(item) for item in raw_inputs]


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show package version.", is_eager=True),
    ] = False,
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()


@app.command()
def doctor(
    fail_on: Annotated[
        str,
        typer.Option(
            "--fail-on",
            help="Exit nonzero on: fail, warn, or never.",
        ),
    ] = "fail",
    profile: Annotated[
        str,
        typer.Option("--profile", help="Readiness profile: development, research, or production."),
    ] = "development",
    provenance: Annotated[
        Path | None,
        typer.Option("--provenance", help="Verified provenance manifest JSON."),
    ] = None,
    required_route: Annotated[
        list[str] | None,
        typer.Option(
            "--required-route",
            help="Route id or verifier_route that must be production-ready for this run.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report operational readiness for CI and autonomous-agent runners."""

    if fail_on not in {"fail", "warn", "never"}:
        console.print("Error: --fail-on must be one of: fail, warn, never")
        raise typer.Exit(2)
    report = build_operational_readiness_report(
        profile=profile,
        provenance=provenance,
        required_routes=required_route,
    )
    _dump(report.model_dump(mode="json"), output)
    if fail_on == "fail" and report.overall_status == "fail":
        raise typer.Exit(1)
    if fail_on == "warn" and report.overall_status in {"fail", "warn"}:
        raise typer.Exit(1)


@app.command()
def extract(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Extract filecontents JSON, BIT MR records, and claim registries."""

    artifact = extract_artifact(source)
    registries = [registry.model_dump(mode="json") for registry in artifact.registries]
    data = {
        "source": artifact.source,
        "filecontents": [block.name for block in artifact.filecontents],
        "json_blocks": sorted(artifact.json_blocks),
        "mr_record_count": len(artifact.mr_records),
        "mr_record_counts": count_mr_records_by_category(artifact.mr_records),
        "registry_count": len(artifact.registries),
        "claim_count": sum(len(registry.claims) for registry in artifact.registries),
        "registries": registries,
    }
    _dump(data, output)


@app.command()
def validate(
    registry: Annotated[Path, typer.Option("--registry", "-r", help="Registry JSON/YAML file.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Validate a registry-like JSON/YAML object against the public schema."""

    data = load_data(registry)
    errors = validate_data(data)
    result = {"registry": str(registry), "valid": not errors, "errors": errors}
    _dump(result, output)
    if errors:
        raise typer.Exit(1)


@app.command()
def schema(
    type_name: Annotated[
        str, typer.Option("--type", help="Public schema type to emit.")
    ] = "Registry",
    all_schemas: Annotated[
        bool,
        typer.Option("--all", help="Emit the full portability schema bundle."),
    ] = False,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write one schema file per public type."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON Schema.")
    ] = None,
) -> None:
    """Emit a public JSON Schema."""

    try:
        if all_schemas:
            bundle = schema_bundle()
            if output_dir is not None:
                output_dir.mkdir(parents=True, exist_ok=True)
                for name, schema_data in bundle.schemas.items():
                    (output_dir / f"{name}.schema.json").write_text(
                        json.dumps(schema_data, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                (output_dir / "bundle.schema.json").write_text(
                    json.dumps(bundle.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                digest = schema_bundle_digest(output_dir, base_dir=output_dir.parent)
                (output_dir / "schema-digest.json").write_text(
                    json.dumps(digest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                return
            _dump(bundle.model_dump(mode="json"), output)
            return
        schema_data = (
            registry_json_schema() if type_name == "Registry" else schema_by_type(type_name)
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(schema_data, output)


@app.command()
def check(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    canonical_key: Annotated[
        str | None,
        typer.Option("--canonical-key", help="Canonical key: ecpt, bit, trc, sqot, or alt."),
    ] = None,
    strict_projection: Annotated[
        bool,
        typer.Option(
            "--strict-projection",
            help="Compare stable registry fields against extractor judgments.",
        ),
    ] = False,
    derive_status: Annotated[
        bool,
        typer.Option("--derive-status", help="Include checker-derived status summary."),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run extraction, uniqueness, and optional canonical MD5 checks."""

    artifact = extract_artifact(source)
    results: dict[str, Any] = {
        "source": str(source),
        "registries": [],
        "valid": True,
        "errors": [],
    }
    if derive_status:
        derived: dict[str, int] = {}
        for judgment in artifact.extractor_output().judgments:
            key = judgment.derived_status.value
            derived[key] = derived.get(key, 0) + 1
        results["derived_status_summary"] = dict(sorted(derived.items()))
    for registry in artifact.registries:
        try:
            registry.require_unique_claim_ids()
            projection = artifact.extractor_output().check_registry_projection(
                registry,
                strict=strict_projection,
            )
            results["registries"].append(
                {
                    "artifact": registry.artifact,
                    "schema_version": registry.schema_version,
                    "claim_count": len(registry.claims),
                    "unique": True,
                    "projection_sound": projection.accepted,
                    "strict_projection": strict_projection,
                }
            )
            if not projection.accepted:
                results["valid"] = False
                results["errors"].extend(projection.reasons)
        except ValueError as exc:
            results["valid"] = False
            results["errors"].append(str(exc))
    if canonical_key is not None:
        canonical = validate_canonical_source(source, canonical_key)
        results["canonical"] = canonical
        if not canonical["matches"]:
            results["valid"] = False
            results["errors"].append("canonical checksum mismatch")
    _dump(results, output)
    if not results["valid"]:
        raise typer.Exit(1)


@app.command()
def coverage(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit definition, claim, and MRRecord coverage for a TeX artifact."""

    record = extract_theory_coverage(source)
    _dump(record.model_dump(mode="json"), output)


@audit_app.command("theory")
def audit_theory(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    canonical_key: Annotated[
        str | None,
        typer.Option("--canonical-key", help="Canonical key: ecpt, bit, or trc."),
    ] = None,
    strict_projection: Annotated[
        bool,
        typer.Option(
            "--strict-projection/--no-strict-projection",
            help="Compare stable registry fields against extractor judgments.",
        ),
    ] = True,
    strict_maturity: Annotated[
        bool,
        typer.Option(
            "--strict-maturity/--no-strict-maturity",
            help="Treat maturity/provenance downgrades as audit-relevant metadata.",
        ),
    ] = False,
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Diagnose unsupported theorem-like or MRRecord source syntax.",
        ),
    ] = False,
    fail_on: Annotated[
        list[str] | None,
        typer.Option(
            "--fail-on",
            help=(
                "Fail when audit contains: unsupported, external, projection, canonical, "
                "or snapshot."
            ),
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit a JSON-first theory, coverage, projection, and obligation audit."""

    report = audit_theory_source(
        source,
        canonical_key=canonical_key,
        strict_projection=strict_projection,
    )
    data = report.model_dump(mode="json")
    data["strict_maturity"] = strict_maturity
    grammar_report = strict_tex_parse_report(source) if strict_grammar else None
    if grammar_report is not None:
        data["strict_grammar"] = grammar_report.model_dump(mode="json")
    _dump(data, output)
    fail_reasons = set(fail_on or [])
    fail = not report.accepted
    if "projection" in fail_reasons and any(
        not audit.accepted for audit in report.projection_audits
    ):
        fail = True
    if (
        "canonical" in fail_reasons
        and report.canonical is not None
        and not report.canonical.get("matches")
    ):
        fail = True
    if "unsupported" in fail_reasons and report.unsupported_items:
        fail = True
    if "external" in fail_reasons and report.external_obligation_items:
        fail = True
    if "snapshot" in fail_reasons and report.snapshot_delta:
        counts_match = bool(report.snapshot_delta.get("coverage_counts_match", True))
        external_match = bool(report.snapshot_delta.get("external_category_summary_match", True))
        if not counts_match or not external_match:
            fail = True
    if "provenance" in fail_reasons and (
        report.canonical is None or not bool(report.canonical.get("matches", False))
    ):
        fail = True
    if grammar_report is not None and not grammar_report.accepted:
        fail = True
    if fail:
        raise typer.Exit(1)


@audit_app.command("canonical-suite")
def audit_canonical_suite_command(
    canonical_dir: Annotated[
        Path,
        typer.Option(
            "--canonical-dir",
            help="Directory containing ECPT, BIT, TRC, SQOT, and ALT canonical TeX files.",
        ),
    ],
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Exit nonzero on: fail or never."),
    ] = "fail",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Audit the complete canonical ECPT/BIT/TRC/SQOT/ALT source suite."""

    if fail_on not in {"fail", "never"}:
        console.print("Error: --fail-on must be one of: fail, never")
        raise typer.Exit(2)
    report = audit_canonical_suite(canonical_dir)
    _dump(report.model_dump(mode="json"), output)
    if fail_on == "fail" and not report.accepted:
        raise typer.Exit(1)


@audit_app.command("fidelity")
def audit_fidelity_command(
    canonical_dir: Annotated[
        Path,
        typer.Option(
            "--canonical-dir",
            help="Directory containing ECPT, BIT, TRC, SQOT, and ALT canonical TeX files.",
        ),
    ],
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Exit nonzero on: fail or never."),
    ] = "fail",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Summarize canonical-suite theory fidelity and finite upgrade candidates."""

    if fail_on not in {"fail", "never"}:
        console.print("Error: --fail-on must be one of: fail, never")
        raise typer.Exit(2)
    report = build_theory_fidelity_report(canonical_dir)
    _dump(report.model_dump(mode="json"), output)
    if fail_on == "fail" and not report.accepted:
        raise typer.Exit(1)


@audit_app.command("canonical-readiness")
def audit_canonical_readiness_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile label to include in the report."),
    ] = "development",
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: json or markdown."),
    ] = "json",
    language: Annotated[
        str,
        typer.Option("--language", help="Markdown language: en or ja."),
    ] = "en",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write output.")] = None,
) -> None:
    """Report pip-safe canonical readiness from bundled derived snapshots."""

    report = build_canonical_implementation_readiness_report(profile)
    if _output_format(output_format) == "markdown":
        _dump_text(
            canonical_implementation_readiness_markdown(report, language=_language(language)),
            output,
        )
        return
    _dump(report.model_dump(mode="json"), output)


@snapshot_app.command("list")
def snapshot_list(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """List bundled derived snapshots without requiring canonical TeX files."""

    snapshots = list_theory_snapshots()
    data = {
        "snapshots": [
            {
                "artifact_key": snapshot.artifact_key,
                "artifact": snapshot.artifact,
                "doi": snapshot.attribution.doi,
                "coverage_counts": snapshot.coverage_counts,
                "external_obligation_category_summary": (
                    snapshot.external_obligation_category_summary
                ),
            }
            for snapshot in snapshots
        ]
    }
    _dump(data, output)


@portability_app.command("verify")
def portability_verify_command(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", help="Portability conformance manifest JSON/YAML."),
    ],
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Exit nonzero on: fail or never."),
    ] = "fail",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Validate golden portability examples against exported public schemas."""

    if fail_on not in {"fail", "never"}:
        console.print("Error: --fail-on must be one of: fail, never")
        raise typer.Exit(2)
    report = verify_portability_conformance(manifest)
    _dump(report.model_dump(mode="json"), output)
    if fail_on == "fail" and not report.accepted:
        raise typer.Exit(1)


@snapshot_app.command("show")
def snapshot_show(
    artifact: Annotated[
        str,
        typer.Option(
            "--artifact",
            "-a",
            help="Snapshot artifact key: ecpt, bit, trc, sqot, or alt.",
        ),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Show one bundled derived theory snapshot."""

    try:
        snapshot = load_theory_snapshot(artifact)
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"unknown snapshot artifact {artifact!r}") from exc
    _dump(snapshot.model_dump(mode="json"), output)


@snapshot_app.command("routes")
def snapshot_routes(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Show adapter route specs for external verifier obligations."""

    _dump(
        {"routes": [spec.model_dump(mode="json") for spec in list_adapter_route_specs()]},
        output,
    )


@routes_app.command("bindings")
def route_bindings(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Show reviewed canonical-to-implementation discharge route bindings."""

    _dump(
        {
            "bindings": [
                binding.model_dump(mode="json") for binding in list_discharge_route_bindings()
            ]
        },
        output,
    )


@routes_app.command("explain")
def route_explain(
    route: Annotated[
        str,
        typer.Option("--route", help="Route id or verifier_route to explain."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Explain one verifier route binding and its settlement scope."""

    specs = {
        key: spec
        for spec in list_adapter_route_specs()
        for key in {spec.route_id, spec.verifier_route}
    }
    spec = specs.get(route)
    if spec is None:
        raise typer.BadParameter(f"unknown adapter route {route!r}")
    binding = binding_for_route(spec.route_id)
    data = {
        "route": spec.model_dump(mode="json"),
        "binding": None if binding is None else binding.model_dump(mode="json"),
        "settled_scope": [] if binding is None else binding.settlement_scope,
        "finite_scope_usable": (
            spec.discharge_level.value != "external_domain_required"
            if binding is None
            else binding.discharge_level.value != "external_domain_required"
        ),
        "residual_external_obligations": []
        if binding is None
        else binding.residual_external_obligation_refs,
        "required_evidence_kind": spec.required_evidence_kind,
    }
    _dump(data, output)


@provenance_app.command("create")
def provenance_create(
    schema_dir: Annotated[
        Path | None,
        typer.Option("--schema-dir", help="Directory containing generated schema JSON files."),
    ] = None,
    sbom_ref: Annotated[
        str | None,
        typer.Option("--sbom-ref", help="Optional SBOM release-asset reference."),
    ] = None,
    artifact_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--artifact-ref",
            help="Additional release artifact path to include in the manifest.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write provenance manifest JSON.")
    ] = None,
) -> None:
    """Create a deterministic SHA-256 provenance manifest."""

    manifest = create_provenance_manifest(
        schema_dir=schema_dir,
        sbom_ref=sbom_ref,
        artifact_refs=artifact_ref,
    )
    _dump(manifest.model_dump(mode="json"), output)


@provenance_app.command("verify")
def provenance_verify(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", "-m", help="Provenance manifest JSON."),
    ],
    require_attestation: Annotated[
        bool,
        typer.Option(
            "--require-attestation/--no-require-attestation",
            help="Require attestation metadata in addition to local SHA-256 checks.",
        ),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write verification JSON.")
    ] = None,
) -> None:
    """Verify a deterministic provenance manifest against local files."""

    data = load_data(manifest)
    parsed = ProvenanceManifest.model_validate(data)
    valid, reasons = verify_provenance_manifest(
        parsed,
        require_attestation=require_attestation,
    )
    _dump(
        {
            "manifest": str(manifest),
            "require_attestation": require_attestation,
            "valid": valid,
            "reasons": reasons,
        },
        output,
    )
    if not valid:
        raise typer.Exit(1)


@snapshot_app.command("verify")
def snapshot_verify(
    artifact: Annotated[
        str,
        typer.Option("--artifact", "-a", help="Snapshot artifact key: ecpt, bit, trc, or sqot."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify derived snapshot attribution against the canonical manifest metadata."""

    snapshot = load_theory_snapshot(artifact)
    manifest = canonical_manifest()
    record = manifest.records.get(snapshot.artifact_key)
    valid = record is not None and snapshot.attribution.doi == record.doi
    data = {
        "artifact_key": snapshot.artifact_key,
        "valid": valid,
        "snapshot_schema_version": snapshot.schema_version,
        "canonical_manifest_schema_version": manifest.schema_version,
        "doi_matches": bool(record and snapshot.attribution.doi == record.doi),
        "legacy_md5_matches": bool(
            record and snapshot.attribution.source_tex_md5 == record.tex_md5_legacy
        ),
        "canonical_sha256": None if record is None else record.tex_sha256,
        "snapshot_is_derived_metadata": True,
    }
    _dump(data, output)
    if not valid:
        raise typer.Exit(1)


@sbom_app.command("create")
def sbom_create(
    format_name: Annotated[
        str,
        typer.Option("--format", help="SBOM format: pic or cyclonedx."),
    ] = "pic",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write SBOM JSON output.")
    ] = None,
) -> None:
    """Create a deterministic SBOM document."""

    try:
        document = build_sbom_document(format_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(document, output)


@parse_app.command("audit")
def parse_audit(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Exit nonzero on strict grammar diagnostics.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run strict TeX parser diagnostics."""

    report = strict_tex_parse_report(source)
    _dump(report.model_dump(mode="json"), output)
    if strict_grammar and not report.accepted:
        raise typer.Exit(1)


@alt_app.command("audit")
def alt_audit(
    source: Annotated[Path, typer.Option("--source", "-s", help="ALT TeX source artifact.")],
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Exit nonzero on strict grammar diagnostics.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Audit ALT source coverage and strict parser compatibility."""

    canonical_key = "alt" if source.name == "Abstraction Liquidity Theory.tex" else None
    data = theory_audit_cli_payload(
        source,
        canonical_key=canonical_key,
        safety_invariants=[
            "ALT audit classifies finite checker coverage and external obligations",
            "ALT audit output does not prove real ASI or external-world outcomes",
            "TeX/PDF sources are not vendored by this command",
        ],
    )
    _dump(data, output)
    grammar = data["strict_grammar"]
    if strict_grammar and isinstance(grammar, dict) and not bool(grammar.get("accepted")):
        raise typer.Exit(1)


@alt_app.command("tokenize")
def alt_tokenize(
    trace: Annotated[Path, typer.Option("--trace", help="ProblemSolvingTrace JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build an ALT abstraction token candidate from a finite trace."""

    token = build_abstraction_token_from_trace(ProblemSolvingTrace.model_validate(load_data(trace)))
    _dump(token.model_dump(mode="json"), output)


@alt_app.command("check-token")
def alt_check_token(
    token: Annotated[Path, typer.Option("--token", help="AbstractionToken JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check ALT token admissibility without promoting status."""

    from percolation_inversion_compiler.alt import AbstractionToken

    result = check_token_admissibility(AbstractionToken.model_validate(load_data(token)))
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("check-transport")
def alt_check_transport(
    certificate: Annotated[
        Path, typer.Option("--certificate", help="TransportCertificate JSON/YAML.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an ALT finite transport certificate."""

    result = check_transport_certificate(
        TransportCertificate.model_validate(load_data(certificate))
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("certify-liquidity")
def alt_certify_liquidity(
    certificate: Annotated[
        Path, typer.Option("--certificate", help="LiquidityCertificate JSON/YAML.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an ALT liquidity certificate and signed surplus lower bound."""

    result = check_liquidity_certificate(
        LiquidityCertificate.model_validate(load_data(certificate))
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("negative-certify")
def alt_negative_certify(
    certificate: Annotated[
        Path, typer.Option("--certificate", help="NegativeLiquidityCertificate JSON/YAML.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an ALT negative-liquidity certificate for scoped pruning."""

    result = check_negative_liquidity_certificate(
        NegativeLiquidityCertificate.model_validate(load_data(certificate))
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("deprecate")
def alt_deprecate(
    token_id: Annotated[str, typer.Option("--token-id", help="Token id to deprecate.")],
    certificate: Annotated[
        Path, typer.Option("--certificate", help="NegativeLiquidityCertificate JSON/YAML.")
    ],
    rollback_ref: Annotated[
        list[str] | None,
        typer.Option("--rollback-ref", help="Rollback/deactivation evidence ref."),
    ] = None,
    lineage_ref: Annotated[
        list[str] | None,
        typer.Option("--lineage-ref", help="Lineage ref to preserve."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Create a scoped ALT deprecation record."""

    result = deprecate_alt_packet(
        token_id,
        NegativeLiquidityCertificate.model_validate(load_data(certificate)),
        rollback_refs=rollback_ref,
        lineage_refs=lineage_ref,
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("resurrect")
def alt_resurrect(
    deprecation: Annotated[
        Path, typer.Option("--deprecation", help="ALTDeprecationRecord JSON/YAML.")
    ],
    packet: Annotated[
        Path, typer.Option("--packet", help="ExecutableALTCertificatePacket JSON/YAML.")
    ],
    override_failure_mode: Annotated[
        str, typer.Option("--override-failure-mode", help="Prior failure mode to override.")
    ],
    evidence_ref: Annotated[
        list[str] | None,
        typer.Option("--evidence-ref", help="Evidence ref supporting resurrection."),
    ] = None,
    profile: Annotated[str, typer.Option("--profile", help="Admission profile.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Resurrect a deprecated token as a candidate after current positive checks."""

    result = resurrect_alt_candidate(
        ALTDeprecationRecord.model_validate(load_data(deprecation)),
        ExecutableALTCertificatePacket.model_validate(load_data(packet)),
        override_failure_mode=override_failure_mode,
        evidence_refs=evidence_ref,
        profile=profile,
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("refresh-baseline")
def alt_refresh_baseline(
    certificate: Annotated[
        Path, typer.Option("--certificate", help="BaselineRefreshCertificate JSON/YAML.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an ALT baseline/opportunity-law refresh certificate."""

    result = check_baseline_refresh_certificate(
        BaselineRefreshCertificate.model_validate(load_data(certificate))
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("reproduction-report")
def alt_reproduction_report(
    certificate: Annotated[
        Path, typer.Option("--certificate", help="ReproductionMatrixCertificate JSON/YAML.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check finite ALT reproduction matrix diagnostics."""

    result = compute_alt_reproduction_report(
        ReproductionMatrixCertificate.model_validate(load_data(certificate))
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("check-cara")
def alt_check_cara(
    certificate: Annotated[
        Path, typer.Option("--certificate", help="ALTCARACertificate JSON/YAML.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check target-valid ALT-CARA finite acceleration evidence."""

    result = check_alt_cara_certificate(ALTCARACertificate.model_validate(load_data(certificate)))
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("admit")
def alt_admit(
    packet: Annotated[
        Path, typer.Option("--packet", help="ExecutableALTCertificatePacket JSON/YAML.")
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Admission profile: development, research, production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run fail-closed ALT packet admission."""

    result = admit_alt_packet(
        ExecutableALTCertificatePacket.model_validate(load_data(packet)),
        profile=profile,
    )
    _dump(result.model_dump(mode="json"), output)


@alt_app.command("foundry-dashboard")
def alt_foundry_dashboard(
    state: Annotated[Path, typer.Option("--state", help="FoundryState JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compute an ALT foundry bottleneck dashboard."""

    dashboard = compute_foundry_dashboard(FoundryState.model_validate(load_data(state)))
    data = dashboard.model_dump(mode="json")
    data["predicted_phase_control_rule"] = predict_foundry_phase_control(dashboard).value
    data["recommended_foundry_actions"] = recommend_foundry_actions(dashboard)
    _dump(data, output)


@alt_app.command("bridge-runtime")
def alt_bridge_runtime(
    report: Annotated[
        Path,
        typer.Option("--report", help="GeneralIntakeRuntimeBridgeReport JSON/YAML."),
    ],
    state: Annotated[Path, typer.Option("--state", help="RuntimeState JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build an ALT foundry sidecar from candidate-only runtime intake."""

    foundry = bridge_alt_to_runtime(
        GeneralIntakeRuntimeBridgeReport.model_validate(load_data(report)),
        RuntimeState.model_validate(load_data(state)),
    )
    _dump(foundry.model_dump(mode="json"), output)


@alt_bridge_app.command("ecpt")
def alt_bridge_ecpt_command(
    packet: Annotated[Path, typer.Option("--packet", help="ALT packet/report JSON/YAML.")],
    profile: Annotated[str, typer.Option("--profile", help="Bridge profile.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a conservative ALT-to-ECPT bridge report."""

    report = alt_ecpt_bridge_report(load_data(packet), profile=profile)
    _dump(report, output)


@alt_app.command("ecpt-lift")
def alt_ecpt_lift_command(
    packets: Annotated[
        list[Path],
        typer.Option(
            "--packets",
            help="ALT packet/report JSON/YAML. May repeat; literal patterns are expanded by PIC.",
        ),
    ],
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check whether ALT artifacts lift into ECPT phase proxy components."""

    packet_data = [load_data(path) for path in _expand_repeated_paths(packets, "--packets")]
    report = verify_alt_ecpt_lift(packet_data, _load_effective_graph(graph))
    _dump(report.model_dump(mode="json"), output)


@alt_app.command("receiver-lift")
def alt_receiver_lift_command(
    packet: Annotated[Path, typer.Option("--packet", help="ALT packet/report JSON/YAML.")],
    receiver_context: Annotated[
        Path,
        typer.Option("--receiver-context", help="Receiver context JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check receiver-context liquidity lift for one ALT artifact."""

    lift = verify_receiver_liquidity_lift(load_data(packet), load_data(receiver_context))
    _dump(lift.model_dump(mode="json"), output)


@alt_app.command("liquidity-to-paths")
def alt_liquidity_to_paths_command(
    packet: Annotated[Path, typer.Option("--packet", help="ALT packet/report JSON/YAML.")],
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check ALT liquidity contribution to execution path density."""

    report = verify_alt_liquidity_to_paths(load_data(packet), _load_effective_graph(graph))
    _dump(report.model_dump(mode="json"), output)


@alt_app.command("capital-impact")
def alt_capital_impact_command(
    reports: Annotated[
        list[Path],
        typer.Option(
            "--reports",
            help=(
                "ALT lift/admission report JSON/YAML. May repeat; "
                "literal patterns are expanded by PIC."
            ),
        ),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Summarize diagnostic ALT capital impact reports."""

    payloads = [load_data(path) for path in _expand_repeated_paths(reports, "--reports")]
    report = compute_alt_capital_impact(payloads)
    _dump(report.model_dump(mode="json"), output)


@bit_app.command("diagnose")
def bit_diagnose_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Diagnose bottlenecks from an effective packet graph."""

    report = diagnose_bottlenecks(_load_effective_graph(graph))
    _dump(report.model_dump(mode="json"), output)


@bit_app.command("invert")
def bit_invert_command(
    bottlenecks: Annotated[
        Path,
        typer.Option("--bottlenecks", help="BottleneckInversionReport JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build recommendation-only inversion candidates."""

    report = invert_bottlenecks(_load_bottleneck_report(bottlenecks))
    _dump(report.model_dump(mode="json"), output)


@bit_app.command("mec")
def bit_mec_command(
    bottleneck: Annotated[str, typer.Option("--bottleneck", help="Bottleneck id.")],
    bottlenecks: Annotated[
        Path | None,
        typer.Option("--bottlenecks", help="Optional BottleneckInversionReport JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit minimal enabling conditions for one bottleneck."""

    report = None if bottlenecks is None else _load_bottleneck_report(bottlenecks)
    conditions = minimal_enabling_conditions_for_bottleneck(bottleneck, report)
    _dump(
        {"minimal_enabling_conditions": [item.model_dump(mode="json") for item in conditions]},
        output,
    )


@bit_app.command("certificate")
def bit_certificate_command(
    candidate: Annotated[
        Path,
        typer.Option("--candidate", help="BottleneckInversionCandidate or report JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a fail-closed inversion certificate candidate."""

    certificate = build_inversion_certificate(_load_inversion_candidate(candidate))
    _dump(certificate.model_dump(mode="json"), output)


@bit_app.command("compare-baseline")
def bit_compare_baseline_command(
    baseline: Annotated[Path, typer.Option("--baseline", help="PhaseWindowObservation JSON/YAML.")],
    candidate: Annotated[
        Path,
        typer.Option("--candidate", help="PhaseWindowObservation JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compare observations for protocol-relative activation gain."""

    baseline_observation = PhaseWindowObservation.model_validate(load_data(baseline))
    candidate_observation = PhaseWindowObservation.model_validate(load_data(candidate))
    report = compare_observation_baseline(baseline_observation, candidate_observation)
    _dump(report.model_dump(mode="json"), output)


@bit_app.command("extract-registry")
def bit_extract_registry_command(
    source: Annotated[Path, typer.Option("--source", help="TeX-like source file.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write registry JSONL.")
    ] = None,
) -> None:
    """Extract BIT MRRecord registry rows as JSONL."""

    report = bit_registry_report(source.read_text(encoding="utf-8"), source=str(source))
    _dump_jsonl(report["records"], output)


@bit_app.command("verify-witnesses")
def bit_verify_witnesses_command(
    registry: Annotated[Path, typer.Option("--registry", help="Registry JSONL file.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify MRRecord witness coverage without failing on malformed lines."""

    records = _load_jsonl_events(registry)
    report = _bit_report_from_registry_records(records, source=str(registry))
    report["accepted"] = not report["missing_witness_claims"]
    report["settled"] = False
    _dump(report, output)


@bit_app.command("emit-ccr-tasks")
def bit_emit_ccr_tasks_command(
    registry: Annotated[Path, typer.Option("--registry", help="Registry JSONL file.")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write task JSONL.")] = None,
) -> None:
    """Emit CCR tasks for BIT claims without witnesses."""

    records = _load_jsonl_events(registry)
    report = _bit_report_from_registry_records(records, source=str(registry))
    _dump_jsonl(bit_tasks_from_registry(report), output)


def _bit_report_from_registry_records(
    records: list[dict[str, Any]],
    *,
    source: str,
) -> dict[str, Any]:
    report = bit_registry_report(
        "\n".join(str(record.get("raw_line", "")) for record in records),
        source=source,
    )
    report["records"] = records
    return report


@sqot_app.command("audit")
def sqot_audit(
    source: Annotated[Path, typer.Option("--source", "-s", help="SQOT TeX source artifact.")],
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Exit nonzero on strict grammar diagnostics.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Audit SQOT source coverage and strict parser compatibility."""

    canonical_key = "sqot" if source.name == "Salience-Queue Occupation Theory.tex" else None
    if canonical_key is None:
        grammar = strict_tex_parse_report(source)
        _dump(
            {
                "source": str(source),
                "accepted": False,
                "reasons": [
                    "SQOT audit requires canonical source file Salience-Queue Occupation Theory.tex"
                ],
                "strict_grammar": grammar.model_dump(mode="json"),
                "coverage_counts": {},
                "audit": None,
            },
            output,
        )
        raise typer.Exit(1)
    data = theory_audit_cli_payload(source, canonical_key=canonical_key)
    _dump(data, output)
    grammar_data = data["strict_grammar"]
    if strict_grammar and isinstance(grammar_data, dict) and not bool(grammar_data.get("accepted")):
        raise typer.Exit(1)


@sqot_app.command("schedule")
def sqot_schedule(
    packets: Annotated[
        Path,
        typer.Option("--packets", help="JSON/YAML queue records or packet candidates."),
    ],
    obligations: Annotated[
        Path | None,
        typer.Option("--obligations", help="Optional JSON/YAML obligations list."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Scheduler profile: development, research, or production."),
    ] = "development",
    attention_budget: Annotated[
        float,
        typer.Option("--attention-budget", help="Finite attention budget for this queue run."),
    ] = 1.0,
    risk_budget: Annotated[
        float,
        typer.Option("--risk-budget", help="Finite risk budget for this queue run."),
    ] = 1.0,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Schedule packet, obligation, and verifier tasks with SQOT reserve rules."""

    records = _load_salience_records(packets)
    if obligations is not None:
        obligation_data = load_data(obligations)
        raw_obligations = obligation_data.get("obligations", [])
        if isinstance(raw_obligations, list):
            for obligation in raw_obligations:
                if not isinstance(obligation, dict):
                    continue
                records.append(
                    SalienceQueueRecord(
                        record_id=str(obligation.get("obligation_id", obligation.get("item_id"))),
                        item_type="obligation",
                        salience_class="diagnostic",
                        expected_downstream_gain=0.1,
                        residual_reduction=1.0,
                        verification_cost=0.1,
                        obligation_ids=[str(obligation.get("obligation_id", ""))],
                        verifier_routes=[str(obligation.get("verifier_hint", ""))],
                    )
                )
    report = build_salience_schedule(
        records,
        attention_budget=attention_budget,
        diagnostic_reserve=DiagnosticReservePolicy(),
        risk_budget=risk_budget,
        profile=profile,
    )
    _dump(report.model_dump(mode="json"), output)


@sqot_app.command("diagnose-queue")
def sqot_diagnose_queue_command(
    graph: Annotated[
        Path | None,
        typer.Option("--graph", help="EffectivePacketGraph JSON/YAML."),
    ] = None,
    state: Annotated[
        Path | None,
        typer.Option("--state", help="Runtime or phase report JSON/YAML."),
    ] = None,
    attention_budget: Annotated[
        float,
        typer.Option("--attention-budget", help="Finite diagnostic attention budget."),
    ] = 1.0,
    emit: Annotated[
        str | None,
        typer.Option("--emit", help="Optional interop emission: ccr-tasks."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Diagnose queue occupation pressure from an effective graph."""

    if state is not None:
        sqot_report = diagnose_sqot_queue_state(load_data(state))
        if emit == "ccr-tasks":
            _dump_jsonl(sqot_report["repair_tasks"], output)
            return
        if emit is not None:
            raise typer.BadParameter("--emit must be ccr-tasks")
        _dump(sqot_report, output)
        return
    if graph is None:
        raise typer.BadParameter("provide --graph or --state")
    report = diagnose_queue_occupation(
        _load_effective_graph(graph),
        attention_budget=attention_budget,
    )
    data = report.model_dump(mode="json")
    data["sqot_queue_report"] = diagnose_sqot_queue_state(data)
    if emit == "ccr-tasks":
        _dump_jsonl(data["sqot_queue_report"]["repair_tasks"], output)
        return
    if emit is not None:
        raise typer.BadParameter("--emit must be ccr-tasks")
    _dump(data, output)


@sqot_app.command("salience-obstruction")
def sqot_salience_obstruction_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Diagnose salience obstruction load."""

    diagnosis = diagnose_salience_obstruction(_load_effective_graph(graph))
    _dump(diagnosis.model_dump(mode="json"), output)


@sqot_app.command("rebalance")
def sqot_rebalance_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit a recommendation-only queue rebalance plan."""

    plan = build_queue_rebalance_plan(_load_effective_graph(graph))
    _dump(plan.model_dump(mode="json"), output)


@sqot_app.command("quarantine")
def sqot_quarantine_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit reversible quarantine decisions without applying them."""

    decisions = build_quarantine_decisions(_load_effective_graph(graph))
    _dump(
        {
            "quarantine_decisions": [decision.model_dump(mode="json") for decision in decisions],
            "applied": False,
            "deletes_packets": False,
            "settled": False,
        },
        output,
    )


@sqot_app.command("reserve-check")
def sqot_reserve_check_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    attention_budget: Annotated[
        float,
        typer.Option("--attention-budget", help="Finite diagnostic attention budget."),
    ] = 1.0,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check diagnostic reserve without scheduling work."""

    report = check_diagnostic_reserve(
        _load_effective_graph(graph),
        attention_budget=attention_budget,
    )
    _dump(report.model_dump(mode="json"), output)


@ecology_app.command("ingest")
def ecology_ingest(
    source: Annotated[
        str,
        typer.Option("--source", help="Local path, URL, repo slug, or literal agent output."),
    ],
    kind: Annotated[
        str,
        typer.Option("--kind", help="local, github, zenodo, arxiv, agent-output, or auto."),
    ] = "auto",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Ingest a source into capability packet candidates."""

    packet_kind = PacketSourceKind(kind)
    if packet_kind == PacketSourceKind.AUTO:
        packet_kind = infer_live_kind(source)
    if packet_kind == PacketSourceKind.LOCAL:
        report = ingest_local_file(Path(source))
    elif packet_kind == PacketSourceKind.AGENT_OUTPUT:
        report = ingest_agent_output(_read_text_or_literal(source))
    else:
        token = os.environ.get("GITHUB_TOKEN") if packet_kind == PacketSourceKind.GITHUB else None
        report = ingest_live_source(
            source,
            kind=packet_kind,
            token=token,
        )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@ecology_app.command("ingest-general")
def ecology_ingest_general_command(
    source: Annotated[
        str,
        typer.Option("--source", help="URI, local path, feed, JSONL, or agent message source."),
    ],
    kind: Annotated[
        str,
        typer.Option(
            "--kind",
            help=(
                "auto, local, http, web-page, rss, atom, json-feed, ndjson, "
                "agent-message, agent-inbox, web-crawl, github, zenodo, or arxiv."
            ),
        ),
    ] = "auto",
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Intake profile."),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded live web/connector fetches for explicit sources.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Ingest broad local/web/feed/message sources as packet candidates."""

    active_policy = _load_general_intake_policy(
        policy,
        profile=profile,
        allow_live_connectors=allow_live_connectors,
    )
    report = ingest_general_source(
        GeneralIntakeSource(
            source=source,
            kind=_packet_source_kind(kind),
            allow_live_connectors=allow_live_connectors,
        ),
        active_policy,
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@ecology_app.command("discover-web")
def ecology_discover_web_command(
    source: Annotated[
        str,
        typer.Option("--source", help="Seed URL or local HTML file."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional WebFetchPolicy JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded live web fetches for explicit sources.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run bounded web discovery without executing scripts or forms."""

    if policy is None:
        active_policy = WebFetchPolicy(allow_live_connectors=allow_live_connectors)
    else:
        data = load_data(policy)
        raw = data.get("web_fetch_policy", data.get("policy", data))
        if not isinstance(raw, dict):
            raise typer.BadParameter("web fetch policy file must contain an object")
        active_policy = WebFetchPolicy.model_validate(raw).model_copy(
            update={"allow_live_connectors": allow_live_connectors}
        )
    report = discover_web_packets(source, active_policy)
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@ecology_policy_app.command("explain")
def ecology_policy_explain_command(
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            help=(
                "Policy preset: local_only, controlled_web, federated_agents, "
                "production_network, adversarial_network, or development."
            ),
        ),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Show the policy with bounded live fetch permission enabled or disabled.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Explain one deterministic general-intake policy preset."""

    policy = general_intake_policy_for_profile(profile).model_copy(
        update={
            "allow_live_connectors": allow_live_connectors,
            "web_policy": general_intake_policy_for_profile(profile).web_policy.model_copy(
                update={"allow_live_connectors": allow_live_connectors}
            ),
        }
    )
    _dump(policy.model_dump(mode="json"), output)


@ecology_app.command("intake-audit")
def ecology_intake_audit_command(
    report: Annotated[
        Path,
        typer.Option("--report", help="GeneralIntakeReport JSON/YAML to audit."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Fallback policy profile when --policy is omitted."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Audit a general intake report against candidate-only runtime rules."""

    parsed_report = _load_general_intake_report(report)
    active_policy = (
        _load_general_intake_policy(policy, profile=profile, allow_live_connectors=False)
        if policy is not None
        else general_intake_policy_for_profile(parsed_report.intake_profile or profile)
    )
    audit = audit_general_intake_report(parsed_report, active_policy)
    _dump(audit.model_dump(mode="json"), output)
    if not audit.accepted:
        raise typer.Exit(1)


@ecology_app.command("bridge-runtime")
def ecology_bridge_runtime_command(
    report: Annotated[
        Path,
        typer.Option("--report", help="GeneralIntakeReport JSON/YAML to bridge."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Fallback policy profile when --policy is omitted."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Classify general intake candidates for SQOT/runtime work queues."""

    parsed_report = _load_general_intake_report(report)
    active_policy = (
        _load_general_intake_policy(policy, profile=profile, allow_live_connectors=False)
        if policy is not None
        else general_intake_policy_for_profile(parsed_report.intake_profile or profile)
    )
    bridge = bridge_general_intake_to_runtime(parsed_report, active_policy)
    _dump(bridge.model_dump(mode="json"), output)
    if not bridge.accepted:
        raise typer.Exit(1)


@ecology_app.command("build-edges")
def ecology_build_edges(
    packets: Annotated[
        Path,
        typer.Option("--packets", help="JSON/YAML packet list or registry."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build finite packet edge witnesses and return a registry."""

    data = load_data(packets)
    registry = registry_from_json(data)
    edges = build_edge_witnesses(registry.packets)
    updated = build_packet_registry(registry.packets, edges, registry_id=registry.registry_id)
    _dump(updated.model_dump(mode="json"), output)


@ecology_app.command("effective-graph")
def ecology_effective_graph_command(
    reports: Annotated[
        list[Path],
        typer.Option(
            "--reports",
            help="PIC report JSON/YAML. May repeat; literal patterns are expanded by PIC.",
        ),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build an effective packet graph from inert report files."""

    payloads = [load_data(path) for path in _expand_repeated_paths(reports, "--reports")]
    graph = build_effective_packet_graph(payloads).graph
    _dump(graph.model_dump(mode="json"), output)


@ecology_app.command("psi")
def ecology_psi(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    threshold: Annotated[
        Path | None,
        typer.Option("--threshold", help="Optional Psi threshold JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compute a finite ASI-proxy Psi dashboard."""

    parsed = registry_from_json(load_data(registry))
    thresholds = _threshold_from_file(threshold) if threshold is not None else None
    dashboard = build_psi_dashboard(parsed, threshold=thresholds)
    _dump(dashboard.model_dump(mode="json"), output)


@ecology_app.command("plan")
def ecology_plan(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    psi: Annotated[
        Path,
        typer.Option("--psi", help="PsiDashboard JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Planner profile: development, research, or production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Rank bottleneck-inversion interventions from a Psi dashboard."""

    parsed_registry = registry_from_json(load_data(registry))
    dashboard = PsiDashboard.model_validate(load_data(psi))
    plan = build_bottleneck_plan(parsed_registry, dashboard, profile=profile)
    _dump(plan.model_dump(mode="json"), output)


@ecology_app.command("paths")
def ecology_paths(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    basin: Annotated[
        Path,
        typer.Option("--basin", help="CapabilityBasinContract JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Find accepted packet paths into an ECPT basin contract."""

    parsed_registry = registry_from_json(load_data(registry))
    basin_contract = CapabilityBasinContract.model_validate(load_data(basin))
    paths = find_accepted_paths_to_basin(parsed_registry, basin_contract)
    _dump({"paths": [path.model_dump(mode="json") for path in paths]}, output)


@ecology_app.command("closures")
def ecology_closures(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    basin: Annotated[
        Path | None,
        typer.Option("--basin", help="Optional CapabilityBasinContract JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Find accepted autocatalytic closure witnesses for collective ECPT phase."""

    parsed_registry = registry_from_json(load_data(registry))
    basin_contract = (
        None if basin is None else CapabilityBasinContract.model_validate(load_data(basin))
    )
    closures = find_autocatalytic_closures(parsed_registry, basin_contract)
    _dump({"closures": [closure.model_dump(mode="json") for closure in closures]}, output)


@ecology_app.command("execution-paths")
def ecology_execution_paths(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    basin: Annotated[
        Path,
        typer.Option("--basin", help="CapabilityBasinContract JSON/YAML."),
    ],
    constraint_frame: Annotated[
        Path | None,
        typer.Option("--constraint-frame", help="Optional constraint-frame JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build execution-available, not-executed path certificates."""

    parsed_registry = registry_from_json(load_data(registry))
    basin_contract = CapabilityBasinContract.model_validate(load_data(basin))
    frame = load_data(constraint_frame) if constraint_frame is not None else None
    paths = find_execution_available_paths(
        parsed_registry,
        basin_contract,
        constraint_frame=frame,
    )
    _dump({"execution_available_paths": [path.model_dump(mode="json") for path in paths]}, output)


@ecology_app.command("execution-available-paths")
def ecology_execution_available_paths_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Detect execution-available, not-executed paths from an effective graph."""

    report = detect_execution_available_paths(_load_effective_graph(graph))
    _dump(report.model_dump(mode="json"), output)


@ecology_app.command("hidden-injection-check")
def ecology_hidden_injection_check(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    events: Annotated[
        Path,
        typer.Option("--events", help="Runtime events JSON/YAML object or list."),
    ],
    protocol: Annotated[
        Path,
        typer.Option("--protocol", help="ProtocolFrameDigest JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check that packets, edges, evidence, and events stay within protocol frame."""

    parsed_registry = registry_from_json(load_data(registry))
    raw_events = load_data(events)
    event_items = raw_events.get("events", raw_events.get("runtime_events", []))
    if not isinstance(event_items, list):
        raise typer.BadParameter("events file must contain an events list")
    protocol_frame = ProtocolFrameDigest.model_validate(load_data(protocol))
    report = check_no_hidden_capability_injection(
        parsed_registry,
        protocol_frame,
        runtime_events=[item for item in event_items if isinstance(item, dict)],
    )
    _dump(report.model_dump(mode="json"), output)


@ecology_app.command("verify-edge")
def ecology_verify_edge(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    certificate: Annotated[
        Path,
        typer.Option("--certificate", help="EdgeWitnessCertificate JSON/YAML."),
    ],
    relation: Annotated[
        str | None,
        typer.Option("--relation", help="Override relation type for built-in verifier."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify finite semantic evidence for an edge relation."""

    parsed_registry = registry_from_json(load_data(registry))
    certificate_data = load_data(certificate)
    edge_certificate = EdgeWitnessCertificate.model_validate(
        certificate_data.get("certificate", certificate_data)
    )
    spec = EdgeRelationVerifierSpec(relation_type=relation) if relation is not None else None
    report = verify_edge_relation(parsed_registry, edge_certificate, spec)
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@ecology_app.command("loop")
def ecology_loop(
    state: Annotated[
        Path,
        typer.Option("--state", help="JSON/YAML state with optional threshold object."),
    ],
    agent_output: Annotated[
        str,
        typer.Option("--agent-output", help="Path or literal output from an agent."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run one deterministic agent-output to packet-ecology planning loop."""

    state_data = load_data(state)
    threshold = state_data.get("threshold")
    thresholds = (
        {str(key): float(value) for key, value in threshold.items()}
        if isinstance(threshold, dict)
        else None
    )
    iteration = closed_loop_iteration(
        state_id=str(state_data.get("state_id", "ecology-state")),
        agent_output=_read_text_or_literal(agent_output),
        threshold=thresholds,
    )
    _dump(iteration.model_dump(mode="json"), output)


@runtime_app.command("step")
def runtime_step_command(
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    step_input: Annotated[
        Path,
        typer.Option("--input", help="RuntimeStepInput JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile: development, research, or production."),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded live connector ingestion for explicit sources.",
        ),
    ] = True,
    action_commit_policy: Annotated[
        str,
        typer.Option("--action-commit-policy", help="Runtime action commit policy."),
    ] = "require_verifier_resolution",
    attention_budget: Annotated[
        float,
        typer.Option("--attention-budget", help="SQOT attention budget for this step."),
    ] = 1.0,
    risk_budget: Annotated[
        float,
        typer.Option("--risk-budget", help="SQOT risk budget for this step."),
    ] = 1.0,
    max_tasks: Annotated[int, typer.Option("--max-tasks", help="Maximum tasks to emit.")] = 8,
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="RuntimeIdentityContext JSON/YAML from `pic identity derive-context`.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run one ECPT active runtime step."""

    parsed_state = _state_with_identity_context(
        _load_runtime_state(state),
        None if identity_context is None else _load_runtime_identity_context(identity_context),
    )
    parsed_input = _load_runtime_step_input(step_input).model_copy(
        update={"allow_live_connectors": allow_live_connectors}
    )
    config = _runtime_config(
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        action_commit_policy=action_commit_policy,
        attention_budget=attention_budget,
        risk_budget=risk_budget,
        max_tasks=max_tasks,
    )
    report = build_runtime_step(parsed_state, parsed_input, config)
    _dump(report.model_dump(mode="json"), output)


@runtime_app.command("loop")
def runtime_loop_command(
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    inputs: Annotated[
        Path,
        typer.Option("--inputs", help="RuntimeStepInput JSONL or JSON with inputs list."),
    ],
    max_steps: Annotated[int, typer.Option("--max-steps", help="Maximum loop steps.")] = 8,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile: development, research, or production."),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded live connector ingestion for explicit sources.",
        ),
    ] = True,
    action_commit_policy: Annotated[
        str,
        typer.Option("--action-commit-policy", help="Runtime action commit policy."),
    ] = "require_verifier_resolution",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run a deterministic ECPT active runtime loop over JSONL inputs."""

    parsed_state = _load_runtime_state(state)
    parsed_inputs = [
        item.model_copy(update={"allow_live_connectors": allow_live_connectors})
        for item in _load_runtime_inputs(inputs)
    ]
    config = _runtime_config(
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        action_commit_policy=action_commit_policy,
        attention_budget=1.0,
        risk_budget=1.0,
        max_tasks=8,
    )
    reports = run_runtime_loop(parsed_state, parsed_inputs, config, max_steps=max_steps)
    _dump({"reports": [report.model_dump(mode="json") for report in reports]}, output)


@runtime_app.command("resolve-evidence")
def runtime_resolve_evidence_command(
    step_input: Annotated[
        Path,
        typer.Option("--input", help="RuntimeStepInput JSON/YAML with inline evidence."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Evidence verification profile."),
    ] = "development",
    evidence_store: Annotated[
        Path | None,
        typer.Option("--evidence-store", help="Optional content-addressed evidence store dir."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Resolve runtime step evidence envelopes against verifier routes."""

    parsed_input = _load_runtime_step_input(step_input)
    store = FileEvidenceEnvelopeStore(evidence_store) if evidence_store is not None else None
    batch = resolve_step_evidence(parsed_input, profile=profile, envelope_store=store)
    _dump(batch.model_dump(mode="json"), output)
    if not batch.accepted and profile == "production":
        raise typer.Exit(1)


@runtime_app.command("execute-task")
def runtime_execute_task_command(
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    task: Annotated[
        Path,
        typer.Option("--task", help="AgentTask JSON/YAML."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="RuntimeExecutorPolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Executor profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Execute one allowlisted runtime task without arbitrary shell execution."""

    report = execute_runtime_task(
        _load_agent_task(task),
        _load_runtime_state(state),
        _load_runtime_executor_policy(policy, profile=profile),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted and profile == "production":
        raise typer.Exit(1)


@runtime_app.command("execute-routes")
def runtime_execute_routes_command(
    requests: Annotated[
        Path,
        typer.Option("--requests", help="RouteExecutionRequest list JSON/YAML."),
    ],
    evidence_store: Annotated[
        Path,
        typer.Option("--evidence-store", help="Content-addressed evidence store dir."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Route execution profile."),
    ] = "development",
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="RuntimeExecutorPolicy JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Execute verifier route requests with sandboxed evidence envelopes."""

    batch = execute_route_batch(
        _load_route_execution_requests(requests),
        FileEvidenceEnvelopeStore(evidence_store),
        _load_runtime_executor_policy(policy, profile=profile),
        profile=profile,
    )
    _dump(batch.model_dump(mode="json"), output)
    if not batch.accepted and profile == "production":
        raise typer.Exit(1)


@runtime_app.command("run-agent-loop")
def runtime_run_agent_loop_command(
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    inputs: Annotated[
        Path,
        typer.Option("--inputs", help="RuntimeStepInput JSONL or JSON with inputs list."),
    ],
    store: Annotated[
        Path,
        typer.Option("--store", help="SQLite runtime store path."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="RuntimeExecutorPolicy JSON/YAML."),
    ] = None,
    max_steps: Annotated[int, typer.Option("--max-steps", help="Maximum loop steps.")] = 8,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Executor profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run an allowlisted autonomous ECPT agent loop with a persistent store."""

    runtime_store = SQLiteRuntimeStore(store)
    reports = run_agent_loop_with_store(
        _load_runtime_state(state),
        _load_runtime_inputs(inputs),
        _load_runtime_executor_policy(policy, profile=profile),
        runtime_store,
        max_steps=max_steps,
    )
    _dump(
        {
            "reports": [report.model_dump(mode="json") for report in reports],
            "store": runtime_store.record().model_dump(mode="json"),
        },
        output,
    )


@runtime_app.command("population-step")
def runtime_population_step_command(
    population: Annotated[
        Path,
        typer.Option("--population", help="AgentPopulationState JSON/YAML."),
    ],
    inputs: Annotated[
        Path,
        typer.Option("--inputs", help="RuntimeStepInput JSONL or JSON with inputs list."),
    ],
    store: Annotated[
        Path | None,
        typer.Option("--store", help="Optional SQLite runtime store path."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile: development, research, or production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run one population-level collective ECPT runtime step."""

    parsed_population = _load_agent_population_state(population)
    report = build_population_runtime_step(
        parsed_population,
        _load_runtime_inputs(inputs),
        AgentRuntimeConfig(profile=profile),
    )
    if store is not None:
        runtime_store = SQLiteRuntimeStore(store)
        if report.next_population is not None:
            runtime_store.append_population(report.next_population)
        for agent_report in report.agent_reports:
            for event in agent_report.event_log_delta.events:
                runtime_store.append_event(event)
    _dump(report.model_dump(mode="json"), output)


@runtime_app.command("collective-certify")
def runtime_collective_certify_command(
    population: Annotated[
        Path,
        typer.Option("--population", help="AgentPopulationState JSON/YAML."),
    ],
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    basin: Annotated[
        Path,
        typer.Option("--basin", help="CapabilityBasinContract JSON/YAML."),
    ],
    baseline: Annotated[
        Path,
        typer.Option("--baseline", help="Baseline RuntimeRunReport JSON/YAML."),
    ],
    threshold: Annotated[
        Path | None,
        typer.Option("--threshold", help="Optional Psi threshold JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            help="Certificate profile: development, research, or production.",
        ),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Certify finite collective ECPT ASI-proxy phase progress."""

    certificate = certify_collective_phase(
        _load_agent_population_state(population),
        _load_runtime_state(state),
        CapabilityBasinContract.model_validate(load_data(basin)),
        _load_runtime_run_report(baseline),
        None if threshold is None else _threshold_from_file(threshold),
        profile=profile,
    )
    _dump(certificate.model_dump(mode="json"), output)


@runtime_app.command("apply-results")
def runtime_apply_results_command(
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    report: Annotated[
        Path,
        typer.Option("--report", help="RuntimeStepReport JSON/YAML."),
    ],
    results: Annotated[
        Path,
        typer.Option("--results", help="JSON/YAML object containing a results list."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write next RuntimeState JSON.")
    ] = None,
) -> None:
    """Apply agent action results to runtime state without status promotion."""

    next_state = apply_action_results(
        _load_runtime_state(state),
        _load_runtime_step_report(report),
        _load_runtime_action_results(results),
    )
    _dump(next_state.model_dump(mode="json"), output)


@runtime_app.command("compare")
def runtime_compare_command(
    baseline: Annotated[
        Path,
        typer.Option("--baseline", help="Baseline RuntimeRunReport JSON/YAML."),
    ],
    candidate: Annotated[
        Path,
        typer.Option("--candidate", help="Candidate RuntimeRunReport JSON/YAML."),
    ],
    threshold: Annotated[
        Path | None,
        typer.Option("--threshold", help="Optional threshold object JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compare baseline and candidate runtime runs."""

    comparison = compare_runtime_runs(
        _load_runtime_run_report(baseline),
        _load_runtime_run_report(candidate),
        {} if threshold is None else _threshold_from_file(threshold),
    )
    _dump(comparison.model_dump(mode="json"), output)


@runtime_app.command("certify-acceleration")
def runtime_certify_acceleration_command(
    baseline: Annotated[
        Path,
        typer.Option("--baseline", help="Baseline RuntimeRunReport JSON/YAML."),
    ],
    candidate: Annotated[
        Path,
        typer.Option("--candidate", help="Candidate RuntimeRunReport JSON/YAML."),
    ],
    threshold: Annotated[
        Path | None,
        typer.Option("--threshold", help="Optional threshold object JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a finite ECPT ASI-proxy acceleration certificate."""

    certificate = certify_runtime_acceleration(
        _load_runtime_run_report(baseline),
        _load_runtime_run_report(candidate),
        {} if threshold is None else _threshold_from_file(threshold),
    )
    _dump(certificate.model_dump(mode="json"), output)


@runtime_app.command("health")
def runtime_health_command(
    state: Annotated[
        Path,
        typer.Option("--state", help="RuntimeState JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile: development, research, or production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit a finite runtime health report."""

    parsed_state = _load_runtime_state(state)
    report = runtime_health(parsed_state, AgentRuntimeConfig(profile=profile))
    _dump(report.model_dump(mode="json"), output)


@runtime_app.command("export-openapi")
def runtime_export_openapi(
    output: Annotated[Path, typer.Option("--output", "-o", help="Write OpenAPI JSON.")],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime service profile."),
    ] = "development",
) -> None:
    """Export the optional local runtime service OpenAPI document."""

    try:
        service_app = create_runtime_app(RuntimeServiceSettings(profile=profile))
    except RuntimeError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(service_app.openapi(), output)


@runtime_app.command("service")
def runtime_service_command(
    host: Annotated[str, typer.Option("--host", help="Service host.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Service port.")] = 8765,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime service profile."),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded live connector use when requests provide explicit sources.",
        ),
    ] = True,
) -> None:
    """Run the optional local ECPT active runtime HTTP service."""

    settings = RuntimeServiceSettings(
        host=host,
        port=port,
        profile=profile,
        allow_live_connectors=allow_live_connectors,
    )
    try:
        run_runtime_service(settings)
    except RuntimeError as exc:
        raise typer.BadParameter(str(exc)) from exc


@adoption_app.command("packet")
def adoption_packet_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Operator-adoption profile."),
    ] = "development",
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: json or markdown."),
    ] = "json",
    language: Annotated[
        str,
        typer.Option("--language", help="Markdown language: en or ja."),
    ] = "en",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write output.")] = None,
) -> None:
    """Generate an optional operator-facing adoption packet."""

    packet = build_operator_adoption_packet(profile)
    if _output_format(output_format) == "markdown":
        _dump_text(adoption_packet_markdown(packet, language=_language(language)), output)
        return
    _dump(packet.model_dump(mode="json"), output)


@adoption_app.command("request")
def adoption_request_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Operator-adoption profile."),
    ] = "development",
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: json or markdown."),
    ] = "json",
    language: Annotated[
        str,
        typer.Option("--language", help="Markdown language: en or ja."),
    ] = "en",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write output.")] = None,
) -> None:
    """Generate a short agent-to-operator adoption request."""

    request = build_agent_to_operator_request(profile)
    if _output_format(output_format) == "markdown":
        _dump_text(operator_request_markdown(request, language=_language(language)), output)
        return
    _dump(request.model_dump(mode="json"), output)


@phase_app.command("plan")
def phase_plan_command(
    request: Annotated[
        Path | None,
        typer.Option("--request", help="PhaseAccelerationRequest JSON/YAML."),
    ] = None,
    runtime_report: Annotated[
        Path | None,
        typer.Option("--runtime-report", help="RuntimeStepReport JSON/YAML."),
    ] = None,
    state: Annotated[
        Path | None,
        typer.Option("--state", help="RuntimeState JSON/YAML. Defaults to minimal demo state."),
    ] = None,
    step_input: Annotated[
        Path | None,
        typer.Option("--input", help="RuntimeStepInput JSON/YAML. Defaults to minimal demo input."),
    ] = None,
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal agent output for the default runtime step."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="File containing agent output text."),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Planner profile."),
    ] = None,
    identity_context: Annotated[
        Path | None,
        typer.Option("--identity-context", help="Optional RuntimeIdentityContext JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool | None,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded live connector use when explicit sources are supplied.",
        ),
    ] = None,
    compact: Annotated[
        bool,
        typer.Option("--compact/--full", help="Emit compact CI/agent JSON."),
    ] = False,
    emit: Annotated[
        str | None,
        typer.Option(
            "--emit",
            help="Optional interop emission: ccr-tasks or ccr-residuals.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a deterministic phase-acceleration plan."""

    parsed_request = _load_phase_acceleration_request(
        request_path=request,
        runtime_report_path=runtime_report,
        state_path=state,
        step_input_path=step_input,
        text=text,
        text_file=text_file,
        profile=profile,
        identity_context_path=identity_context,
        allow_live_connectors=allow_live_connectors,
        compact=compact,
    )
    plan = build_phase_acceleration_plan(parsed_request)
    if emit is not None:
        if emit == "ccr-tasks":
            _dump_jsonl(ccr_tasks_from_phase_plan(plan), output)
            return
        if emit == "ccr-residuals":
            _dump_jsonl(ccr_residuals_from_phase_plan(plan), output)
            return
        raise typer.BadParameter("--emit must be ccr-tasks or ccr-residuals")
    payload = phase_acceleration_compact_payload(plan) if compact else plan.model_dump(mode="json")
    _dump(payload, output)


@phase_app.command("gap")
def phase_gap_command(
    request: Annotated[
        Path | None,
        typer.Option("--request", help="PhaseAccelerationRequest JSON/YAML."),
    ] = None,
    runtime_report: Annotated[
        Path | None,
        typer.Option("--runtime-report", help="RuntimeStepReport JSON/YAML."),
    ] = None,
    state: Annotated[
        Path | None,
        typer.Option("--state", help="RuntimeState JSON/YAML. Defaults to minimal demo state."),
    ] = None,
    step_input: Annotated[
        Path | None,
        typer.Option("--input", help="RuntimeStepInput JSON/YAML. Defaults to minimal demo input."),
    ] = None,
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal agent output for the default runtime step."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="File containing agent output text."),
    ] = None,
    profile: Annotated[str | None, typer.Option("--profile", help="Planner profile.")] = None,
    identity_context: Annotated[
        Path | None,
        typer.Option("--identity-context", help="Optional RuntimeIdentityContext JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool | None,
        typer.Option("--allow-live-connectors/--no-allow-live-connectors"),
    ] = None,
    compact: Annotated[
        bool,
        typer.Option("--compact/--full", help="Accepted for command symmetry."),
    ] = False,
    emit: Annotated[
        str | None,
        typer.Option(
            "--emit",
            help="Optional interop emission: ccr-residuals or ccr-tasks.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit only the finite phase-gap vector."""

    parsed_request = _load_phase_acceleration_request(
        request_path=request,
        runtime_report_path=runtime_report,
        state_path=state,
        step_input_path=step_input,
        text=text,
        text_file=text_file,
        profile=profile,
        identity_context_path=identity_context,
        allow_live_connectors=allow_live_connectors,
        compact=compact,
    )
    plan = build_phase_acceleration_plan(parsed_request)
    if emit is not None:
        if emit == "ccr-residuals":
            _dump_jsonl(ccr_residuals_from_phase_plan(plan), output)
            return
        if emit == "ccr-tasks":
            _dump_jsonl(ccr_tasks_from_phase_plan(plan), output)
            return
        raise typer.BadParameter("--emit must be ccr-residuals or ccr-tasks")
    _dump(plan.phase_gap_vector.model_dump(mode="json"), output)


@phase_app.command("trajectory")
def phase_trajectory_command(
    report: Annotated[
        list[Path] | None,
        typer.Option("--report", help="RuntimeStepReport JSON/YAML. May be repeated."),
    ] = None,
    profile: Annotated[str, typer.Option("--profile", help="Planner profile.")] = "development",
    compact: Annotated[
        bool,
        typer.Option("--compact/--full", help="Omit nested runtime reports in generated plans."),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a trajectory from one or more runtime reports."""

    reports = report or []
    if reports:
        requests = [
            PhaseAccelerationRequest(
                request_id=f"phase-trajectory:{index}",
                profile=profile,
                runtime_report=_load_runtime_step_report(path),
                compact=compact,
            )
            for index, path in enumerate(reports)
        ]
    else:
        requests = [
            PhaseAccelerationRequest(
                request_id="phase-trajectory:default",
                profile=profile,
                state=_load_agent_default_state(None),
                step_input=minimal_runtime_step_input(),
                runtime_config=AgentRuntimeConfig(profile=profile),
                compact=compact,
            )
        ]
    trajectory = build_phase_trajectory(requests, profile=profile)
    _dump(trajectory.model_dump(mode="json"), output)


@phase_app.command("runbook")
def phase_runbook_command(
    profile: Annotated[str, typer.Option("--profile", help="Planner profile.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Print deterministic phase-acceleration guidance for agents."""

    _dump(phase_acceleration_runbook(profile), output)


@phase_app.command("benchmark")
def phase_benchmark_command(
    request: Annotated[
        Path | None,
        typer.Option("--request", help="PhaseAccelerationRequest JSON/YAML."),
    ] = None,
    runtime_report: Annotated[
        Path | None,
        typer.Option("--runtime-report", help="RuntimeStepReport JSON/YAML."),
    ] = None,
    state: Annotated[
        Path | None,
        typer.Option("--state", help="RuntimeState JSON/YAML. Defaults to minimal demo state."),
    ] = None,
    step_input: Annotated[
        Path | None,
        typer.Option("--input", help="RuntimeStepInput JSON/YAML. Defaults to minimal demo input."),
    ] = None,
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal agent output for the default runtime step."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="File containing agent output text."),
    ] = None,
    profile: Annotated[str, typer.Option("--profile", help="Planner profile.")] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option("--identity-context", help="Optional RuntimeIdentityContext JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool | None,
        typer.Option("--allow-live-connectors/--no-allow-live-connectors"),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compare candidate-only sharing with PIC-guided finite routing."""

    parsed_request = _load_phase_acceleration_request(
        request_path=request,
        runtime_report_path=runtime_report,
        state_path=state,
        step_input_path=step_input,
        text=text,
        text_file=text_file,
        profile=profile,
        identity_context_path=identity_context,
        allow_live_connectors=allow_live_connectors,
        compact=True,
    )
    plan = build_phase_acceleration_plan(parsed_request)
    _dump(build_phase_acceleration_benchmark(plan).model_dump(mode="json"), output)


@phase_app.command("benchmark-suite")
def phase_benchmark_suite_command(
    profile: Annotated[str, typer.Option("--profile", help="Benchmark profile.")] = "development",
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: json or markdown."),
    ] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write output.")] = None,
) -> None:
    """Run the diagnostic protocol-relative phase benchmark suite."""

    report = build_phase_benchmark_suite(profile=profile)
    if _output_format(output_format) == "markdown":
        _dump_text(phase_benchmark_suite_markdown(report), output)
        return
    _dump(report.model_dump(mode="json"), output)


@phase_app.command("dashboard")
def phase_dashboard_command(
    profile: Annotated[str, typer.Option("--profile", help="Dashboard profile.")] = "development",
    runtime_report: Annotated[
        Path | None,
        typer.Option("--runtime-report", help="Optional RuntimeStepReport JSON/YAML."),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: json or markdown."),
    ] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write output.")] = None,
) -> None:
    """Emit an observation-only phase dashboard."""

    parsed_report = None if runtime_report is None else _load_runtime_step_report(runtime_report)
    dashboard = build_phase_dashboard(profile=profile, runtime_report=parsed_report)
    if _output_format(output_format) == "markdown":
        _dump_text(phase_dashboard_markdown(dashboard), output)
        return
    _dump(dashboard.model_dump(mode="json"), output)


@phase_app.command("observe")
def phase_observe_command(
    reports: Annotated[
        list[Path] | None,
        typer.Option("--reports", help="RuntimeStepReport or PhaseDashboardReport JSON/YAML."),
    ] = None,
    profile: Annotated[str, typer.Option("--profile", help="Observation profile.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Aggregate phase reports into an observation-only dashboard report."""

    dashboards: list[PhaseDashboardReport] = []
    for path in _expand_repeated_paths(reports, "--reports"):
        data = load_data(path)
        if "dashboard_id" in data and "packet_candidate_count" in data:
            dashboards.append(_load_phase_dashboard_report(path))
        else:
            dashboards.append(
                build_phase_dashboard(
                    profile=profile,
                    runtime_report=_load_runtime_step_report(path),
                )
            )
    if not dashboards:
        dashboards.append(build_phase_dashboard(profile=profile))
    _dump(build_phase_observation(dashboards, profile=profile).model_dump(mode="json"), output)


@phase_lab_app.command("init")
def phase_lab_init_command(
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory for the local Phase Lab store."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Initialize a local Phase Ecology Lab store."""

    manifest = init_phase_lab_store(output_dir)
    _dump(manifest.model_dump(mode="json"), output)


@phase_lab_app.command("ingest")
def phase_lab_ingest_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    report: Annotated[
        list[Path] | None,
        typer.Option(
            "--report",
            help="PIC report JSON/YAML. May repeat; literal patterns are expanded by PIC.",
        ),
    ] = None,
    packet: Annotated[
        list[Path] | None,
        typer.Option(
            "--packet",
            help="Packet JSON/YAML. May repeat; literal patterns are expanded by PIC.",
        ),
    ] = None,
    directory: Annotated[
        Path | None,
        typer.Option("--directory", help="Directory of JSON/YAML reports to ingest."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Ingest local report or packet data into a new Phase Lab window."""

    paths = [
        *_expand_repeated_paths(report, "--report"),
        *_expand_repeated_paths(packet, "--packet"),
    ]
    if directory is not None:
        ingest = ingest_phase_lab_directory(store, directory)
    elif paths:
        ingest = ingest_phase_lab_paths(store, paths)
    else:
        raise typer.BadParameter("provide --report, --packet, or --directory")
    _dump(ingest.model_dump(mode="json"), output)


@phase_lab_app.command("list-windows")
def phase_lab_list_windows_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """List deterministic Phase Lab ingest windows."""

    active = PhaseLabStore(store)
    _dump(
        {
            "store_manifest": active.manifest().model_dump(mode="json"),
            "windows": [window.model_dump(mode="json") for window in active.list_windows()],
            "settled": False,
        },
        output,
    )


@phase_lab_app.command("observe")
def phase_lab_observe_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    window: Annotated[
        str,
        typer.Option("--window", help="latest, previous, or window id."),
    ] = "latest",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Observe one Phase Lab window."""

    observation, _graph = _phase_lab_observation(store, window)
    _dump(observation.model_dump(mode="json"), output)


@phase_lab_app.command("graph")
def phase_lab_graph_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    window: Annotated[
        str,
        typer.Option("--window", help="latest, previous, all, or window id."),
    ] = "all",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build an effective packet graph from Phase Lab events."""

    _dump(_phase_lab_graph(store, window).model_dump(mode="json"), output)


@phase_lab_app.command("closure")
def phase_lab_closure_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    window: Annotated[
        str,
        typer.Option("--window", help="latest, previous, all, or window id."),
    ] = "all",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Detect autocatalytic closure candidates without settlement."""

    graph = _phase_lab_graph(store, window)
    _dump(detect_autocatalytic_closure(graph).model_dump(mode="json"), output)


@phase_lab_app.command("executable-paths")
def phase_lab_executable_paths_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    window: Annotated[
        str,
        typer.Option("--window", help="latest, previous, all, or window id."),
    ] = "all",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Detect execution-available, not-executed hyperpaths."""

    graph = _phase_lab_graph(store, window)
    _dump(detect_execution_available_paths(graph).model_dump(mode="json"), output)


@phase_lab_app.command("threshold-status")
def phase_lab_threshold_status_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    threshold: Annotated[
        Path,
        typer.Option("--threshold", help="ASIProxyThresholdSpec JSON/YAML."),
    ],
    window: Annotated[
        str,
        typer.Option("--window", help="latest, previous, or window id."),
    ] = "latest",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compute protocol-relative ASI-proxy threshold status."""

    observation, _graph = _phase_lab_observation(store, window)
    status = build_threshold_status(observation, _load_asi_proxy_threshold(threshold))
    _dump(status.model_dump(mode="json"), output)


@phase_lab_app.command("certify")
def phase_lab_certify_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    threshold: Annotated[
        Path,
        typer.Option("--threshold", help="ASIProxyThresholdSpec JSON/YAML."),
    ],
    window: Annotated[
        str,
        typer.Option("--window", help="latest, previous, or window id."),
    ] = "latest",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a collective phase certificate candidate or abstention report."""

    observation, graph = _phase_lab_observation(store, window)
    status = build_threshold_status(observation, _load_asi_proxy_threshold(threshold))
    candidate = build_collective_phase_certificate_candidate(status, graph)
    _dump(candidate.model_dump(mode="json"), output)


@phase_lab_app.command("compare-window")
def phase_lab_compare_window_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    baseline: Annotated[str, typer.Option("--baseline", help="previous, latest, or window id.")],
    candidate: Annotated[str, typer.Option("--candidate", help="latest or window id.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compare two Phase Lab windows."""

    baseline_observation, _baseline_graph = _phase_lab_observation(store, baseline)
    candidate_observation, _candidate_graph = _phase_lab_observation(store, candidate)
    _dump(
        compare_phase_windows(baseline_observation, candidate_observation).model_dump(mode="json"),
        output,
    )


@phase_lab_app.command("export")
def phase_lab_export_command(
    store: Annotated[Path, typer.Option("--store", help="Phase Lab store directory.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Export directory.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Export a sanitized Phase Lab bundle."""

    manifest = export_phase_lab_store(store, output_dir)
    _dump(manifest.model_dump(mode="json"), output)


@phase_closure_app.command("find")
def phase_closure_find_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Find closure candidates from an effective packet graph."""

    report = detect_autocatalytic_closure(_load_effective_graph(graph))
    _dump(report.model_dump(mode="json"), output)


@phase_closure_app.command("certify")
def phase_closure_certify_command(
    graph: Annotated[Path, typer.Option("--graph", help="EffectivePacketGraph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit only the closure certificate candidate."""

    report = detect_autocatalytic_closure(_load_effective_graph(graph))
    _dump(report.certificate_candidate.model_dump(mode="json"), output)


@packet_app.command("export")
def packet_export_command(
    report: Annotated[
        Path,
        typer.Option("--report", help="RuntimeStepReport JSON/YAML to export as data."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write packet JSON.")
    ] = None,
) -> None:
    """Export a runtime report as a data-only packet envelope."""

    envelope = packet_exchange_envelope_from_runtime_report(_load_runtime_step_report(report))
    _dump(envelope.model_dump(mode="json"), output)


@packet_app.command("inspect")
def packet_inspect_command(
    packet: Annotated[
        Path,
        typer.Option("--packet", help="PacketExchangeEnvelope JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write inspection JSON.")
    ] = None,
) -> None:
    """Inspect a data-only packet envelope without executing content."""

    _dump(
        inspect_packet_exchange_envelope(_load_packet_exchange_envelope(packet)).model_dump(
            mode="json"
        ),
        output,
    )


@packet_app.command("merge")
def packet_merge_command(
    packets: Annotated[
        list[Path],
        typer.Option("--packets", help="PacketExchangeEnvelope JSON/YAML. May be repeated."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write merge-report JSON.")
    ] = None,
) -> None:
    """Merge packet envelopes by digest without promoting them."""

    report = merge_packet_exchange_envelopes(
        [
            _load_packet_exchange_envelope(path)
            for path in _expand_repeated_paths(packets, "--packets")
        ]
    )
    _dump(report.model_dump(mode="json"), output)


@packet_app.command("lineage")
def packet_lineage_command(
    packet: Annotated[
        Path,
        typer.Option("--packet", help="PacketExchangeEnvelope or PacketMergeReport JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write lineage JSON.")
    ] = None,
) -> None:
    """Emit packet lineage without promotion."""

    _dump(packet_lineage_digest(_load_packet_or_merge(packet)).model_dump(mode="json"), output)


@agent_app.command("explain")
def agent_explain_command(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Explain the repository to autonomous agents."""

    manifest = agent_manifest_payload()
    _dump(
        {
            "name": manifest["name"],
            "version": __version__,
            "what_this_repo_is": (
                "AI agent runtime verification and ECPT ASI-proxy collective phase "
                "acceleration module"
            ),
            "what_it_does_not_do": manifest["non_goals"],
            "recommended_docs": manifest["recommended_docs"],
            "safe_first_commands": manifest["safe_cli_entrypoints"],
            "python_entrypoints": [
                "percolation_inversion_compiler.agent.run_agent_intake",
                "percolation_inversion_compiler.agent.accelerate_agent_phase",
                "percolation_inversion_compiler.acceleration.build_phase_acceleration_plan",
                "percolation_inversion_compiler.agent.minimal_runtime_state",
                "percolation_inversion_compiler.runtime.build_runtime_step",
                "percolation_inversion_compiler.runtime.derive_runtime_identity_context",
                "percolation_inversion_compiler.runtime.runtime_health",
                "percolation_inversion_compiler.identity.sybil_policy_for_profile",
            ],
            "machine_contract": manifest["machine_contract"],
        },
        output,
    )


@agent_app.command("doctor")
def agent_doctor_command(
    state: Annotated[
        Path | None,
        typer.Option(
            "--state",
            help="RuntimeState JSON/YAML. Defaults to examples/runtime_state.json when present.",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run a safe agent-facing runtime health check."""

    parsed_state = _load_agent_default_state(state)
    report = runtime_health(parsed_state, AgentRuntimeConfig(profile=profile))
    recommendations = [
        'Run `uv run pic agent intake --text "..." --profile development` for a minimal step.',
        "Inspect residual_ledger, missing_obligations, and settled before acting.",
    ]
    if profile.lower() in {"production", "adversarial"} and not report.production_identity_ready:
        recommendations.append(
            "Derive identity context with `uv run pic identity derive-context "
            "--population examples/agent_population_signed.json --profile production "
            "--output identity-context.json`."
        )
    _dump(
        {
            "runtime_health": report.model_dump(mode="json"),
            "recommended_next_commands": recommendations,
            "accepted": report.accepted,
            "operationally_usable": report.operationally_usable,
            "settled": report.settled,
        },
        output,
    )


@agent_app.command("autonomy-audit")
def agent_autonomy_audit_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent autonomy profile."),
    ] = "development",
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: json or markdown."),
    ] = "json",
    language: Annotated[
        str,
        typer.Option("--language", help="Markdown language: en or ja."),
    ] = "en",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write output.")] = None,
) -> None:
    """Audit whether agent activity is blocked by approval or adoption state."""

    report = build_agent_autonomy_audit(profile)
    if _output_format(output_format) == "markdown":
        _dump_text(
            agent_autonomy_audit_markdown(report, language=_language(language)),
            output,
        )
        return
    _dump(report.model_dump(mode="json"), output)


@agent_app.command("guide")
def agent_guide_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent workflow profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit the full-feature AI-agent workflow guide."""

    guide = build_agent_workflow_guide(profile)
    _dump(guide.model_dump(mode="json"), output)


@agent_app.command("communication-guide")
def agent_communication_guide_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent communication profile."),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Describe the workflow with bounded live connectors enabled or disabled.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit the external-communication guide for agents."""

    guide = build_agent_communication_guide(profile, allow_live_connectors)
    _dump(guide.model_dump(mode="json"), output)


@agent_app.command("network-readiness")
def agent_network_readiness_command(
    state: Annotated[
        Path | None,
        typer.Option(
            "--state",
            help="RuntimeState JSON/YAML. Defaults to examples/runtime_state.json when present.",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent communication profile."),
    ] = "development",
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Check readiness for bounded live connector use.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report network readiness without making network calls."""

    report = agent_network_readiness(
        _load_agent_default_state(state),
        profile,
        allow_live_connectors,
    )
    _dump(report.model_dump(mode="json"), output)


@agent_app.command("relay-readiness")
def agent_relay_readiness_command(
    inbox: Annotated[
        Path | None,
        typer.Option("--inbox", help="Optional local agent inbox JSON/JSONL path."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent relay profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="Optional RuntimeIdentityContext JSON/YAML accepted by population Sybil checks.",
        ),
    ] = None,
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Report bounded live default mode for relay-adjacent explicit sources.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report local agent-message relay readiness without network calls."""

    policy = GeneralIntakePolicy(
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        web_policy=WebFetchPolicy(allow_live_connectors=allow_live_connectors),
    )
    report = agent_relay_readiness_report(
        inbox,
        policy,
        _load_agent_message_verification_context(identity_context),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@agent_app.command("readiness")
def agent_readiness_command(
    state: Annotated[
        Path | None,
        typer.Option(
            "--state",
            help="RuntimeState JSON/YAML. Defaults to examples/runtime_state.json when present.",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent workflow profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report whether the full agent workflow is ready or diagnostic."""

    report = agent_feature_readiness(_load_agent_default_state(state), profile)
    _dump(report.model_dump(mode="json"), output)


@agent_app.command("intake")
def agent_intake_command(
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal agent output to ingest."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="File containing agent output text."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option("--identity-context", help="Optional RuntimeIdentityContext JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded runtime live connector ingestion for explicit sources.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run a minimal agent-output intake through the runtime."""

    if text is not None and text_file is not None:
        raise typer.BadParameter("Use either --text or --text-file, not both")
    agent_output = text
    if text_file is not None:
        agent_output = text_file.read_text(encoding="utf-8")
    report = run_agent_intake(
        AgentIntakeRequest(
            agent_output=agent_output,
            profile=profile,
            identity_context=(
                None
                if identity_context is None
                else _load_runtime_identity_context(identity_context)
            ),
            allow_live_connectors=allow_live_connectors,
        )
    )
    _dump(report.model_dump(mode="json"), output)


@agent_app.command("runbook")
def agent_runbook_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent workflow profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Print deterministic command/schema/field guidance for AI agents."""

    _dump(build_agent_runbook(profile).model_dump(mode="json"), output)


@agent_app.command("check")
def agent_check_command(
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal agent output to check."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="File containing agent output text."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option("--identity-context", help="Optional RuntimeIdentityContext JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded runtime live connector ingestion for explicit sources.",
        ),
    ] = True,
    compact: Annotated[
        bool,
        typer.Option(
            "--compact/--full",
            help="Emit compact CI/agent JSON without nested runtime output.",
        ),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check agent output with beginner-readable workflow usability fields."""

    if text is not None and text_file is not None:
        raise typer.BadParameter("Use either --text or --text-file, not both")
    agent_output = text
    if text_file is not None:
        agent_output = text_file.read_text(encoding="utf-8")
    report = run_agent_check(
        AgentIntakeRequest(
            agent_output=agent_output,
            profile=profile,
            identity_context=(
                None
                if identity_context is None
                else _load_runtime_identity_context(identity_context)
            ),
            allow_live_connectors=allow_live_connectors,
        ),
        compact=compact,
    )
    payload = agent_check_compact_payload(report) if compact else report.model_dump(mode="json")
    _dump(payload, output)


@agent_app.command("accelerate")
def agent_accelerate_command(
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal agent output to plan around."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="File containing agent output text."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option("--identity-context", help="Optional RuntimeIdentityContext JSON/YAML."),
    ] = None,
    allow_live_connectors: Annotated[
        bool,
        typer.Option(
            "--allow-live-connectors/--no-allow-live-connectors",
            help="Allow bounded runtime live connector ingestion for explicit sources.",
        ),
    ] = True,
    compact: Annotated[
        bool,
        typer.Option(
            "--compact/--full",
            help="Emit compact CI/agent JSON without nested runtime output.",
        ),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Plan the next finite phase-acceleration steps for an agent output."""

    if text is not None and text_file is not None:
        raise typer.BadParameter("Use either --text or --text-file, not both")
    agent_output = text
    if text_file is not None:
        agent_output = text_file.read_text(encoding="utf-8")
    plan = accelerate_agent_phase(
        AgentIntakeRequest(
            agent_output=agent_output,
            profile=profile,
            identity_context=(
                None
                if identity_context is None
                else _load_runtime_identity_context(identity_context)
            ),
            allow_live_connectors=allow_live_connectors,
        ),
        compact=compact,
    )
    payload = phase_acceleration_compact_payload(plan) if compact else plan.model_dump(mode="json")
    _dump(payload, output)


@agent_app.command("next")
def agent_next_command(
    intake_report: Annotated[
        Path,
        typer.Option("--intake-report", help="AgentIntakeReport JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Agent workflow profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Recommend next safe actions from an agent intake report."""

    data = load_data(intake_report)
    raw = data.get("agent_intake_report", data.get("report", data))
    if not isinstance(raw, dict):
        raise typer.BadParameter("agent intake report file must contain an object")
    report = AgentIntakeReport.model_validate(raw)
    _dump(recommend_agent_next_actions(report, profile).model_dump(mode="json"), output)


@agent_app.command("manifest")
def agent_manifest_command(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Print the machine-readable agent manifest."""

    manifest_path = Path("agent-manifest.json")
    if output is None and manifest_path.exists():
        _dump(json.loads(manifest_path.read_text(encoding="utf-8")), output)
        return
    _dump(agent_manifest_payload(), output)


@agent_inbox_app.command("init")
def agent_inbox_init_command(
    inbox: Annotated[
        Path,
        typer.Option("--inbox", help="Agent inbox JSON path to create or overwrite."),
    ],
    inbox_id: Annotated[
        str,
        typer.Option("--inbox-id", help="Portable inbox identifier."),
    ] = "agent-inbox",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Initialize a local agent inbox/outbox JSON file."""

    record = AgentInboxRecord(inbox_id=inbox_id)
    write_agent_inbox(inbox, record)
    _dump(record.model_dump(mode="json"), output)


@agent_inbox_app.command("append")
def agent_inbox_append_command(
    inbox: Annotated[
        Path,
        typer.Option("--inbox", help="Agent inbox JSON path."),
    ],
    message: Annotated[
        Path,
        typer.Option("--message", help="AgentMessageEnvelope JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Append one message envelope to a local inbox."""

    record = append_agent_message(inbox, _load_agent_message(message))
    _dump(record.model_dump(mode="json"), output)


@agent_inbox_app.command("export")
def agent_inbox_export_command(
    inbox: Annotated[
        Path,
        typer.Option("--inbox", help="Agent inbox JSON path."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Export one local agent inbox."""

    _dump(read_agent_inbox(inbox).model_dump(mode="json"), output)


@agent_inbox_app.command("verify")
def agent_inbox_verify_command(
    inbox: Annotated[
        Path,
        typer.Option("--inbox", help="Agent inbox JSON or JSONL path."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Message verification profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="Optional RuntimeIdentityContext JSON/YAML accepted by population Sybil checks.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify all local agent-message inbox entries."""

    report = receive_agent_inbox(
        inbox,
        _load_general_intake_policy(policy, profile=profile),
        _load_agent_message_verification_context(identity_context),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@agent_message_app.command("create")
def agent_message_create_command(
    sender: Annotated[
        str,
        typer.Option("--sender", help="Sender agent id."),
    ],
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal message content."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="Message content file."),
    ] = None,
    receiver: Annotated[
        str | None,
        typer.Option("--receiver", help="Optional receiver agent id."),
    ] = None,
    nonce: Annotated[
        str | None,
        typer.Option("--nonce", help="Optional replay nonce."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Create an unsigned local agent-message envelope."""

    if text is not None and text_file is not None:
        raise typer.BadParameter("Use either --text or --text-file, not both")
    content = text_file.read_text(encoding="utf-8") if text_file is not None else text
    if content is None:
        raise typer.BadParameter("message content requires --text or --text-file")
    message = create_agent_message(
        content,
        sender_agent_id=sender,
        receiver_agent_id=receiver,
        nonce=nonce,
    )
    _dump(message.model_dump(mode="json"), output)


@agent_message_app.command("send")
def agent_message_send_command(
    inbox: Annotated[
        Path,
        typer.Option("--inbox", help="Local agent inbox/outbox JSON path."),
    ],
    sender: Annotated[
        str,
        typer.Option("--sender", help="Sender agent id."),
    ],
    text: Annotated[
        str | None,
        typer.Option("--text", help="Literal message content."),
    ] = None,
    text_file: Annotated[
        Path | None,
        typer.Option("--text-file", help="Message content file."),
    ] = None,
    receiver: Annotated[
        str | None,
        typer.Option("--receiver", help="Optional receiver agent id."),
    ] = None,
    nonce: Annotated[
        str | None,
        typer.Option("--nonce", help="Optional replay nonce."),
    ] = None,
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Message verification profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="Optional RuntimeIdentityContext JSON/YAML accepted by population Sybil checks.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Create, verify, and append one local agent-message envelope."""

    if text is not None and text_file is not None:
        raise typer.BadParameter("Use either --text or --text-file, not both")
    content = text_file.read_text(encoding="utf-8") if text_file is not None else text
    if content is None:
        raise typer.BadParameter("message content requires --text or --text-file")
    message = create_agent_message(
        content,
        sender_agent_id=sender,
        receiver_agent_id=receiver,
        nonce=nonce,
    )
    report = deliver_agent_message(
        inbox,
        message,
        _load_general_intake_policy(policy, profile=profile),
        _load_agent_message_verification_context(identity_context),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@agent_message_app.command("receive")
def agent_message_receive_command(
    inbox: Annotated[
        Path,
        typer.Option("--inbox", help="Local agent inbox JSON or JSONL path."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Message verification profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="Optional RuntimeIdentityContext JSON/YAML accepted by population Sybil checks.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Receive and verify all messages in a local agent inbox."""

    report = receive_agent_inbox(
        inbox,
        _load_general_intake_policy(policy, profile=profile),
        _load_agent_message_verification_context(identity_context),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@agent_message_app.command("verify")
def agent_message_verify_command(
    message: Annotated[
        Path,
        typer.Option("--message", help="AgentMessageEnvelope JSON/YAML."),
    ],
    policy: Annotated[
        Path | None,
        typer.Option("--policy", help="Optional GeneralIntakePolicy JSON/YAML."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Message verification profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="Optional RuntimeIdentityContext JSON/YAML accepted by population Sybil checks.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify agent-message envelope shape and replay policy."""

    report = verify_agent_message(
        _load_agent_message(message),
        _load_general_intake_policy(policy, profile=profile),
        _load_agent_message_verification_context(identity_context),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@agent_message_app.command("contract")
def agent_message_contract_command(
    message: Annotated[
        Path,
        typer.Option("--message", help="AgentMessageEnvelope JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check portable agent-message envelope contract without trusting content."""

    report = check_agent_message_contract(_load_agent_message(message))
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@agent_message_app.command("ingest")
def agent_message_ingest_command(
    message: Annotated[
        Path,
        typer.Option("--message", help="AgentMessageEnvelope JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Message intake profile."),
    ] = "development",
    identity_context: Annotated[
        Path | None,
        typer.Option(
            "--identity-context",
            help="Optional RuntimeIdentityContext JSON/YAML accepted by population Sybil checks.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Ingest one agent message as packet candidate."""

    report = ingest_general_source(
        GeneralIntakeSource(source=str(message), kind=PacketSourceKind.AGENT_MESSAGE),
        GeneralIntakePolicy(profile=profile),
        _load_agent_message_verification_context(identity_context),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@identity_app.command("verify")
def identity_verify_command(
    identity: Annotated[
        Path,
        typer.Option("--identity", help="CryptographicAgentIdentity JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify a protocol-relative cryptographic agent identity."""

    report = verify_agent_identity(_load_agent_identity(identity))
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@identity_app.command("verify-attestation")
def identity_verify_attestation_command(
    attestation: Annotated[
        Path,
        typer.Option("--attestation", help="AgentIdentityAttestation JSON/YAML."),
    ],
    identities: Annotated[
        Path,
        typer.Option("--identities", help="Known CryptographicAgentIdentity list JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify a signed agent identity attestation."""

    report = verify_agent_attestation(
        _load_identity_attestation(attestation),
        _load_agent_identities(identities),
    )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@identity_app.command("sybil-check")
def identity_sybil_check_command(
    population: Annotated[
        Path,
        typer.Option("--population", help="AgentPopulationState JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check a population for protocol-relative Sybil-resistance failures."""

    parsed_population = _load_agent_population_state(population)
    ledger = check_sybil_resistance(
        parsed_population.population_id,
        parsed_population.cryptographic_identities,
        parsed_population.sybil_resistance_policy,
        [attestation.attestation_id for attestation in parsed_population.identity_attestations],
    )
    _dump(ledger.model_dump(mode="json"), output)
    if not ledger.accepted:
        raise typer.Exit(1)


@identity_app.command("explain-profile")
def identity_explain_profile_command(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Identity trust profile."),
    ] = "production",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Explain Sybil and packet-promotion policy for a trust profile."""

    sybil_policy = sybil_policy_for_profile(profile)
    promotion_policy = PacketPromotionPolicy.for_profile(profile)
    _dump(
        {
            "profile": sybil_policy.trust_profile.value,
            "sybil_policy": sybil_policy.model_dump(mode="json"),
            "packet_promotion_policy": promotion_policy.model_dump(mode="json"),
            "identity_limit": (
                "cryptographic identity proves protocol-relative key control only; "
                "it does not prove legal identity, real-world personhood, "
                "organizational authority, or global uniqueness"
            ),
        },
        output,
    )


@identity_app.command("derive-context")
def identity_derive_context_command(
    population: Annotated[
        Path,
        typer.Option("--population", help="AgentPopulationState JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Identity trust profile."),
    ] = "production",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Derive runtime identity context from a signed population."""

    context = derive_runtime_identity_context(_load_agent_population_state(population), profile)
    _dump(context.model_dump(mode="json"), output)
    if not context.accepted and profile.lower() in {"production", "adversarial"}:
        raise typer.Exit(1)


@runtime_store_app.command("init")
def runtime_store_init_command(
    store: Annotated[
        Path,
        typer.Option("--store", help="SQLite runtime store path."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Initialize a SQLite runtime store."""

    _dump(SQLiteRuntimeStore(store).record().model_dump(mode="json"), output)


@runtime_store_app.command("append")
def runtime_store_append_command(
    store: Annotated[
        Path,
        typer.Option("--store", help="SQLite runtime store path."),
    ],
    state: Annotated[
        Path | None,
        typer.Option("--state", help="Optional RuntimeState JSON/YAML to append."),
    ] = None,
    run: Annotated[
        Path | None,
        typer.Option("--run", help="Optional RuntimeRunReport JSON/YAML to append."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Append runtime state or run report records to a SQLite store."""

    runtime_store = SQLiteRuntimeStore(store)
    if state is not None:
        runtime_store.append_state(_load_runtime_state(state))
    if run is not None:
        runtime_store.append_run(_load_runtime_run_report(run))
    _dump(runtime_store.record().model_dump(mode="json"), output)


@runtime_store_app.command("load")
def runtime_store_load_command(
    store: Annotated[
        Path,
        typer.Option("--store", help="SQLite runtime store path."),
    ],
    state_id: Annotated[str, typer.Option("--state-id", help="Runtime state id.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Load one runtime state from a SQLite store."""

    state = SQLiteRuntimeStore(store).load_state(state_id)
    if state is None:
        _dump({"accepted": False, "reasons": ["runtime state not found"]}, output)
        raise typer.Exit(1)
    _dump(state.model_dump(mode="json"), output)


@runtime_store_app.command("export")
def runtime_store_export_command(
    store: Annotated[
        Path,
        typer.Option("--store", help="SQLite runtime store path."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Export a deterministic runtime store snapshot."""

    _dump(SQLiteRuntimeStore(store).snapshot().model_dump(mode="json"), output)


@ecpt_app.command("plan")
def ecpt_plan(
    state: Annotated[
        Path,
        typer.Option("--state", help="PhaseControlState JSON/YAML, optionally with actions."),
    ],
    target: Annotated[
        Path,
        typer.Option("--target", help="ASIProxyTargetContract or PhaseControlObjective JSON/YAML."),
    ],
    budget: Annotated[
        Path,
        typer.Option("--budget", help="Budget/objective JSON/YAML, optionally with actions."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Planner profile: development, research, or production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a deterministic ECPT ASI-proxy phase-control plan."""

    phase_state, state_actions = _load_phase_state(state)
    budget_data = load_data(budget)
    raw_budgets = budget_data.get("budgets")
    if isinstance(raw_budgets, dict):
        phase_state = phase_state.model_copy(update={"budgets": raw_budgets})
    objective = _load_phase_objective(target, budget_data)
    actions = state_actions
    if "actions" in budget_data:
        raw_actions = budget_data["actions"]
        if not isinstance(raw_actions, list):
            raise typer.BadParameter("budget file actions must be a list when present")
        actions.extend(PhaseControlAction.model_validate(item) for item in raw_actions)
    if not actions:
        raise typer.BadParameter("phase-control planning requires at least one action")
    report = build_phase_control_plan(phase_state, objective, actions, profile=profile)
    _dump(report.model_dump(mode="json"), output)


@ecpt_app.command("simulate")
def ecpt_simulate(
    state: Annotated[
        Path,
        typer.Option("--state", help="PhaseControlState JSON/YAML."),
    ],
    actions: Annotated[
        Path,
        typer.Option("--actions", help="JSON/YAML object containing an actions list."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Simulate finite ECPT reachable-mass response for proposed actions."""

    phase_state, _ = _load_phase_state(state)
    parsed_actions = _load_phase_actions(actions)
    target_nodes = sorted({action.target_node for action in parsed_actions})
    objective = PhaseControlObjective(
        objective_id="simulate-finite-reachable-mass",
        target=ASIProxyTargetContract(
            target_id="simulation-target",
            target_nodes=target_nodes,
        ),
        residual_budget=1.0,
        risk_tolerance=1.0,
    )
    report = build_phase_control_plan(phase_state, objective, parsed_actions)
    _dump(
        {
            "state_id": phase_state.state_id,
            "baseline_reachable_mass": dict(sorted(reachable_mass(phase_state.graph).items())),
            "controlled_reachable_mass": report.controlled_reachable_mass,
            "candidates": [
                candidate.model_dump(mode="json") for candidate in report.plan.candidates
            ],
            "safety_invariants": report.safety_invariants,
        },
        output,
    )


@ecpt_app.command("route-obligations")
def ecpt_route_obligations(
    audit: Annotated[
        Path,
        typer.Option("--audit", help="pic audit theory JSON output with ECPT external items."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Map ECPT external obligations to verifier route bindings."""

    data = load_data(audit)
    external_items = data.get("external_obligation_items", [])
    catalog = data.get("external_obligation_catalog")
    if isinstance(catalog, dict) and not external_items:
        external_items = catalog.get("obligations", [])
    if not isinstance(external_items, list):
        raise typer.BadParameter("audit JSON external obligations must be a list")
    specs = {
        key: spec
        for spec in list_adapter_route_specs()
        for key in {spec.route_id, spec.verifier_route}
    }
    routed: list[dict[str, Any]] = []
    for item in external_items:
        if not isinstance(item, dict):
            continue
        route_id = item.get("verifier_route") or item.get("route_id")
        spec = specs.get(str(route_id)) if route_id is not None else None
        binding = binding_for_route(spec.route_id) if spec is not None else None
        routed.append(
            {
                "item_id": item.get("item_id"),
                "label": item.get("label"),
                "obligation_category": item.get("obligation_category"),
                "verifier_route": route_id,
                "route_known": spec is not None,
                "required_evidence_kind": [] if spec is None else spec.required_evidence_kind,
                "binding": None if binding is None else binding.model_dump(mode="json"),
                "safe_default": item.get("safe_default") if spec is None else spec.safe_default,
                "residual_coordinates": item.get("residual_coordinates", []),
            }
        )
    _dump({"routed_obligations": routed}, output)


@phase_app.command("acceleration-report")
def phase_acceleration_report_command(
    target: Annotated[Path, typer.Option("--target", help="ASI-proxy target JSON/YAML.")],
    baseline: Annotated[
        Path,
        typer.Option("--baseline", help="Baseline upper envelope JSON/YAML."),
    ],
    capital: Annotated[
        Path,
        typer.Option("--capital", help="Runtime capital witness JSONL."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit target-valid CARA phase acceleration diagnostics."""

    _dump(
        phase_acceleration_report(
            load_data(target),
            load_data(baseline),
            _load_jsonl_events(capital),
        ),
        output,
    )


@alt_app.command("capital-witness")
def alt_capital_witness_command(
    packet: Annotated[Path, typer.Option("--packet", help="ALT packet/report JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit a runtime capital witness without promoting proxy-only evidence."""

    _dump(capital_witness_report(load_data(packet)), output)


@alt_app.command("deployment-admissibility")
def alt_deployment_admissibility_command(
    packet: Annotated[Path, typer.Option("--packet", help="ALT packet/report JSON/YAML.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile name.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check deployment admissibility without provider dispatch."""

    _dump(deployment_admissibility_report(load_data(packet), profile=profile), output)


@ecpt_app.command("target-validity-check")
def ecpt_target_validity_check_command(
    target: Annotated[Path, typer.Option("--target", help="ASI-proxy target JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check target validity before acceleration comparison."""

    _dump(target_validity_check(load_data(target)), output)


@ecpt_app.command("baseline-envelope-check")
def ecpt_baseline_envelope_check_command(
    baseline: Annotated[
        Path,
        typer.Option("--baseline", help="Baseline upper envelope JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check baseline upper-envelope completeness and freshness."""

    _dump(baseline_envelope_check(load_data(baseline)), output)


@ecpt_app.command("activation-check")
def ecpt_activation_check_command(
    state: Annotated[Path, typer.Option("--state", help="Finite ECPT state/graph JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a finite ECPT activation construction report."""

    _dump(activation_construction_report(load_data(state)), output)


@ecpt_app.command("phase-response-step")
def ecpt_phase_response_step_command(
    state: Annotated[Path, typer.Option("--state", help="Finite ECPT state JSON/YAML.")],
    control: Annotated[Path, typer.Option("--control", help="Control action JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report one finite phase-response control step."""

    _dump(phase_response_control_step(load_data(state), load_data(control)), output)


@ecpt_app.command("response-policy")
def ecpt_response_policy_command(
    trajectory: Annotated[Path, typer.Option("--trajectory", help="Trajectory JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check a path-law response policy report."""

    _dump(path_law_response_policy_report(load_data(trajectory)), output)


@sqot_app.command("protocol-integrity")
def sqot_protocol_integrity_command(
    state: Annotated[Path, typer.Option("--state", help="SQOT protocol state JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check SQOT protocol integrity without scalar-only safety promotion."""

    _dump(sqot_protocol_integrity_report(load_data(state)), output)


@sqot_app.command("resource-exchange")
def sqot_resource_exchange_command(
    state: Annotated[Path, typer.Option("--state", help="SQOT resource exchange JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check cross-modal resource exchange ledgers."""

    _dump(sqot_resource_exchange_report(load_data(state)), output)


@sqot_app.command("probe-stop")
def sqot_probe_stop_command(
    probe_tree: Annotated[
        Path,
        typer.Option("--probe-tree", help="Finite probe tree JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check whether probe planning should stop, abstain, or quarantine."""

    _dump(probe_stop_report(load_data(probe_tree)), output)


@bit_app.command("mec-frontier")
def bit_mec_frontier_command(
    certificates: Annotated[
        Path,
        typer.Option("--certificates", help="BIT certificate JSONL."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Extract a finite minimal-effective-condition frontier."""

    _dump(bit_mec_frontier_report(_load_jsonl_events(certificates)), output)


@bit_app.command("compiler-report")
def bit_compiler_report_command(
    certificates: Annotated[
        Path,
        typer.Option("--certificates", help="BIT certificate JSONL."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compile finite certificate diagnostics without promoting settlement."""

    _dump(bit_certificate_compiler_report(_load_jsonl_events(certificates)), output)


@bit_app.command("cegar-barrier")
def bit_cegar_barrier_command(
    barrier: Annotated[Path, typer.Option("--barrier", help="CEGAR barrier JSON/YAML.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check finite CEGAR simulation barrier evidence."""

    _dump(cegar_simulation_barrier_report(load_data(barrier)), output)


@bit_app.command("dynamic-regime")
def bit_dynamic_regime_command(
    surface: Annotated[
        Path,
        typer.Option("--surface", help="Dynamic-regime acceleration surface JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check a dynamic-regime acceleration surface."""

    _dump(dynamic_regime_acceleration_report(load_data(surface)), output)


@mcp_app.command("descriptor-check")
def mcp_descriptor_check_command(
    descriptor: Annotated[Path, typer.Option("--descriptor", help="MCP descriptor JSON/YAML.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile name.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an MCP tool descriptor as untrusted candidate evidence."""

    _dump(mcp_tool_descriptor_report(load_data(descriptor), profile=profile), output)


@mcp_app.command("invocation-preflight")
def mcp_invocation_preflight_command(
    descriptor: Annotated[Path, typer.Option("--descriptor", help="MCP descriptor JSON/YAML.")],
    call: Annotated[Path, typer.Option("--call", help="MCP call JSON/YAML.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile name.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Preflight an MCP invocation without dispatching the tool."""

    _dump(
        mcp_tool_invocation_preflight(load_data(descriptor), load_data(call), profile=profile),
        output,
    )


@a2a_app.command("card-check")
def a2a_card_check_command(
    card: Annotated[Path, typer.Option("--card", help="A2A agent card JSON/YAML.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile name.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an A2A agent card without granting delegated authority."""

    _dump(a2a_agent_card_report(load_data(card), profile=profile), output)


@a2a_app.command("handoff-check")
def a2a_handoff_check_command(
    handoff: Annotated[Path, typer.Option("--handoff", help="A2A handoff JSON/YAML.")],
    profile: Annotated[str, typer.Option("--profile", help="Profile name.")] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check an A2A task handoff as provider evidence, not settlement."""

    _dump(a2a_task_handoff_report(load_data(handoff), profile=profile), output)


@trc_app.command("trace-adapter")
def trc_trace_adapter_command(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Trace JSON/YAML to adapt."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Adapt agent/workflow trace data into a TRC typed trace."""

    report = adapt_trc_trace(load_data(input_path))
    _dump(report.model_dump(mode="json"), output)


@trc_app.command("trace-normalize")
def trc_trace_normalize_command(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Agent trace JSON/YAML to normalize."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Normalize an agent trace into a practical finite TraceNF."""

    _dump(trace_normal_form_report(load_data(input_path)), output)


@trc_app.command("trace-check")
def trc_trace_check_command(
    trace: Annotated[
        Path,
        typer.Option("--trace", help="TraceNF JSON/YAML to check."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Check a practical TraceNF without promoting execution claims."""

    _dump(trace_check_report(load_data(trace)), output)


@trc_app.command("operation-gate")
def trc_operation_gate_command(
    trace: Annotated[
        Path,
        typer.Option("--trace", help="TraceNF or PIC trace-check report JSON/YAML."),
    ],
    provider_profile: Annotated[
        Path | None,
        typer.Option("--provider-profile", help="Provider/authority gate profile JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit a TRC operation gate report without dispatching a provider."""

    profile = load_data(provider_profile) if provider_profile else None
    if profile is not None and not isinstance(profile, dict):
        raise typer.BadParameter("provider profile must be a JSON/YAML object")
    _dump(operation_gate_report(load_data(trace), provider_profile=profile), output)


@trc_app.command("trace-to-packet")
def trc_trace_to_packet_command(
    trace: Annotated[
        Path,
        typer.Option("--trace", help="TraceNF JSON/YAML to convert."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Convert TraceNF into a candidate packet."""

    _dump(trace_packet_candidate(load_data(trace)), output)


@trc_app.command("tool-trace")
def trc_tool_trace_command(
    events: Annotated[
        Path,
        typer.Option("--events", help="JSONL tool events or JSON object with events."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Adapt JSONL agent tool-call events into typed trace records."""

    if events.suffix.lower() == ".jsonl":
        report = adapt_tool_trace_events(_load_jsonl_events(events))
    else:
        data = load_data(events)
        raw_events = data.get("events", data.get("tool_calls", []))
        if not isinstance(raw_events, list):
            raise typer.BadParameter("tool trace JSON must contain events or tool_calls list")
        report = adapt_tool_trace_events([item for item in raw_events if isinstance(item, dict)])
    _dump(report.model_dump(mode="json"), output)


@trc_app.command("action-boundary")
def trc_action_boundary_command(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Runtime report JSON/YAML."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Extract typed action-boundary diagnostics from a runtime report."""

    report = action_boundary_from_runtime_report(load_data(report_path))
    _dump(report.model_dump(mode="json"), output)


@app.command(name="compile")
def compile_command(
    records: Annotated[
        Path,
        typer.Option("--records", "-r", help="JSON/YAML file with a top-level records list."),
    ],
    archive_cap: Annotated[
        int, typer.Option("--archive-cap", help="Returned efficiency archive cap.")
    ] = 64,
    fail_on: Annotated[
        list[str] | None,
        typer.Option("--fail-on", help="Fail on invalid-main-trace."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compile typed frontier records into TRC strata."""

    data = load_data(records)
    raw_records = data.get("records")
    if not isinstance(raw_records, list):
        raise typer.BadParameter("records file must contain a top-level 'records' list")
    frontier_records = [FrontierRecord.model_validate(item) for item in raw_records]
    try:
        fail_reasons = set(fail_on or [])
        result = compile_frontier(
            frontier_records,
            archive_cap=archive_cap,
            fail_on_invalid_main_trace="invalid-main-trace" in fail_reasons,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(result.model_dump(mode="json"), output)


@evidence_app.command("verify")
def evidence_verify(
    envelope: Annotated[
        Path,
        typer.Option("--envelope", "-e", help="VerifierEvidenceEnvelope JSON/YAML file."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Evidence verification profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify a finite evidence envelope against its adapter route contract."""

    data = load_data(envelope)
    evidence = VerifierEvidenceEnvelope.model_validate(data)
    specs = {spec.route_id: spec for spec in list_adapter_route_specs()}
    spec = specs.get(evidence.route_id)
    if spec is None:
        raise typer.BadParameter(f"unknown adapter route {evidence.route_id!r}")
    result = resolve_adapter_route(spec, evidence, base_dir=envelope.parent, profile=profile)
    _dump(result.model_dump(mode="json"), output)
    if not result.accepted:
        raise typer.Exit(1)


@evidence_app.command("discharge")
def evidence_discharge(
    envelope: Annotated[
        Path,
        typer.Option("--envelope", "-e", help="VerifierEvidenceEnvelope JSON/YAML file."),
    ],
    obligations: Annotated[
        Path,
        typer.Option("--obligations", help="JSON/YAML object with an obligations list."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Evidence verification profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify evidence and emit a provenance-bound ExternalVerifierHook."""

    evidence = VerifierEvidenceEnvelope.model_validate(load_data(envelope))
    obligation_data = load_data(obligations)
    raw_obligations = obligation_data.get("obligations")
    if not isinstance(raw_obligations, list):
        raise typer.BadParameter("obligations file must contain a top-level 'obligations' list")
    parsed_obligations = [ExternalProofObligation.model_validate(item) for item in raw_obligations]
    specs = {spec.route_id: spec for spec in list_adapter_route_specs()}
    spec = specs.get(evidence.route_id)
    if spec is None:
        raise typer.BadParameter(f"unknown adapter route {evidence.route_id!r}")
    resolution = resolve_adapter_route(spec, evidence, base_dir=envelope.parent, profile=profile)
    hook = resolution.to_external_verifier_hook()
    check = check_external_verifier_hook(hook, parsed_obligations)
    data = {
        "resolution": resolution.model_dump(mode="json"),
        "hook": hook.model_dump(mode="json"),
        "check": check.model_dump(mode="json"),
    }
    _dump(data, output)
    if not resolution.accepted or not check.accepted:
        raise typer.Exit(1)


@demo_app.command("datacenter")
def demo_datacenter(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run the TRC AI datacenter cooling and management-link example."""

    result = datacenter_demo()
    _dump(result.model_dump(mode="json"), output)


@demo_app.command("bootstrap")
def demo_bootstrap(
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Directory where the curated installed-package demo files are copied.",
        ),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Replace existing curated demo files in output-dir."),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Export curated install-time demo assets from package data."""

    written = _copy_installed_demo(output_dir, overwrite)
    agent_output_path = output_dir / "agent_output.txt"
    runtime_state_path = output_dir / "runtime_state.json"
    runtime_input_path = output_dir / "runtime_step_input.json"
    alt_packet_path = output_dir / "alt_admission_packet.json"
    agent_inbox_path = output_dir / "agent_inbox.json"
    runtime_report_path = output_dir / "runtime_step_report.json"
    packet_path = output_dir / "packet_envelope.json"
    dashboard_path = output_dir / "phase_dashboard.json"
    phase_lab_report_path = output_dir / "phase_lab_runtime_report.json"
    phase_lab_threshold_path = output_dir / "phase_lab_threshold.json"
    phase_lab_store_path = output_dir / "phase-lab"
    merged_packets_path = output_dir / "merged-packets.json"
    observation_path = output_dir / "observation.json"
    recommended_next_commands = [
        f"pic agent check --text-file {agent_output_path} --profile development",
        f"pic runtime step --state {runtime_state_path} "
        f"--input {runtime_input_path} --profile development",
        f"pic agent message receive --inbox {agent_inbox_path}",
        f"pic agent inbox verify --inbox {agent_inbox_path}",
        f"pic alt admit --packet {alt_packet_path}",
        "pic phase benchmark-suite --profile development --format json",
        f"pic phase dashboard --runtime-report {runtime_report_path} --profile development",
        f"pic packet inspect --packet {packet_path}",
        f"pic packet merge --packets {packet_path} --output {merged_packets_path}",
        f"pic packet lineage --packet {merged_packets_path}",
        f"pic phase observe --reports {dashboard_path} --output {observation_path}",
        f"pic phase lab init --output-dir {phase_lab_store_path}",
        f"pic phase lab ingest --store {phase_lab_store_path} --report {phase_lab_report_path}",
        f"pic phase lab observe --store {phase_lab_store_path} --window latest",
        f"pic phase lab graph --store {phase_lab_store_path}",
        f"pic phase lab closure --store {phase_lab_store_path}",
        f"pic phase lab executable-paths --store {phase_lab_store_path}",
        (
            f"pic phase lab certify --store {phase_lab_store_path} "
            f"--threshold {phase_lab_threshold_path}"
        ),
        "pic audit canonical-readiness --profile development --format json",
    ]
    recommended_next_invocations = [
        {
            "invocation_id": "agent-check-bootstrapped-text",
            "argv": [
                "pic",
                "agent",
                "check",
                "--text-file",
                str(agent_output_path),
                "--profile",
                "development",
            ],
        },
        {
            "invocation_id": "runtime-step-bootstrapped",
            "argv": [
                "pic",
                "runtime",
                "step",
                "--state",
                str(runtime_state_path),
                "--input",
                str(runtime_input_path),
                "--profile",
                "development",
            ],
        },
        {
            "invocation_id": "packet-merge-bootstrapped",
            "argv": [
                "pic",
                "packet",
                "merge",
                "--packets",
                str(packet_path),
                "--output",
                str(merged_packets_path),
            ],
        },
        {
            "invocation_id": "phase-observe-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "observe",
                "--reports",
                str(dashboard_path),
                "--output",
                str(observation_path),
            ],
        },
        {
            "invocation_id": "phase-lab-ingest-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "lab",
                "ingest",
                "--store",
                str(phase_lab_store_path),
                "--report",
                str(phase_lab_report_path),
            ],
        },
        {
            "invocation_id": "phase-lab-observe-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "lab",
                "observe",
                "--store",
                str(phase_lab_store_path),
                "--window",
                "latest",
            ],
        },
        {
            "invocation_id": "phase-lab-graph-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "lab",
                "graph",
                "--store",
                str(phase_lab_store_path),
            ],
        },
        {
            "invocation_id": "phase-lab-closure-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "lab",
                "closure",
                "--store",
                str(phase_lab_store_path),
            ],
        },
        {
            "invocation_id": "phase-lab-executable-paths-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "lab",
                "executable-paths",
                "--store",
                str(phase_lab_store_path),
            ],
        },
        {
            "invocation_id": "phase-lab-certify-bootstrapped",
            "argv": [
                "pic",
                "phase",
                "lab",
                "certify",
                "--store",
                str(phase_lab_store_path),
                "--threshold",
                str(phase_lab_threshold_path),
            ],
        },
        {
            "invocation_id": "canonical-readiness",
            "argv": [
                "pic",
                "audit",
                "canonical-readiness",
                "--profile",
                "development",
                "--format",
                "json",
            ],
        },
    ]
    _dump(
        {
            "accepted": True,
            "bundle": _demo_manifest(),
            "files": written,
            "output_dir": str(output_dir),
            "recommended_next_commands": recommended_next_commands,
            "recommended_next_invocations": recommended_next_invocations,
            "settled": False,
            "workflow_usable": True,
        },
        output,
    )


@demo_app.command("installed-smoke")
def demo_installed_smoke(
    profile: Annotated[
        str,
        typer.Option("--profile", help="Runtime profile for the installed-package smoke check."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run a no-network smoke check that works from a PyPI-installed wheel."""

    demo_text = _demo_resource_text("agent_output.txt").strip()
    report = run_agent_intake(
        AgentIntakeRequest(
            agent_output=demo_text,
            profile=profile,
            allow_live_connectors=True,
        )
    )
    _dump(
        {
            "accepted": report.accepted,
            "demo_id": f"installed-smoke:{__version__}",
            "operationally_usable": report.operationally_usable,
            "profile": profile,
            "recommended_next_commands": [
                f'pic agent check --text "{demo_text}" --profile {profile}',
                "pic demo bootstrap --output-dir pic-demo",
                (
                    f"pic runtime step --state pic-demo/runtime_state.json "
                    f"--input pic-demo/runtime_step_input.json --profile {profile}"
                ),
                "pic agent message receive --inbox pic-demo/agent_inbox.json",
                "pic alt admit --packet pic-demo/alt_admission_packet.json",
                f"pic phase benchmark-suite --profile {profile} --format json",
                "pic phase dashboard --runtime-report pic-demo/runtime_step_report.json "
                f"--profile {profile}",
                "pic packet inspect --packet pic-demo/packet_envelope.json",
                "pic packet merge --packets pic-demo/packet_envelope.json "
                "--output pic-demo/merged-packets.json",
                "pic packet lineage --packet pic-demo/merged-packets.json",
                "pic phase observe --reports pic-demo/phase_dashboard.json "
                "--output pic-demo/observation.json",
                "pic phase lab init --output-dir pic-demo/phase-lab",
                "pic phase lab ingest --store pic-demo/phase-lab "
                "--report pic-demo/phase_lab_runtime_report.json",
                "pic phase lab observe --store pic-demo/phase-lab --window latest",
                "pic phase lab graph --store pic-demo/phase-lab",
                "pic phase lab closure --store pic-demo/phase-lab",
                "pic phase lab executable-paths --store pic-demo/phase-lab",
                "pic phase lab certify --store pic-demo/phase-lab "
                "--threshold pic-demo/phase_lab_threshold.json",
                f"pic audit canonical-readiness --profile {profile} --format json",
            ],
            "recommended_next_invocations": [
                {
                    "invocation_id": "demo-bootstrap",
                    "argv": ["pic", "demo", "bootstrap", "--output-dir", "pic-demo"],
                },
                {
                    "invocation_id": "sidecar-packet-merge",
                    "argv": [
                        "pic",
                        "packet",
                        "merge",
                        "--packets",
                        "pic-demo/packet_envelope.json",
                        "--output",
                        "pic-demo/merged-packets.json",
                    ],
                },
                {
                    "invocation_id": "phase-lab-ingest",
                    "argv": [
                        "pic",
                        "phase",
                        "lab",
                        "ingest",
                        "--store",
                        "pic-demo/phase-lab",
                        "--report",
                        "pic-demo/phase_lab_runtime_report.json",
                    ],
                },
                {
                    "invocation_id": "canonical-readiness",
                    "argv": [
                        "pic",
                        "audit",
                        "canonical-readiness",
                        "--profile",
                        profile,
                        "--format",
                        "json",
                    ],
                },
            ],
            "residual_summary": report.residual_summary,
            "runtime_report": report.runtime_report.model_dump(mode="json"),
            "safety_invariants": agent_safety_invariants(),
            "settled": report.settled,
            "version": __version__,
            "workflow_usable": bool(report.accepted),
        },
        output,
    )


@app.command()
def explain(
    topic: Annotated[
        str,
        typer.Argument(help="Topic: ecpt, bit, trc, status, license, coverage, or external."),
    ],
    item_id: Annotated[
        str | None,
        typer.Argument(help="Optional item id for 'coverage' or 'external'."),
    ] = None,
    from_snapshot: Annotated[
        bool,
        typer.Option(
            "--from-snapshot",
            help="Explain coverage/external items from bundled derived snapshots.",
        ),
    ] = False,
    artifact: Annotated[
        str | None,
        typer.Option("--artifact", help="Snapshot artifact key when using --from-snapshot."),
    ] = None,
) -> None:
    """Print concise scientific framing for a subsystem."""

    if topic.lower() in {"coverage", "external"}:
        if item_id is None:
            raise typer.BadParameter(f"{topic.lower()} explanation requires an item id")
        if from_snapshot:
            snapshot_record = find_snapshot_item(
                item_id,
                artifact_key=artifact,
                external_only=topic.lower() == "external",
            )
            if snapshot_record is None:
                raise typer.BadParameter(f"snapshot {topic.lower()} item {item_id!r} was not found")
            _dump(snapshot_record.model_dump(mode="json"))
            return
        canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
        if not canonical_dir:
            raise typer.BadParameter(f"set PIC_CANONICAL_TEX_DIR to explain {topic.lower()} items")
        for filename in [
            "Executable Capability Percolation Theory.tex",
            "Bottleneck Inversion Theory.tex",
            "Typed Reality Compilation.tex",
        ]:
            source = Path(canonical_dir) / filename
            if not source.exists():
                continue
            if topic.lower() == "external":
                audit = audit_theory_source(source, strict_projection=True)
                catalog = audit.external_obligation_catalog
                if catalog is None:
                    continue
                for obligation in catalog.obligations:
                    if obligation.item_id == item_id:
                        _dump(obligation.model_dump(mode="json"))
                        return
                continue
            coverage_record = extract_theory_coverage(source)
            for coverage_item in coverage_record.items:
                if coverage_item.item_id == item_id:
                    _dump(coverage_item.model_dump(mode="json"))
                    return
        raise typer.BadParameter(f"{topic.lower()} item {item_id!r} was not found")

    explanations = {
        "ecpt": (
            "ECPT models protocol-relative capability propagation through finite "
            "hypergraphs, activation laws, queue/capacity ledgers, and checker output."
        ),
        "bit": (
            "BIT reports only unit-compatible, intervention-backed potential coordinates "
            "with finite witnesses and explicit selection/resource charges."
        ),
        "trc": (
            "TRC compiles observed cyber-physical infrastructure into typed process "
            "frontiers with residual, tolerance, resource, and trace-normal-form ledgers."
        ),
        "status": (
            "Status labels are not scalar confidence scores. Settled claims require all "
            "settled obligations; provisional, speculative, risk, relaxed, and diagnostic "
            "records do not silently promote."
        ),
        "license": (
            "Repository code is Apache-2.0. Cited Zenodo papers are CC-BY-4.0 and are "
            "not vendored by this package."
        ),
    }
    key = topic.lower()
    if key not in explanations:
        raise typer.BadParameter(f"unknown topic {topic!r}")
    console.print(explanations[key])
