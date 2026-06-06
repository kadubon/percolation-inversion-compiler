from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.core import AdapterRouteSpec, VerifierEvidenceEnvelope
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    EdgeWitnessCertificate,
    PacketPromotionPolicy,
    PacketSourceKind,
    build_edge_witnesses,
    build_packet_registry,
    check_basin_reachability,
    edge_certificate_from_witness,
    verify_edge_witness_certificate,
)
from percolation_inversion_compiler.io.schema import load_data, schema_by_type
from percolation_inversion_compiler.runtime import (
    AgentRuntimeConfig,
    RuntimeActionResult,
    RuntimeRunReport,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    apply_action_results,
    build_runtime_run_report,
    build_runtime_step,
    certify_runtime_acceleration,
    compare_runtime_runs,
    create_runtime_app,
    promote_packet_candidate,
    resolve_step_evidence,
)

runner = CliRunner()


def _state() -> RuntimeState:
    return RuntimeState.model_validate(load_data("examples/runtime_state.json"))


def _input_with_evidence() -> RuntimeStepInput:
    return RuntimeStepInput.model_validate(
        load_data("examples/runtime_step_input_with_evidence.json")
    )


def test_evidence_resolution_promotes_finite_scope_packets_without_settling() -> None:
    state = _state()
    step_input = _input_with_evidence()
    batch = resolve_step_evidence(step_input, profile="production")
    assert batch.accepted
    assert batch.resolutions[0].accepted
    assert batch.resolutions[0].finite_scope_usable
    assert not batch.resolutions[0].settled

    report = build_runtime_step(state, step_input, AgentRuntimeConfig(profile="production"))
    assert report.evidence_resolution_batch.accepted
    assert report.promotion_report.verified_packets
    assert report.verified_packet_count >= len(report.promotion_report.verified_packets)
    assert not report.settled
    assert report.acceleration_certificate_eligible
    assert any(
        packet.residual_external_obligations for packet in report.promotion_report.verified_packets
    )


def test_packet_promotion_fails_closed_on_hash_authority_route_and_rollback() -> None:
    candidate = CapabilityPacketCandidate(
        packet_id="packet:unsafe",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref="unsafe",
        content_sha256="3" * 64,
        claim="Unsafe packet must not promote.",
        evidence_refs=["sha256:" + "4" * 64],
        receiver_family=["agent"],
        verifier_routes=["missing.route"],
        authority_required=True,
        authority_granted=False,
        route_safe=False,
        evidence_hash_valid=False,
        rollback_available=False,
    )
    result = promote_packet_candidate(candidate, [], [], PacketPromotionPolicy())
    assert result.__class__.__name__ == "PacketRejection"
    assert result.residual_ledger.burden_sum() > 0.0
    assert any("hash" in reason or "route" in reason for reason in result.reasons)


def test_evidence_resolution_unknown_route_and_ref_debt() -> None:
    step_input = RuntimeStepInput(
        input_id="unknown-evidence",
        evidence_envelope_refs=["external-envelope.json"],
        evidence_envelopes=[
            VerifierEvidenceEnvelope(
                envelope_id="unknown-envelope",
                route_id="missing.route",
                obligation_ids=["obligation:missing-route"],
            )
        ],
    )
    batch = resolve_step_evidence(step_input, profile="production")
    assert not batch.accepted
    assert "external-envelope.json" in batch.unresolved_envelope_refs
    assert "obligation:missing-route" in batch.rejected_obligations
    assert batch.residual_ledger.burden_sum() >= 2.0
    custom_spec = AdapterRouteSpec(
        route_id="custom.route",
        verifier_route="custom.verifier.route",
        obligation_category="custom",
        required_evidence_kind=[],
        residual_policy="preserve-custom",
        safe_default="diagnostic-custom",
    )
    custom_batch = resolve_step_evidence(
        RuntimeStepInput(
            input_id="custom-evidence",
            evidence_envelopes=[
                VerifierEvidenceEnvelope(
                    envelope_id="custom-envelope",
                    route_id="custom.verifier.route",
                )
            ],
        ),
        route_catalog={"custom.route": custom_spec},
    )
    assert custom_batch.resolutions[0].route_id == "custom.route"


