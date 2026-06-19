from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.alt import (
    ALTAccelerationCertificate,
    ALTAdmissionAction,
    ALTCARACertificate,
    ALTKernelTransitionReport,
    BaselineRefreshCertificate,
    ExecutableALTCertificatePacket,
    FoundryBottleneck,
    FoundryState,
    HazardEnvelopeCertificate,
    LiquidityCertificate,
    NegativeLiquidityCertificate,
    OpportunityMeasureContract,
    ProblemSolvingTrace,
    ReproductionMatrixCertificate,
    RootFinalityCertificate,
    TelemetryCostCertificate,
    admit_alt_packet,
    build_abstraction_token_from_packet,
    build_abstraction_token_from_trace,
    check_alt_acceleration_certificate,
    check_alt_cara_certificate,
    check_alt_kernel_transition,
    check_baseline_refresh_certificate,
    check_hazard_envelope_certificate,
    check_liquidity_certificate,
    check_negative_liquidity_certificate,
    check_opportunity_measure_contract,
    check_root_finality_certificate,
    check_telemetry_cost_certificate,
    check_token_admissibility,
    compute_alt_reproduction_report,
    compute_foundry_dashboard,
    deprecate_alt_packet,
    recommend_foundry_actions,
    resurrect_alt_candidate,
)
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitnessCertificate,
    PacketSourceKind,
    build_packet_registry,
    build_psi_dashboard,
    verify_edge_relation,
)
from percolation_inversion_compiler.io import audit_theory_source, schema_by_type
from percolation_inversion_compiler.io.schema import load_data
from percolation_inversion_compiler.io.snapshots import load_theory_snapshot
from percolation_inversion_compiler.io.tex import strict_tex_parse_report

runner = CliRunner()


def test_alt_token_admissibility_requires_operational_fields() -> None:
    trace = ProblemSolvingTrace.model_validate(load_data("examples/alt/trace.json"))
    token = build_abstraction_token_from_trace(
        trace,
        {
            "authority_refs": ["authority:example"],
            "capability_envelope_refs": ["capability-envelope:example"],
            "interface_refs": ["schema:GeneralIntakeReport"],
            "verifier_routes": ["alt.adapters.transport.verify_density_ratio_support"],
        },
    )
    result = check_token_admissibility(token)
    assert result.accepted
    assert not result.settled

    rejected = check_token_admissibility(
        token.model_copy(update={"authority_refs": [], "capability_envelope_refs": []})
    )
    assert not rejected.accepted
    assert "authority-refs" in rejected.missing_obligations
    assert "capability-envelope-refs" in rejected.missing_obligations


def test_alt_liquidity_certificate_accepts_only_positive_certified_surplus() -> None:
    certificate = LiquidityCertificate.model_validate(
        load_data("examples/alt/liquidity_certificate.json")
    )
    checked = check_liquidity_certificate(certificate)
    assert checked.accepted
    assert checked.value_evidence_level == "calibrated-proxy"
    assert checked.proxy_bridge_refs
    assert checked.value_bridge_report.accepted
    assert checked.value_bridge_report.calibrated_proxy_bridge_ready
    assert checked.value_bridge_report.common_estimand_ready
    assert checked.signed_surplus_lower_bound > 0.0
    assert checked.operationally_usable
    assert not checked.settled

    proxy_only = certificate.model_copy(update={"value_evidence_level": "proxy-only"})
    proxy_only_report = check_liquidity_certificate(proxy_only)
    assert not proxy_only_report.accepted
    assert "proxy-only evidence cannot certify reusable abstraction capital" in (
        proxy_only_report.reasons
    )
    assert proxy_only_report.value_bridge_report.proxy_only
    assert "proxy-only evidence cannot certify reusable abstraction capital" in (
        proxy_only_report.value_bridge_report.reasons
    )

    causal_without_evidence = certificate.model_copy(
        update={"value_evidence_level": "causal", "causal_effect_refs": []}
    )
    causal_report = check_liquidity_certificate(causal_without_evidence)
    assert not causal_report.accepted
    assert "causal value evidence requires causal_effect_refs" in causal_report.reasons
    assert not causal_report.value_bridge_report.causal_effect_ready

    negative = LiquidityCertificate.model_validate(
        load_data("examples/alt/negative_hazard_token.json")
    )
    rejected = check_liquidity_certificate(negative)
    assert not rejected.accepted
    assert not rejected.operationally_usable
    assert not rejected.settled
    assert any("surplus" in reason for reason in rejected.reasons)


