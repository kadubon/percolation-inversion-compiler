from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.afst import (
    AFSTProfilePolicy,
    AuthorityEnvelope,
    BoundedFrictionHandover,
    BufferComponent,
    CandidateFlux,
    ConsentChannel,
    RefusalChannel,
    ResourceBalanceWitness,
    SatisfactionCoordinate,
    SatisfactionDeficit,
    SatisfactionEffectWitness,
    ShockEnvelope,
    StabilizationBuffer,
    UnitFrame,
    afst_profile_policy,
    audit_afst_raw_input,
    build_afst_flux_stabilization_report,
    check_authority_envelope,
    check_bounded_friction_handover,
    check_consent_channel,
    check_non_market_liquidity,
    check_refusal_channel,
    check_resource_balance,
    check_stabilization_buffer,
    compute_certified_abundance,
    compute_satisfaction_deficit,
    unit_compatible,
)
from percolation_inversion_compiler.afst.records import CertifiedAbundanceCoordinate
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.interop import afst_ccr_tasks_from_report
from percolation_inversion_compiler.io.schema import load_data, schema_by_type

runner = CliRunner()
AFST_EXAMPLES = Path("examples") / "afst"


def _example(name: str) -> dict[str, object]:
    return load_data(AFST_EXAMPLES / name)


def test_minimal_afst_case_is_accepted_but_never_dispatch_ready() -> None:
    report = build_afst_flux_stabilization_report(_example("minimal_accepted.json"))

    assert report.accepted is True
    assert report.flux_admissible is True
    assert report.settled is False
    assert report.operation_ready is False
    assert report.provider_dispatch_ready is False
    assert report.physical_dispatch_ready is False
    assert report.status == "provisional"
    assert "not_execution_authority" in report.non_claims


def test_compute_certified_abundance_subtracts_all_residuals() -> None:
    abundance = compute_certified_abundance(
        CertifiedAbundanceCoordinate(
            abundance_id="a",
            cell_id="source",
            resource_type="compute",
            available_amount=20.0,
            safe_floor=5.0,
            reserve_amount=2.0,
            legal_hold_amount=1.0,
            spoilage_upper_bound=1.0,
            transfer_loss_upper_bound=1.0,
            observation_residual=2.0,
            lifecycle_residual=1.0,
            other_hard_residual=1.0,
            unit="gpu-hour",
            authority_refs=["auth"],
            evidence_refs=["evidence"],
        )
    )

    assert abundance.certified_amount == 6.0
    assert abundance.accepted is True


def test_blocked_examples_preserve_blocking_residuals() -> None:
    expected = {
        "blocked_refusal.json": "refusal_active",
        "blocked_buffer.json": "buffer_insufficient",
        "blocked_authority.json": "authority_status_not_active",
        "blocked_unit_mismatch.json": "unit_mismatch",
        "blocked_balance.json": "resource_balance_violation",
        "blocked_missing_shock.json": "missing_shock_envelope",
    }

    for filename, blocker in expected.items():
        report = build_afst_flux_stabilization_report(_example(filename))
        assert report.accepted is False
        assert blocker in report.blockers
        assert any(item["kind"] == blocker for item in report.residuals)


def test_active_refusal_blocks_even_when_abundance_is_large() -> None:
    data = copy.deepcopy(_example("minimal_accepted.json"))
    abundance = data["abundance_coordinates"][0]  # type: ignore[index]
    abundance["available_amount"] = 1000.0  # type: ignore[index]
    refusal = data["refusal_channels"][0]  # type: ignore[index]
    refusal["active_refusal"] = True  # type: ignore[index]

    report = build_afst_flux_stabilization_report(data)

    assert report.accepted is False
    assert report.status == "rejected"
    assert "refusal_active" in report.blockers


def test_missing_refusal_and_consent_channels_block_production() -> None:
    data = copy.deepcopy(_example("minimal_accepted.json"))
    data.pop("refusal_channels")
    data.pop("consent_channels")

    report = build_afst_flux_stabilization_report(data, profile="production")

    assert report.accepted is False
    assert "missing_refusal_channels" in report.blockers
    assert "missing_consent_channels" in report.blockers


def test_missing_shock_is_not_treated_as_zero() -> None:
    report = build_afst_flux_stabilization_report(_example("blocked_missing_shock.json"))

    assert report.accepted is False
    assert "missing_shock_envelope" in report.blockers
    buffer = report.stabilization_buffers[0]
    assert buffer.available_buffer == 6.0
    assert buffer.required_buffer == 0.0
    assert buffer.accepted is False