def test_packet_promotion_policy_branches_for_edges_and_external_residuals() -> None:
    batch = resolve_step_evidence(_input_with_evidence(), profile="production")
    accepted_resolution = batch.resolutions[0]
    rejected_resolution = accepted_resolution.model_copy(update={"accepted": False})
    candidate = CapabilityPacketCandidate(
        packet_id="packet:policy",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref="policy",
        content_sha256="9" * 64,
        claim="Policy branch packet",
        evidence_refs=["sha256:" + "9" * 64],
        receiver_family=[],
        verifier_routes=[accepted_resolution.route_id],
        expires_at="expired",
        rollback_available=True,
    )
    low_edge = EdgeWitnessCertificate(
        certificate_id="edge-certificate:low",
        edge_id="edge:low",
        source_packet_ids=["packet:source"],
        target_packet_id="packet:policy",
        evidence_refs=["sha256:" + "9" * 64],
        confidence_lower_bound=0.0,
        accepted=True,
    )
    result = promote_packet_candidate(
        candidate,
        [accepted_resolution],
        [low_edge],
        PacketPromotionPolicy(
            require_edge_certificate=True,
            allow_residual_external_obligations=False,
        ),
    )
    assert result.__class__.__name__ == "PacketRejection"
    assert "packet candidate is expired" in result.reasons
    assert "packet receiver family is empty" in result.reasons
    assert "packet has no accepted edge certificate" in result.reasons
    assert "packet has unresolved external domain obligations" in result.reasons
    rejected = promote_packet_candidate(
        candidate.model_copy(update={"expires_at": None, "receiver_family": ["agent"]}),
        [rejected_resolution],
        [],
        PacketPromotionPolicy(require_edge_certificate=False),
    )
    assert "packet verifier route resolution is rejected" in rejected.reasons


def test_edge_certificate_and_basin_reachability_are_finite_checks() -> None:
    source = CapabilityPacketCandidate(
        packet_id="packet:source",
        source_ref="source",
        content_sha256="5" * 64,
        claim="source phase packet",
        evidence_refs=["sha256:" + "5" * 64],
        receiver_family=["agent"],
        tags=["phase"],
    )
    target = CapabilityPacketCandidate(
        packet_id="packet:target",
        source_ref="target",
        content_sha256="6" * 64,
        claim="target phase packet",
        dependencies=["packet:source"],
        evidence_refs=["sha256:" + "6" * 64],
        receiver_family=["agent"],
        tags=["phase"],
        verifier_routes=["adapters.domain.verify_ecpt_proxy_target_contract"],
    )
    registry = build_packet_registry([source, target], build_edge_witnesses([source, target]))
    edge_certificate = edge_certificate_from_witness(registry.edges[0])
    check = verify_edge_witness_certificate(registry, edge_certificate)
    assert check.accepted

    basin = CapabilityBasinContract.model_validate(load_data("examples/ecpt_basin_contract.json"))
    reachability = check_basin_reachability(registry, basin)
    assert reachability.accepted
    assert reachability.receiver_compatible
    bad_edge = EdgeWitnessCertificate(
        certificate_id="edge-certificate:bad",
        edge_id="edge:bad",
        source_packet_ids=["missing"],
        target_packet_id="packet:target",
        evidence_refs=[],
    )
    assert not verify_edge_witness_certificate(registry, bad_edge).accepted