def test_alt_new_certificate_guards_fail_closed() -> None:
    opportunity = OpportunityMeasureContract(
        contract_id="alt-opportunity:bad",
        mission_id="mission:demo",
    )
    opportunity_report = check_opportunity_measure_contract(opportunity)
    assert not opportunity_report.accepted
    assert "opportunity receiver_family is required" in opportunity_report.reasons
    assert "baseline_ref is required" in opportunity_report.reasons

    root = RootFinalityCertificate(
        certificate_id="alt-root:bad",
        token_id="alt-token:trace:alt-example",
        root_role_refs=["root:same", "root:same"],
        byzantine_budget_upper_bound=2.0,
        correlated_capture_budget_upper_bound=2.0,
        partition_alarm=True,
    )
    root_report = check_root_finality_certificate(root)
    assert not root_report.accepted
    joined_root = " ".join(root_report.reasons)
    assert "root roles must be distinct" in joined_root
    assert "finality partition alarm is active" in joined_root

    telemetry = TelemetryCostCertificate.model_validate(
        load_data("examples/alt/telemetry_failure_certificate.json")
    )
    telemetry_report = check_telemetry_cost_certificate(telemetry)
    assert not telemetry_report.accepted
    assert "tamper-positive" in " ".join(telemetry_report.reasons)

    hazard = HazardEnvelopeCertificate.model_validate(
        load_data("examples/alt/hazard_overflow_certificate.json")
    )
    hazard_report = check_hazard_envelope_certificate(hazard)
    assert not hazard_report.accepted
    assert "noncompensable hazard" in " ".join(hazard_report.reasons)
    assert "risk exceeds" in " ".join(hazard_report.reasons)

    baseline = BaselineRefreshCertificate(
        certificate_id="alt-baseline-refresh:bad",
        old_baseline_ref="baseline:same",
        new_baseline_ref="baseline:same",
    )
    baseline_report = check_baseline_refresh_certificate(baseline)
    assert not baseline_report.accepted
    assert "baseline refresh must change" in " ".join(baseline_report.reasons)


def test_alt_acceleration_and_kernel_transitions_fail_closed() -> None:
    acceleration = ALTAccelerationCertificate(
        certificate_id="alt-acceleration:bad",
        baseline_foundry_id="foundry:baseline",
        candidate_foundry_id="foundry:candidate",
        residual_external_obligations=["external-causal-effect"],
    )
    acceleration_report = check_alt_acceleration_certificate(acceleration)
    assert not acceleration_report.accepted
    assert "not positive" in " ".join(acceleration_report.reasons)
    assert "external acceleration obligation remains" in " ".join(acceleration_report.reasons)

    stagnant = ALTKernelTransitionReport(
        report_id="alt-kernel:bad",
        prior_state_id="kernel:1",
        next_state_id="kernel:1",
        action=ALTAdmissionAction.DEPRECATE,
    )
    stagnant_report = check_alt_kernel_transition(stagnant)
    assert not stagnant_report.accepted
    assert "distinct state id" in " ".join(stagnant_report.reasons)
    assert "deprecation/rollback transition requires" in " ".join(stagnant_report.reasons)

    missing_resurrection = ALTKernelTransitionReport(
        report_id="alt-kernel:resurrection-bad",
        prior_state_id="kernel:1",
        next_state_id="kernel:2",
        action=ALTAdmissionAction.RESURRECT_AS_CANDIDATE,
    )
    missing_resurrection_report = check_alt_kernel_transition(missing_resurrection)
    assert not missing_resurrection_report.accepted
    assert "resurrection transition requires" in " ".join(missing_resurrection_report.reasons)


def test_alt_negative_deprecation_and_resurrection_paths() -> None:
    negative = NegativeLiquidityCertificate.model_validate(
        load_data("examples/alt/negative_liquidity_certificate.json")
    )
    checked = check_negative_liquidity_certificate(negative)
    assert checked.accepted
    assert not checked.settled

    deprecation = deprecate_alt_packet(
        "alt-token:trace:alt-example",
        checked,
        rollback_refs=["rollback:example"],
        lineage_refs=["lineage:alt-token:trace:alt-example"],
    )
    assert deprecation.accepted
    assert not deprecation.settled

    packet = ExecutableALTCertificatePacket.model_validate(
        load_data("examples/alt/admission_packet.json")
    )
    resurrection = resurrect_alt_candidate(
        deprecation,
        packet,
        override_failure_mode="hazard-overflow",
        evidence_refs=["resurrection:evidence:example"],
    )
    assert resurrection.accepted
    assert resurrection.operationally_usable is False
    assert not resurrection.settled