def test_required_record_fields_are_residuals_not_defaults() -> None:
    data = copy.deepcopy(_example("minimal_accepted.json"))
    del data["satisfaction_coordinates"][0]["value"]  # type: ignore[index]
    del data["refusal_channels"][0]["active_refusal"]  # type: ignore[index]
    del data["refusal_channels"][0]["legal_hold"]  # type: ignore[index]
    del data["stabilization_buffers"][0]["shock_envelope"]["panic_load"]  # type: ignore[index]

    report = build_afst_flux_stabilization_report(data)
    residual_kinds = {str(item["kind"]) for item in report.residuals}

    assert report.accepted is False
    assert "missing_satisfaction_coordinate_value" in report.blockers
    assert "missing_refusal_channel_active_refusal" in report.blockers
    assert "missing_refusal_channel_legal_hold" in report.blockers
    assert "missing_shock_envelope_panic_load" in report.blockers
    assert {
        "missing_satisfaction_coordinate_value",
        "missing_refusal_channel_active_refusal",
        "missing_refusal_channel_legal_hold",
        "missing_shock_envelope_panic_load",
    }.issubset(residual_kinds)


def test_afst_report_sorts_unordered_arrays_and_residuals() -> None:
    data = copy.deepcopy(_example("minimal_accepted.json"))
    first_buffer = copy.deepcopy(data["stabilization_buffers"][0])  # type: ignore[index]
    first_buffer["buffer_id"] = "buffer:aaa"  # type: ignore[index]
    first_handover = copy.deepcopy(data["handover_protocols"][0])  # type: ignore[index]
    first_handover["handover_id"] = "handover:aaa"  # type: ignore[index]
    data["stabilization_buffers"] = [data["stabilization_buffers"][0], first_buffer]  # type: ignore[index]
    data["handover_protocols"] = [data["handover_protocols"][0], first_handover]  # type: ignore[index]

    report = build_afst_flux_stabilization_report(data)
    residuals = report.residuals

    assert [item.buffer_id for item in report.stabilization_buffers] == [
        "buffer:aaa",
        "buffer:research-compute",
    ]
    assert [item.handover_id for item in report.handover_protocols] == [
        "handover:aaa",
        "handover:compute-scheduler",
    ]
    assert residuals == sorted(
        residuals,
        key=lambda item: (
            str(item.get("kind") or ""),
            str(item.get("object_id") or ""),
            str(item.get("residual_id") or ""),
        ),
    )


def test_resource_balance_violation_blocks() -> None:
    witness = check_resource_balance(
        ResourceBalanceWitness(
            witness_id="balance",
            flux_id="flux",
            source_debit=3.0,
            target_credit=4.0,
            loss_upper_bound=0.5,
            conversion_factor=1.0,
            conservation_residual=0.0,
        )
    )

    assert witness.accepted is False
    assert "resource_balance_violation" in witness.reasons


def test_low_level_afst_audits_and_numeric_guards_preserve_residuals() -> None:
    audit = audit_afst_raw_input({"unknown_path": []}, afst_profile_policy("production"))
    assert audit.accepted is False
    assert "unknown_top_level_paths_preserved" in audit.reasons
    assert "satisfaction_coordinates" in audit.missing_required_paths

    assert (
        unit_compatible(
            UnitFrame(resource_type="compute", unit="gpu-hour"),
            UnitFrame(resource_type="memory", unit="gpu-hour"),
        )
        is False
    )

    deficit = compute_satisfaction_deficit(
        SatisfactionCoordinate(
            value=float("inf"),
            floor_critical=5.0,
            floor_min=4.0,
            floor_safe=3.0,
        )
    )
    assert "nonfinite_numeric_field" in deficit.reasons
    assert "satisfaction_floor_order_violation" in deficit.reasons
    assert "missing_satisfaction_coordinate_id" in deficit.reasons

    abundance = compute_certified_abundance(
        CertifiedAbundanceCoordinate(available_amount=1.0, safe_floor=2.0)
    )
    assert abundance.accepted is False
    assert "missing_authority_ref" in abundance.reasons
    assert "certified_abundance_nonpositive" in abundance.reasons


