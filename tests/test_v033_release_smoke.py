from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeRelationVerifierSpec,
    EdgeWitness,
    EdgeWitnessCertificate,
    ExecutionAvailablePathCertificate,
    PacketSourceKind,
    ProtocolFrameDigest,
    check_execution_available_path,
    check_no_hidden_capability_injection,
    edge_certificate_from_witness,
    find_accepted_paths_to_basin,
    verify_edge_relation,
)
from percolation_inversion_compiler.runtime import (
    AgentPolicyIdentity,
    FixedPopulationLedger,
    ResourceMatchedBaselineConfig,
    RuntimeRunReport,
    certify_runtime_acceleration,
    check_fixed_population_ledger,
)

runner = CliRunner()


def test_release_cli_smoke_matrix(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    provenance = tmp_path / "provenance.json"
    sbom = tmp_path / "sbom.json"
    cyclonedx = tmp_path / "cyclonedx.json"
    validate_out = tmp_path / "validate.json"
    step_out = tmp_path / "step.json"
    psi_out = tmp_path / "psi.json"
    openapi = tmp_path / "openapi.json"

    commands = [
        ["--version"],
        ["validate", "--registry", "examples/minimal_registry.json", "--output", str(validate_out)],
        ["schema", "--type", "RuntimeState", "--output", str(tmp_path / "runtime-schema.json")],
        ["schema", "--all", "--output-dir", str(schema_dir)],
        ["snapshot", "list"],
        ["snapshot", "show", "--artifact", "ecpt"],
        ["snapshot", "routes"],
        ["snapshot", "verify", "--artifact", "ecpt"],
        ["routes", "bindings"],
        ["routes", "explain", "--route", "adapters.domain.verify_ecpt_proxy_target_contract"],
        ["sbom", "create", "--format", "pic", "--output", str(sbom)],
        ["sbom", "create", "--format", "cyclonedx", "--output", str(cyclonedx)],
        ["parse", "audit", "--source", "tests/fixtures/minimal_claims.tex", "--strict-grammar"],
        ["ecology", "ingest", "--source", "agent packet", "--kind", "agent-output"],
        [
            "ecology",
            "psi",
            "--registry",
            "examples/collective_packet_registry.json",
            "--output",
            str(psi_out),
        ],
        [
            "ecology",
            "plan",
            "--registry",
            "examples/collective_packet_registry.json",
            "--psi",
            str(psi_out),
        ],
        [
            "runtime",
            "step",
            "--state",
            "examples/runtime_state.json",
            "--input",
            "examples/runtime_step_input.json",
            "--output",
            str(step_out),
        ],
        ["runtime", "health", "--state", "examples/runtime_state.json", "--profile", "production"],
        ["runtime", "export-openapi", "--output", str(openapi)],
        [
            "ecpt",
            "simulate",
            "--state",
            "examples/ecpt_phase_control_state.json",
            "--actions",
            "examples/ecpt_phase_control_actions.json",
        ],
        ["compile", "--records", "examples/minimal_invalid_main_frontier.json"],
        ["demo", "datacenter"],
        ["explain", "ecpt"],
        ["explain", "--from-snapshot", "coverage", "definition:15"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, (command, result.output)

    created = runner.invoke(
        app,
        [
            "provenance",
            "create",
            "--schema-dir",
            str(schema_dir),
            "--sbom-ref",
            str(sbom),
            "--output",
            str(provenance),
        ],
    )
    assert created.exit_code == 0, created.output
    verified = runner.invoke(app, ["provenance", "verify", "--manifest", str(provenance)])
    assert verified.exit_code == 0, verified.output


def test_edge_relation_positive_and_negative_branches() -> None:
    theorem = CapabilityPacketCandidate(
        packet_id="packet:theorem",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref="theorem",
        content_sha256="1" * 64,
        claim="theorem packet",
        receiver_family=["agent"],
        evidence_refs=["sha256:" + "1" * 64],
        expected_downstream_gain=1.0,
        verification_cost=0.1,
        tags=["theorem"],
    )
    code = theorem.model_copy(
        update={
            "packet_id": "packet:code",
            "source_ref": "code",
            "content_sha256": "2" * 64,
            "tags": ["code"],
            "evidence_refs": ["sha256:" + "2" * 64],
        }
    )
    registry = CapabilityPacketRegistry(registry_id="registry:edge", packets=[theorem, code])
    accepted = EdgeWitnessCertificate(
        certificate_id="cert:theorem-code",
        edge_id="edge:theorem-code",
        relation_type="theorem-to-code",
        source_packet_ids=[theorem.packet_id],
        target_packet_id=code.packet_id,
        evidence_refs=["claim:theorem", "code:symbol"],
        confidence_lower_bound=0.8,
        false_edge_residual=0.0,
        accepted=True,
        relation_evidence={
            "theorem_id": "thm:1",
            "code_symbol": "pkg.mod.fn",
            "support_digest": "sha256:" + "3" * 64,
        },
    )
    assert verify_edge_relation(registry, accepted).accepted

    rejected = accepted.model_copy(update={"relation_type": "receiver-compatibility"})
    report = verify_edge_relation(
        registry,
        rejected,
        EdgeRelationVerifierSpec(relation_type="code-to-test"),
    )
    assert not report.accepted
    assert report.residual_ledger.coordinates

    missing_target = accepted.model_copy(update={"target_packet_id": "packet:missing"})
    assert "target packet is absent" in " ".join(
        verify_edge_relation(registry, missing_target).reasons
    )
    no_receiver_target = code.model_copy(update={"receiver_family": ["other"]})
    no_receiver_registry = CapabilityPacketRegistry(
        registry_id="registry:no-receiver",
        packets=[theorem, no_receiver_target],
    )
    no_receiver = accepted.model_copy(update={"relation_type": "receiver-compatibility"})
    no_receiver_report = verify_edge_relation(
        no_receiver_registry,
        no_receiver,
        EdgeRelationVerifierSpec(
            relation_type="receiver-compatibility",
            require_receiver_overlap=True,
        ),
    )
    assert not no_receiver_report.accepted
    needs_resolution = accepted.model_copy(update={"relation_type": "obligation-to-verifier"})
    assert "verifier resolution" in " ".join(
        verify_edge_relation(registry, needs_resolution).reasons
    )

    semantic_edge = EdgeWitness(
        edge_id="edge:semantic",
        source_packet_ids=[theorem.packet_id],
        target_packet_id=code.packet_id,
        edge_type="semantic-dependency",
        accepted=True,
    )
    execution_edge = semantic_edge.model_copy(update={"edge_type": "execution-path"})
    assert edge_certificate_from_witness(semantic_edge).relation_evidence
    assert edge_certificate_from_witness(execution_edge).relation_evidence["not_executed"] == "true"


def test_hidden_injection_and_execution_path_diagnostics() -> None:
    packet = CapabilityPacketCandidate(
        packet_id="packet:hidden",
        source_kind=PacketSourceKind.GITHUB,
        source_ref="hidden",
        content_sha256="4" * 64,
        claim="hidden packet",
        evidence_refs=["http://example.invalid/evidence"],
        verifier_routes=["route:outside"],
    )
    edge = EdgeWitness(
        edge_id="edge:hidden",
        source_packet_ids=["packet:missing"],
        target_packet_id=packet.packet_id,
        accepted=True,
    )
    registry = CapabilityPacketRegistry(
        registry_id="registry:hidden",
        packets=[packet],
        edges=[edge],
    )
    protocol = ProtocolFrameDigest(
        protocol_id="protocol:hidden",
        allowed_source_kinds=["agent-output"],
        allowed_route_ids=["route:inside"],
        allowed_packet_ids=["packet:declared"],
        allowed_evidence_prefixes=["sha256:"],
        sha256="5" * 64,
        accepted=True,
    )
    hidden = check_no_hidden_capability_injection(
        registry,
        protocol,
        runtime_events=[{"event_id": "bad", "event_type": "shell-mutated"}],
    )
    assert not hidden.accepted
    assert hidden.rejected_packet_ids
    assert hidden.rejected_edge_ids
    assert hidden.rejected_event_ids
    assert hidden.rejected_evidence_refs

    path = ExecutionAvailablePathCertificate(
        certificate_id="exec:bad",
        path_id="path:bad",
        packet_ids=[packet.packet_id, "packet:missing"],
        edge_ids=["edge:missing"],
        not_executed=False,
        authority_granted=False,
        rollback_available=False,
    )
    checked = check_execution_available_path(
        path,
        registry,
        constraint_frame={"hard_gates": {"gate": False}},
    )
    joined = " ".join(checked.reasons)
    assert not checked.accepted
    assert "missing packets" in joined
    assert "closed hard gate" in joined

    unsafe_packet = packet.model_copy(
        update={
            "packet_id": "packet:unsafe",
            "authority_required": True,
            "authority_granted": False,
            "rollback_available": False,
            "route_safe": False,
        }
    )
    unsafe_registry = CapabilityPacketRegistry(
        registry_id="registry:unsafe",
        packets=[unsafe_packet],
    )
    unsafe_path = ExecutionAvailablePathCertificate(
        certificate_id="exec:unsafe",
        path_id="path:unsafe",
        packet_ids=[unsafe_packet.packet_id],
        edge_ids=[],
        not_executed=True,
        execution_gates=["ExecGate"],
        authority_granted=True,
        rollback_available=True,
        receiver_context=["agent"],
        evidence_refs=["sha256:" + "4" * 64],
    )
    unsafe_checked = check_execution_available_path(unsafe_path, unsafe_registry)
    unsafe_reasons = " ".join(unsafe_checked.reasons)
    assert "required authority" in unsafe_reasons
    assert "rollback support" in unsafe_reasons
    assert "route is unsafe" in unsafe_reasons


def test_path_reachability_and_baseline_config_negative_branches() -> None:
    source = CapabilityPacketCandidate(
        packet_id="packet:path-source",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref="source",
        content_sha256="7" * 64,
        claim="source",
        receiver_family=["agent"],
        evidence_refs=["sha256:" + "7" * 64],
        tags=["source"],
        verifier_routes=["route:source"],
        verification_cost=1.0,
    )
    target = source.model_copy(
        update={
            "packet_id": "packet:path-target",
            "source_ref": "target",
            "content_sha256": "8" * 64,
            "receiver_family": ["other"],
            "tags": ["target"],
            "verifier_routes": [],
            "verification_cost": 2.0,
        }
    )
    edge = EdgeWitness(
        edge_id="edge:path",
        source_packet_ids=[source.packet_id],
        target_packet_id=target.packet_id,
        edge_type="semantic-dependency",
        confidence=0.1,
        accepted=True,
    )
    registry = CapabilityPacketRegistry(
        registry_id="registry:path",
        packets=[source, target],
        edges=[edge],
    )
    basin = {
        "basin_id": "basin:path",
        "receiver_family": ["agent"],
        "target_basis": ["packet:path-target"],
        "required_packet_types": ["missing-type"],
        "required_verifier_routes": ["route:missing"],
        "max_path_cost": 0.1,
    }
    paths = find_accepted_paths_to_basin(
        registry,
        CapabilityBasinContract.model_validate(basin),
    )
    assert not paths

    base = RuntimeRunReport(
        run_id="baseline:left-config",
        initial_state_id="state",
        baseline_config=ResourceMatchedBaselineConfig(),
    )
    candidate = RuntimeRunReport(run_id="candidate:no-config", initial_state_id="state")
    cert = certify_runtime_acceleration(base, candidate)
    assert not cert.resource_matched

    drift = check_fixed_population_ledger(
        FixedPopulationLedger(
            ledger_id="fixed:drift",
            before_agents=[
                AgentPolicyIdentity(
                    agent_id="agent:same",
                    policy_digest="policy:a",
                    model_digest="model:a",
                )
            ],
            after_agents=[
                AgentPolicyIdentity(
                    agent_id="agent:same",
                    policy_digest="policy:b",
                    model_digest="model:b",
                )
            ],
        )
    )
    drift_reasons = " ".join(drift.reasons)
    assert "policy digest changed" in drift_reasons
    assert "model digest changed" in drift_reasons


def test_cli_bad_parameter_branches(tmp_path: Path) -> None:
    bad_object = tmp_path / "bad.json"
    bad_object.write_text("[]", encoding="utf-8")
    bad_routes = tmp_path / "bad-routes.json"
    bad_routes.write_text('{"requests":{}}', encoding="utf-8")
    bad_events = tmp_path / "bad-events.json"
    bad_events.write_text('{"events":{}}', encoding="utf-8")
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(ProtocolFrameDigest(protocol_id="p", sha256="6" * 64).model_dump(mode="json")),
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    registry.write_text('{"registry_id":"r","packets":[],"edges":[]}', encoding="utf-8")
    checks = [
        [
            "runtime",
            "step",
            "--state",
            str(bad_object),
            "--input",
            "examples/runtime_step_input.json",
        ],
        [
            "runtime",
            "execute-routes",
            "--requests",
            str(bad_routes),
            "--evidence-store",
            str(tmp_path),
        ],
        [
            "ecology",
            "hidden-injection-check",
            "--registry",
            str(registry),
            "--events",
            str(bad_events),
            "--protocol",
            str(protocol),
        ],
        ["routes", "explain", "--route", "missing.route"],
        ["snapshot", "show", "--artifact", "missing"],
        ["schema", "--type", "MissingType"],
        ["sbom", "create", "--format", "missing"],
    ]
    for command in checks:
        result = runner.invoke(app, command)
        assert result.exit_code != 0, command
