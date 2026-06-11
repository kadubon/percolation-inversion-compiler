"""Command-line interface for Percolation Inversion Compiler."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.agent import (
    AgentIntakeReport,
    AgentIntakeRequest,
    agent_feature_readiness,
    agent_manifest_payload,
    agent_network_readiness,
    build_agent_communication_guide,
    build_agent_workflow_guide,
    minimal_runtime_state,
    recommend_agent_next_actions,
    run_agent_intake,
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
from percolation_inversion_compiler.ecology import (
    AgentInboxRecord,
    AgentMessageEnvelope,
    AgentMessageVerificationContext,
    CapabilityBasinContract,
    EdgeRelationVerifierSpec,
    EdgeWitnessCertificate,
    GeneralIntakePolicy,
    GeneralIntakeReport,
    GeneralIntakeSource,
    PacketPromotionPolicy,
    PacketSourceKind,
    ProtocolFrameDigest,
    PsiDashboard,
    WebFetchPolicy,
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
from percolation_inversion_compiler.io import (
    audit_theory_source,
    build_operational_readiness_report,
    build_sbom_document,
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
    validate_canonical_source,
    validate_data,
    verify_provenance_manifest,
)
from percolation_inversion_compiler.io.provenance import ProvenanceManifest
from percolation_inversion_compiler.io.schema import load_data
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
from percolation_inversion_compiler.trc import compile_frontier, datacenter_demo

app = typer.Typer(
    help="Finite certificate compiler toolkit for ECPT, BIT, TRC, and SQOT.",
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
ecpt_app = typer.Typer(help="Run ECPT active phase-control planning tools.")
sqot_app = typer.Typer(help="Run SQOT salience-queue scheduling tools.")
ecology_app = typer.Typer(help="Run ECPT capability packet ecology tools.")
ecology_policy_app = typer.Typer(help="Explain bounded general-intake policy presets.")
runtime_app = typer.Typer(help="Run ECPT active agent runtime loops and local service.")
runtime_store_app = typer.Typer(help="Manage persistent runtime stores.")
identity_app = typer.Typer(help="Verify cryptographic agent identities and Sybil ledgers.")
agent_app = typer.Typer(help="Agent-facing shortcuts for PIC runtime integration.")
agent_inbox_app = typer.Typer(help="Manage local agent inbox/outbox records.")
agent_message_app = typer.Typer(help="Create, verify, and ingest agent message envelopes.")
app.add_typer(demo_app, name="demo")
app.add_typer(audit_app, name="audit")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(evidence_app, name="evidence")
app.add_typer(routes_app, name="routes")
app.add_typer(provenance_app, name="provenance")
app.add_typer(sbom_app, name="sbom")
app.add_typer(parse_app, name="parse")
app.add_typer(ecpt_app, name="ecpt")
app.add_typer(sqot_app, name="sqot")
app.add_typer(ecology_app, name="ecology")
ecology_app.add_typer(ecology_policy_app, name="policy")
app.add_typer(runtime_app, name="runtime")
runtime_app.add_typer(runtime_store_app, name="store")
app.add_typer(identity_app, name="identity")
app.add_typer(agent_app, name="agent")
agent_app.add_typer(agent_inbox_app, name="inbox")
agent_app.add_typer(agent_message_app, name="message")
console = Console()


def _dump(data: Any, output: Path | None = None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, default=str)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        console.print_json(text)


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
    allow_live_connectors: bool = False,
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
    return RuntimeStepReport.model_validate(raw)


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
        typer.Option("--canonical-key", help="Canonical key: ecpt, bit, or trc."),
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


@snapshot_app.command("show")
def snapshot_show(
    artifact: Annotated[
        str,
        typer.Option("--artifact", "-a", help="Snapshot artifact key: ecpt, bit, trc, or sqot."),
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

    grammar = strict_tex_parse_report(source)
    coverage_record = extract_theory_coverage(source)
    canonical_key = "sqot" if source.name == "Salience-Queue Occupation Theory.tex" else None
    audit = audit_theory_source(source, canonical_key=canonical_key, strict_projection=True)
    data = {
        "source": str(source),
        "strict_grammar": grammar.model_dump(mode="json"),
        "coverage": coverage_record.model_dump(mode="json"),
        "coverage_counts": coverage_record.counts_by_status(),
        "audit": audit.model_dump(mode="json"),
    }
    _dump(data, output)
    if strict_grammar and not grammar.accepted:
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
            help="Explicitly enable live web/connector fetches.",
        ),
    ] = False,
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
            help="Explicitly enable live web fetches.",
        ),
    ] = False,
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
            help="Show the policy with live fetch permission enabled or disabled.",
        ),
    ] = False,
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
            help="Allow explicitly requested live connector ingestion.",
        ),
    ] = False,
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
    parsed_input = _load_runtime_step_input(step_input)
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
            help="Allow explicitly requested live connector ingestion.",
        ),
    ] = False,
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
    parsed_inputs = _load_runtime_inputs(inputs)
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
            help="Allow live connector use when requests also opt in.",
        ),
    ] = False,
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
            help="Describe the workflow with live connectors explicitly enabled.",
        ),
    ] = False,
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
            help="Check readiness for explicit live connector opt-in.",
        ),
    ] = False,
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
            help="Explicitly allow runtime live connector ingestion when the input also opts in.",
        ),
    ] = False,
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
    if manifest_path.exists():
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