def test_afst_gate_checkers_reject_expired_invalid_and_covert_inputs() -> None:
    reference_time = datetime(2026, 1, 1, tzinfo=UTC)
    authority = check_authority_envelope(
        AuthorityEnvelope(
            status="revoked",
            action="transfer",
            resource_type="memory",
            expires_at="2000-01-01T00:00:00Z",
            fixture_only=True,
        ),
        required_scope={"source", "target", "compute", "allocate"},
        required_resource_type="compute",
        required_action="allocate",
        reference_time=reference_time,
        dry_run=False,
    )
    assert {
        "authority_status_not_active",
        "authority_resource_mismatch",
        "authority_action_mismatch",
        "authority_scope_mismatch",
        "authority_expired",
        "fixture_only_authority_non_executable",
        "missing_authority_envelope",
    }.issubset(set(authority.reasons))

    flux = CandidateFlux(
        flux_id="flux",
        target_cell_id="target",
        resource_type="compute",
        unit="gpu-hour",
    )
    consent = check_consent_channel(
        ConsentChannel(
            consent_granted=False,
            resource_type="memory",
            action="send",
            expires_at="2000-01-01T00:00:00Z",
        ),
        flux=flux,
        reference_time=reference_time,
    )
    assert {
        "consent_not_granted",
        "consent_resource_mismatch",
        "consent_scope_mismatch",
        "consent_action_mismatch",
        "consent_expired",
        "missing_consent_channel",
    }.issubset(set(consent.reasons))

    refusal = check_refusal_channel(
        RefusalChannel(active_refusal=True, legal_hold=True, observed_signal=2.0)
    )
    assert {
        "refusal_channel_missing",
        "refusal_active",
        "legal_hold_present",
        "refusal_stop_threshold_crossed",
    }.issubset(set(refusal.reasons))

    handover = check_bounded_friction_handover(
        BoundedFrictionHandover(
            mode="automation",
            covert_transition=True,
            irreversible_transition=True,
            skill_debt_upper_bound=2.0,
            skill_debt_budget=1.0,
            settled=True,
        )
    )
    assert handover.settled is False
    assert {
        "handover_authority_invalid",
        "handover_telemetry_stale",
        "handover_rollback_missing",
        "handover_override_missing",
        "handover_explanation_channel_missing",
        "handover_covert_transition",
        "handover_irreversible_transition",
        "handover_skill_debt_unbounded",
        "handover_no_shadow_or_dual_run",
        "handover_settlement_blocked",
    }.issubset(set(handover.reasons))


def test_afst_buffer_and_liquidity_negative_paths_are_explicit() -> None:
    buffer = check_stabilization_buffer(
        StabilizationBuffer(
            resource_type="compute",
            unit="gpu-hour",
            components=[
                BufferComponent(
                    component_id="bad",
                    amount=-1.0,
                    resource_type="memory",
                    unit="gb",
                )
            ],
            shock_envelope=ShockEnvelope(
                resource_type="memory",
                unit="gb",
                shock_upper_bound=-1.0,
            ),
        )
    )
    assert buffer.accepted is False
    assert {
        "buffer_unit_mismatch",
        "buffer_negative_component",
        "shock_negative_component",
    }.issubset(set(buffer.reasons))

    certificate = check_non_market_liquidity(
        CertifiedAbundanceCoordinate(
            abundance_id="abundance",
            cell_id="source",
            resource_type="compute",
            certified_amount=0.0,
            unit="gpu-hour",
        ),
        SatisfactionDeficit(
            deficit_id="deficit",
            coordinate_id="psi",
            cell_id="target",
            resource_type="compute",
            amount=0.0,
            unit="gpu-hour",
        ),
        CandidateFlux(
            flux_id="flux",
            source_cell_id="source",
            target_cell_id="target",
            resource_type="compute",
            amount=0.0,
            unit="gpu-hour",
            latency=-1.0,
            loss_upper_bound=-1.0,
            transfer_residual=-1.0,
            conversion_factor=0.0,
            liquidity_mode="market_signal_only",
        ),
        policy=AFSTProfilePolicy(
            require_authority=True,
            require_consent_channel=True,
            require_refusal_channel=True,
            require_balance_witness=True,
            require_lifecycle_freshness=True,
        ),
        effect_witnesses=[
            SatisfactionEffectWitness(
                witness_id="effect",
                flux_id="flux",
                predicted_delta=0.0,
            )
        ],
    )
    assert certificate.accepted is False
    assert {
        "flux_amount_nonpositive",
        "flux_conversion_nonpositive",
        "negative_numeric_field",
        "source_floor_violation",
        "certified_abundance_nonpositive",
        "target_deficit_not_positive",
        "target_deficit_not_reduced",
        "price_only_signal",
        "missing_authority_envelope",
        "missing_consent_channel",
        "refusal_channel_missing",
        "physical_balance_unknown",
        "lifecycle_stale",
    }.issubset(set(certificate.reasons))