def test_ecology_safety_residuals_and_negative_basin_branches() -> None:
    unsafe = CapabilityPacketCandidate(
        packet_id="packet:unsafe-ecology",
        source_ref="unsafe-ecology",
        content_sha256="a" * 64,
        claim="Unsafe ecology packet",
        evidence_refs=["sha256:" + "a" * 64],
        authority_required=True,
        authority_granted=False,
        route_safe=False,
        hazard_charge=0.3,
    )
    registry = build_packet_registry([unsafe], [])
    assert registry.residual_ledger.burden_sum() >= 2.0
    negative_edge = EdgeWitnessCertificate(
        certificate_id="edge-certificate:negative",
        edge_id="edge:negative",
        source_packet_ids=[],
        target_packet_id="missing-target",
        confidence_lower_bound=-1.0,
        false_edge_residual=-1.0,
        expires_at="expired",
    )
    edge_check = verify_edge_witness_certificate(registry, negative_edge)
    assert not edge_check.accepted
    assert "edge certificate is expired" in edge_check.reasons
    basin = CapabilityBasinContract(
        basin_id="negative-basin",
        receiver_family=["missing-receiver"],
        target_basis=["missing-target"],
        required_packet_types=["missing-type"],
        required_edge_types=["missing-edge-type"],
        required_verifier_routes=["missing.route"],
        max_path_cost=-1.0,
    )
    reachability = check_basin_reachability(registry, basin)
    assert not reachability.accepted
    assert reachability.residual_ledger.burden_sum() > registry.residual_ledger.burden_sum()
    assert "required verifier route is missing" in reachability.reasons


def test_sqot_quarantine_downgrades_runtime_operational_use() -> None:
    state = _state()
    bad_packet = CapabilityPacketCandidate(
        packet_id="packet:quarantine",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref="quarantine",
        content_sha256="7" * 64,
        claim="Hash invalid packet should be quarantined.",
        evidence_refs=["sha256:" + "8" * 64],
        receiver_family=["agent"],
        evidence_hash_valid=False,
        rollback_available=False,
        expected_downstream_gain=1.0,
        verification_cost=0.1,
    )
    step_input = RuntimeStepInput(input_id="quarantine-step", packets=[bad_packet])
    report = build_runtime_step(state, step_input, AgentRuntimeConfig(profile="production"))
    assert report.salience_schedule.quarantine_ledger.quarantined_items
    unresolved_ref_report = build_runtime_step(
        state,
        RuntimeStepInput(input_id="unresolved-ref-step", evidence_envelope_refs=["missing.json"]),
        AgentRuntimeConfig(profile="production"),
    )
    assert "one or more evidence envelope refs were unresolved" in unresolved_ref_report.reasons
    assert not report.operationally_usable
    next_state = apply_action_results(state, report, [])
    assert next_state.quarantine_ledger.quarantined_items


def test_action_results_event_log_and_run_comparison_certificate() -> None:
    state = _state()
    report = build_runtime_step(
        state,
        _input_with_evidence(),
        AgentRuntimeConfig(profile="production"),
    )
    result_data = load_data("examples/runtime_action_results.json")["results"][0]
    result = RuntimeActionResult.model_validate(result_data)
    next_state = apply_action_results(state, report, [result])
    assert next_state.event_log.events
    assert next_state.event_log.aggregate_sha256 != state.event_log.aggregate_sha256
    assert next_state.residual_ledger.burden_sum() >= report.residual_ledger.burden_sum()

    candidate_run = build_runtime_run_report(state, [report], run_id="candidate-run")
    baseline_report = report.model_copy(
        update={
            "phase_acceleration_score": report.phase_acceleration_score.model_copy(
                update={"total_score": report.phase_acceleration_score.total_score - 1.0}
            ),
            "residual_ledger": report.residual_ledger.add_coordinate(
                "baseline:extra-debt",
                2.0,
                kind=CoordinateKind.RESIDUAL,
            ),
        }
    )
    baseline_run = build_runtime_run_report(state, [baseline_report], run_id="baseline-run")
    certificate = certify_runtime_acceleration(baseline_run, candidate_run)
    comparison = compare_runtime_runs(baseline_run, candidate_run)
    assert certificate.accepted
    assert comparison.accepted
    assert not certificate.settled

    non_matched = candidate_run.model_copy(update={"resource_units": 2.0})
    assert not certify_runtime_acceleration(baseline_run, non_matched).accepted