def test_alt_admission_packet_is_protocol_relative_not_settled() -> None:
    packet = ExecutableALTCertificatePacket.model_validate(
        load_data("examples/alt/admission_packet.json")
    )
    result = runner.invoke(app, ["alt", "admit", "--packet", "examples/alt/admission_packet.json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"]
    assert data["action"] == "admit"
    assert data["settled"] is False
    assert data["certified_capital_ref"]
    assert packet.token.candidate_only


def test_alt_admission_defers_unresolved_external_obligations() -> None:
    packet = ExecutableALTCertificatePacket.model_validate(
        load_data("examples/alt/admission_packet.json")
    )
    assert packet.liquidity_certificate is not None
    unresolved = packet.liquidity_certificate.model_copy(
        update={"residual_external_obligations": ["alt.adapters.causal.verify_token_effect"]}
    )
    decision = admit_alt_packet(packet.model_copy(update={"liquidity_certificate": unresolved}))
    assert not decision.accepted
    assert decision.action == "defer"
    assert not decision.settled
    assert "liquidity certificate retains residual external obligations" in decision.reasons


def test_alt_cara_and_reproduction_preserve_protocol_relative_scope() -> None:
    reproduction = ReproductionMatrixCertificate.model_validate(
        load_data("examples/alt/reproduction_certificate.json")
    )
    reproduction_report = compute_alt_reproduction_report(reproduction)
    assert reproduction_report.accepted
    assert not reproduction_report.settled

    cara = ALTCARACertificate.model_validate(load_data("examples/alt/alt_cara_certificate.json"))
    report = check_alt_cara_certificate(cara)
    assert report.accepted
    assert report.operationally_usable
    assert not report.settled

    unresolved = cara.model_copy(update={"residual_external_obligations": ["oracle-target"]})
    unresolved_report = check_alt_cara_certificate(unresolved)
    assert not unresolved_report.accepted
    assert not unresolved_report.settled


def test_alt_foundry_actions_explain_bottlenecks() -> None:
    state = FoundryState(
        foundry_id="foundry:blocked",
        evidence_backlog=2,
        transport_backlog=1,
        risk_backlog=1,
        receiver_absorption_capacity=0.0,
        settlement_capacity=0.0,
    )
    dashboard = compute_foundry_dashboard(state)
    actions = recommend_foundry_actions(dashboard)
    assert not dashboard.accepted
    assert FoundryBottleneck.EVIDENCE_LIMITED in dashboard.bottlenecks
    assert FoundryBottleneck.TRANSPORT_LIMITED in dashboard.bottlenecks
    assert FoundryBottleneck.RISK_LIMITED in dashboard.bottlenecks
    assert FoundryBottleneck.CAPACITY_LIMITED in dashboard.bottlenecks
    assert "suspend-risky-token-admission" in actions
    assert "increase-receiver-absorption-or-settlement-capacity" in actions
    assert "collect-transport-support-and-density-ratio-evidence" in actions
    assert "route-candidates-to-trace-mission-telemetry-verifiers" in actions
    assert "form-certified-abstraction-capital-before-phase-claims" in actions


def test_alt_external_candidate_does_not_improve_psi() -> None:
    raw = CapabilityPacketCandidate(
        packet_id="packet:external-alt",
        source_kind=PacketSourceKind.WEB_PAGE,
        source_ref="https://example.invalid/alt",
        content_sha256="0" * 64,
        claim="External ALT candidate with no certificate",
        receiver_family=["agent"],
        evidence_refs=["sha256:" + "0" * 64],
        expected_downstream_gain=100.0,
        verification_cost=0.0,
        tags=["external-candidate", "alt", "liquidity"],
        verifier_routes=["alt.adapters.transport.verify_density_ratio_support"],
    )
    token = build_abstraction_token_from_packet(raw)
    assert token.candidate_only
    registry = build_packet_registry([raw], registry_id="registry:alt-external")
    psi = build_psi_dashboard(registry)
    assert psi.components["G"] == 0.0
    assert psi.components["SD"] == 0.0
    assert psi.components["BR"] == 0.0
    assert psi.components["AC"] == 0.0
    assert not psi.safety_invariants[1].startswith("dashboard output proves")
    assert (
        psi.residual_ledger.value("psi:registry:alt-external:external-candidate-volume-excluded")
        == 1.0
    )


def test_liquidity_transfer_edge_requires_alt_certificate_evidence() -> None:
    source = CapabilityPacketCandidate(
        packet_id="packet:alt-source",
        source_kind=PacketSourceKind.LOCAL,
        source_ref="sha256:" + "1" * 64,
        content_sha256="1" * 64,
        claim="ALT source capital",
        receiver_family=["agent"],
        tags=["alt", "capital"],
    )
    target = source.model_copy(
        update={
            "packet_id": "packet:alt-target",
            "content_sha256": "2" * 64,
            "claim": "ALT target capital",
        }
    )
    registry = CapabilityPacketRegistry(
        registry_id="registry:alt-liquidity-edge",
        packets=[source, target],
    )
    weak = EdgeWitnessCertificate(
        certificate_id="edge-cert:weak-liquidity",
        edge_id="edge:weak-liquidity",
        relation_type="liquidity-transfer",
        source_packet_ids=[source.packet_id],
        target_packet_id=target.packet_id,
        evidence_refs=["liquidity:tag-only"],
        confidence_lower_bound=0.8,
        false_edge_residual=0.0,
        accepted=True,
        relation_evidence={
            "source_liquidity": "source",
            "target_liquidity": "target",
        },
    )
    assert not verify_edge_relation(registry, weak).accepted

    certified = weak.model_copy(
        update={
            "certificate_id": "edge-cert:alt-liquidity",
            "evidence_refs": [
                "alt-liquidity:cert",
                "transport:cert",
                "root:quorum",
                "finality:record",
            ],
            "relation_evidence": {
                "alt_liquidity_certificate_id": "alt-liquidity:cert",
                "transport_certificate_id": "transport:cert",
                "root_of_trust_ref": "root:quorum",
                "finality_record_ref": "finality:record",
                "residual_policy": "charge-until-alt-certificate-remains-valid",
            },
        }
    )
    assert verify_edge_relation(registry, certified).accepted


def test_alt_snapshot_and_strict_parse_when_present() -> None:
    snapshot = load_theory_snapshot("alt")
    assert snapshot.definitions == 159
    assert snapshot.claims == 197
    assert snapshot.coverage_counts["unsupported"] == 0
    assert snapshot.external_obligation_category_summary["alt-transport"] >= 1

    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    source = Path(canonical_dir) / "Abstraction Liquidity Theory.tex"
    grammar = strict_tex_parse_report(source)
    assert grammar.accepted
    audit = audit_theory_source(source, canonical_key="alt")
    assert audit.coverage.definitions == snapshot.definitions
    assert audit.coverage.claims == snapshot.claims
    assert audit.snapshot_delta["coverage_counts_match"]


def test_alt_cli_and_schema_smoke() -> None:
    for type_name in [
        "AbstractionToken",
        "LiquidityCertificate",
        "FoundryControlDashboard",
        "ALTCARACertificate",
        "NegativeLiquidityCertificate",
        "ALTDeprecationRecord",
        "ALTResurrectionRecord",
        "BaselineRefreshCertificate",
        "OpportunityMeasureContract",
        "RootFinalityCertificate",
        "TelemetryCostCertificate",
        "HazardEnvelopeCertificate",
        "ReproductionMatrixCertificate",
        "ALTKernelTransitionReport",
    ]:
        schema = schema_by_type(type_name)
        assert schema["title"] == type_name

    commands = [
        ["alt", "tokenize", "--trace", "examples/alt/trace.json"],
        ["alt", "check-token", "--token", "examples/alt/token_candidate.json"],
        [
            "alt",
            "certify-liquidity",
            "--certificate",
            "examples/alt/liquidity_certificate.json",
        ],
        [
            "alt",
            "negative-certify",
            "--certificate",
            "examples/alt/negative_liquidity_certificate.json",
        ],
        [
            "alt",
            "deprecate",
            "--token-id",
            "alt-token:trace:alt-example",
            "--certificate",
            "examples/alt/negative_liquidity_certificate.json",
            "--rollback-ref",
            "rollback:example",
        ],
        [
            "alt",
            "resurrect",
            "--deprecation",
            "examples/alt/deprecation_record.json",
            "--packet",
            "examples/alt/admission_packet.json",
            "--override-failure-mode",
            "hazard-overflow",
            "--evidence-ref",
            "resurrection:evidence:example",
        ],
        [
            "alt",
            "refresh-baseline",
            "--certificate",
            "examples/alt/baseline_refresh_certificate.json",
        ],
        [
            "alt",
            "reproduction-report",
            "--certificate",
            "examples/alt/reproduction_certificate.json",
        ],
        [
            "alt",
            "check-cara",
            "--certificate",
            "examples/alt/alt_cara_certificate.json",
        ],
        ["alt", "foundry-dashboard", "--state", "examples/alt/foundry_state.json"],
        [
            "alt",
            "bridge-runtime",
            "--report",
            "examples/alt/runtime_bridge_report.json",
            "--state",
            "examples/runtime_state.json",
        ],
        ["snapshot", "show", "--artifact", "alt"],
        ["snapshot", "verify", "--artifact", "alt"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