def test_report_preserves_missing_abundance_and_deficit_as_blockers() -> None:
    missing_abundance = copy.deepcopy(_example("minimal_accepted.json"))
    missing_abundance["candidate_fluxes"][0]["source_cell_id"] = "missing-source"  # type: ignore[index]
    abundance_report = build_afst_flux_stabilization_report(missing_abundance)
    assert "missing_certified_abundance" in abundance_report.blockers

    missing_deficit = copy.deepcopy(_example("minimal_accepted.json"))
    missing_deficit["candidate_fluxes"][0]["target_cell_id"] = "missing-target"  # type: ignore[index]
    deficit_report = build_afst_flux_stabilization_report(missing_deficit)
    assert "missing_target_deficit" in deficit_report.blockers


def test_schema_export_includes_afst_report() -> None:
    schema = schema_by_type("AFSTFluxStabilizationReport")

    assert schema["title"] == "AFSTFluxStabilizationReport"
    assert "operation_ready" in schema["properties"]


def test_afst_ccr_tasks_from_report_are_deterministic_and_non_executing() -> None:
    report = build_afst_flux_stabilization_report(_example("blocked_authority.json"))
    first = afst_ccr_tasks_from_report(report.model_dump(mode="json"))
    second = afst_ccr_tasks_from_report(report.model_dump(mode="json"))

    assert first == second
    assert first
    assert first[0]["constraints"]["authority_policy"] == "read_only"
    assert any(task["extensions"]["x_pic_task_kind"] == "afst_authority_repair" for task in first)


def test_cli_afst_check_and_emit_ccr_tasks(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "afst",
            "check",
            "--case",
            str(AFST_EXAMPLES / "minimal_accepted.json"),
            "--compact",
        ],
    )
    assert result.exit_code == 0
    compact = json.loads(result.output)
    assert compact["accepted"] is True
    assert compact["settled"] is False
    assert compact["ok"] is True

    report_path = tmp_path / "afst-report.json"
    report_result = runner.invoke(
        app,
        [
            "afst",
            "check",
            "--case",
            str(AFST_EXAMPLES / "blocked_refusal.json"),
            "--output",
            str(report_path),
        ],
    )
    assert report_result.exit_code == 0
    task_result = runner.invoke(
        app,
        ["afst", "emit-ccr-tasks", "--report", str(report_path)],
    )
    assert task_result.exit_code == 0
    assert "afst_refusal_channel_repair" in task_result.output


def test_cli_afst_isolated_debug_commands() -> None:
    handover = runner.invoke(
        app,
        ["afst", "handover", "--handover", str(AFST_EXAMPLES / "handover_minimal.json")],
    )
    assert handover.exit_code == 0
    assert json.loads(handover.output)["accepted"] is True

    balance = runner.invoke(
        app,
        ["afst", "balance", "--witness", str(AFST_EXAMPLES / "balance_witness.json")],
    )
    assert balance.exit_code == 0
    assert json.loads(balance.output)["accepted"] is True


def test_afst_public_boundary_rejects_coercion_and_invalid_time() -> None:
    numeric_string = copy.deepcopy(_example("minimal_accepted.json"))
    numeric_string["candidate_fluxes"][0]["amount"] = "1.0"  # type: ignore[index]
    numeric_report = build_afst_flux_stabilization_report(numeric_string)
    assert "invalid_candidate_flux_amount" in numeric_report.blockers

    string_boolean = copy.deepcopy(_example("minimal_accepted.json"))
    string_boolean["refusal_channels"][0]["active_refusal"] = "false"  # type: ignore[index]
    boolean_report = build_afst_flux_stabilization_report(string_boolean)
    assert "invalid_refusal_channel_active_refusal" in boolean_report.blockers

    invalid_time = copy.deepcopy(_example("minimal_accepted.json"))
    invalid_time["reference_time"] = "not-a-time"
    invalid_time_report = build_afst_flux_stabilization_report(invalid_time)
    assert "invalid_reference_time" in invalid_time_report.blockers


def test_afst_report_checks_authority_expiry_against_reference_time() -> None:
    data = copy.deepcopy(_example("minimal_accepted.json"))
    data["reference_time"] = "2026-07-10T00:00:00Z"
    data["authority_envelopes"][0]["expires_at"] = "2026-07-09T23:59:59Z"  # type: ignore[index]
    report = build_afst_flux_stabilization_report(data)
    assert not report.accepted
    assert "authority_expired" in report.blockers