def test_action_result_and_acceleration_negative_branches() -> None:
    state = _state()
    report = build_runtime_step(
        state,
        _input_with_evidence(),
        AgentRuntimeConfig(profile="production"),
    )
    resolution = report.evidence_resolution_batch.resolutions[0]
    not_executed = RuntimeActionResult(
        result_id="runtime-action-result-not-executed",
        task_id="task:not-executed",
        executed=False,
        verifier_resolution=resolution,
        residual_ledger=Ledger().add_coordinate(
            "result:not-executed",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        ),
    )
    next_state = apply_action_results(state, report, [not_executed])
    assert next_state.residual_ledger.burden_sum() > report.residual_ledger.burden_sum()

    obstructed_report = report.model_copy(
        update={
            "salience_schedule": report.salience_schedule.model_copy(
                update={
                    "quarantine_ledger": report.salience_schedule.quarantine_ledger.model_copy(
                        update={"quarantined_items": ["packet:bad"]}
                    )
                }
            ),
            "psi": report.psi.model_copy(
                update={
                    "throughput": report.psi.throughput.model_copy(
                        update={
                            "false_liquidity_rate": 0.5,
                            "unresolved_obligation_backlog": 999,
                        }
                    )
                }
            ),
        }
    )
    baseline = build_runtime_run_report(state, [report], run_id="baseline-negative")
    candidate = build_runtime_run_report(state, [obstructed_report], run_id="candidate-negative")
    candidate = candidate.model_copy(
        update={
            "resource_units": 2.0,
            "cumulative_residual_ledger": candidate.cumulative_residual_ledger.add_coordinate(
                "candidate:extra-debt",
                10.0,
                kind=CoordinateKind.RESIDUAL,
            ),
        }
    )
    certificate = certify_runtime_acceleration(baseline, candidate)
    assert not certificate.accepted
    assert "runtime runs are not resource matched" in certificate.reasons
    assert "candidate run is obstructed by SQOT quarantine" in certificate.reasons
    assert "candidate false-liquidity rate exceeds bound" in certificate.reasons
    assert "candidate verifier backlog exceeds bound" in certificate.reasons
    assert "candidate residual debt exceeds baseline" in certificate.reasons


def test_threshold_crossing_and_empty_score_branches() -> None:
    state = _state()
    report = build_runtime_step(
        state,
        _input_with_evidence(),
        AgentRuntimeConfig(profile="production"),
    )
    crossing_run = build_runtime_run_report(
        state,
        [report],
        run_id="crossing-run",
        threshold={"G": 0.0},
    )
    assert crossing_run.threshold_crossing_step == 0
    baseline = RuntimeRunReport(
        run_id="baseline-crossing",
        initial_state_id=state.state_id,
        threshold_crossing_step=3,
        resource_units=1.0,
    )
    candidate = RuntimeRunReport(
        run_id="candidate-crossing",
        initial_state_id=state.state_id,
        threshold_crossing_step=1,
        resource_units=1.0,
    )
    certificate = certify_runtime_acceleration(baseline, candidate)
    assert certificate.hitting_time_gain_lower_bound == 2.0
    assert certificate.accepted


def test_new_schema_and_cli_smoke(tmp_path: Path) -> None:
    for name in [
        "RuntimeActionResult",
        "RuntimeEvent",
        "RuntimeEventLog",
        "RuntimeRunReport",
        "RuntimeComparisonReport",
        "AccelerationCertificate",
        "EvidenceResolutionBatch",
        "VerifiedCapabilityPacket",
        "PacketPromotionPolicy",
        "PacketPromotionReport",
        "PacketRejection",
        "EdgeWitnessCertificate",
        "CapabilityBasinContract",
        "BasinReachabilityReport",
    ]:
        assert schema_by_type(name)["title"] == name

    evidence = runner.invoke(
        app,
        [
            "runtime",
            "resolve-evidence",
            "--input",
            "examples/runtime_step_input_with_evidence.json",
            "--profile",
            "production",
        ],
    )
    assert evidence.exit_code == 0, evidence.output
    assert json.loads(evidence.output)["accepted"]

    report_path = tmp_path / "runtime-report.json"
    step = runner.invoke(
        app,
        [
            "runtime",
            "step",
            "--state",
            "examples/runtime_state.json",
            "--input",
            "examples/runtime_step_input_with_evidence.json",
            "--profile",
            "production",
            "--output",
            str(report_path),
        ],
    )
    assert step.exit_code == 0, step.output
    next_state_path = tmp_path / "next-state.json"
    apply_result = runner.invoke(
        app,
        [
            "runtime",
            "apply-results",
            "--state",
            "examples/runtime_state.json",
            "--report",
            str(report_path),
            "--results",
            "examples/runtime_action_results.json",
            "--output",
            str(next_state_path),
        ],
    )
    assert apply_result.exit_code == 0, apply_result.output
    assert json.loads(next_state_path.read_text(encoding="utf-8"))["event_log"]["events"]

    compare = runner.invoke(
        app,
        [
            "runtime",
            "compare",
            "--baseline",
            "examples/runtime_baseline_run.json",
            "--candidate",
            "examples/runtime_candidate_run.json",
            "--threshold",
            "examples/runtime_threshold.json",
        ],
    )
    assert compare.exit_code == 0, compare.output
    assert json.loads(compare.output)["accepted"]

    cert = runner.invoke(
        app,
        [
            "runtime",
            "certify-acceleration",
            "--baseline",
            "examples/runtime_baseline_run.json",
            "--candidate",
            "examples/runtime_candidate_run.json",
        ],
    )
    assert cert.exit_code == 0, cert.output
    assert json.loads(cert.output)["accepted"]


def test_closed_loop_service_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    fastapi = pytest.importorskip("fastapi")
    _ = fastapi
    from fastapi.testclient import TestClient

    monkeypatch.setenv("PIC_RUNTIME_TOKEN", "runtime-token")
    client = TestClient(create_runtime_app(RuntimeServiceSettings(profile="production")))
    headers = {"Authorization": "Bearer runtime-token"}
    state = load_data("examples/runtime_state.json")
    step_input = load_data("examples/runtime_step_input_with_evidence.json")
    step = client.post(
        "/runtime/step",
        headers=headers,
        json={"state": state, "input": step_input, "config": {"profile": "production"}},
    )
    assert step.status_code == 200
    report = step.json()
    evidence = client.post(
        "/runtime/evidence/resolve",
        headers=headers,
        json={"input": step_input, "profile": "production"},
    )
    assert evidence.status_code == 200
    assert evidence.json()["accepted"]
    applied = client.post(
        "/runtime/result/apply",
        headers=headers,
        json={
            "state": state,
            "report": report,
            "results": load_data("examples/runtime_action_results.json")["results"],
        },
    )
    assert applied.status_code == 200
    assert applied.json()["event_log"]["events"]
    baseline = load_data("examples/runtime_baseline_run.json")
    candidate = load_data("examples/runtime_candidate_run.json")
    comparison = client.post(
        "/runtime/compare",
        headers=headers,
        json={"baseline": baseline, "candidate": candidate},
    )
    assert comparison.status_code == 200
    assert comparison.json()["accepted"]
    certificate = client.post(
        "/runtime/certify-acceleration",
        headers=headers,
        json={"baseline": baseline, "candidate": candidate},
    )
    assert certificate.status_code == 200
    assert certificate.json()["accepted"]
    openapi = client.get("/schemas/openapi.json", headers=headers)
    assert "/runtime/result/apply" in openapi.json()["paths"]
