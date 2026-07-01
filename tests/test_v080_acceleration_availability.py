from __future__ import annotations

from percolation_inversion_compiler.interop import (
    a2a_task_handoff_report,
    bit_mec_frontier_report,
    dynamic_regime_acceleration_report,
    mcp_tool_descriptor_report,
    operation_gate_report,
    phase_acceleration_report,
    sqot_protocol_integrity_report,
    target_validity_check,
    trace_normal_form_report,
)


def _physical_trace() -> dict:
    return trace_normal_form_report(
        {
            "operation_evaluation_clock": "2026-07-01T00:00:00Z",
            "provider_target": "fixture-provider",
            "side_effect_policy": "physical_provider_allowed",
            "trace_id": "trace:v080-physical",
            "steps": [
                {
                    "authority_envelope": {
                        "expires_at": "2099-01-01T00:00:00Z",
                        "issuer": "operator:test",
                        "scopes": [
                            "fixture-provider",
                            "local-test",
                            "environment:local-test",
                        ],
                        "status": "approved",
                    },
                    "causal_schedule_block": {"block_id": "schedule:test"},
                    "certificate_version_refs": ["cert:test:v1"],
                    "evidence_refs": ["evidence:fixture"],
                    "hazard_envelope": {"hazard_refs": ["hazard:test"]},
                    "resource_ledger": {"budget": 1, "units": "fixture"},
                    "rollback_escrow_obligation": {"rollback": "delete fixture output"},
                    "step_id": "s1",
                    "tolerance_ledger": {"observation_error": 0.0},
                    "tool": "fixture-provider",
                    "validity_domain": {"environment": "local-test"},
                }
            ],
        }
    )


def test_physical_gate_requires_accepted_fresh_certificate_status() -> None:
    common_profile = {
        "actuator_class": "fixture_arm",
        "allow_execute": True,
        "allowed_actuator_classes": ["fixture_arm"],
        "explicit_execute": True,
        "observation_window": {"has_verifier": True},
        "physical_dispatch_requested": True,
        "provider_target": "fixture-provider",
        "rollback_escrow": {"status": "verified"},
        "side_effect_policy": "physical_provider_allowed",
        "trusted_issuers": ["operator:test"],
    }
    rejected = operation_gate_report(
        _physical_trace(),
        provider_profile={
            **common_profile,
            "emergency_stop": {"status": "present"},
            "hazard_envelope": {"status": "present"},
            "human_operator_authority": {
                "expires_at": "2099-01-01T00:00:00Z",
                "status": "present",
            },
            "lifecycle_certificate": {"status": "present"},
            "physical_domain_profile": {
                "allowed_actuator_classes": ["fixture_arm"],
                "status": "present",
            },
            "runtime_assurance_certificate": {"status": "present"},
        },
    )
    accepted = operation_gate_report(
        _physical_trace(),
        provider_profile={
            **common_profile,
            "emergency_stop": {"status": "tested"},
            "hazard_envelope": {"expires_at": "2099-01-01T00:00:00Z", "status": "accepted"},
            "human_operator_authority": {
                "expires_at": "2099-01-01T00:00:00Z",
                "status": "approved",
            },
            "lifecycle_certificate": {"status": "fresh"},
            "physical_domain_profile": {
                "allowed_actuator_classes": ["fixture_arm"],
                "status": "accepted",
            },
            "runtime_assurance_certificate": {"status": "fresh"},
        },
    )

    assert rejected["provider_dispatch_ready"] is True
    assert rejected["physical_dispatch_ready"] is False
    assert "physical_profile_not_accepted" in rejected["physical_dispatch_blockers"]
    assert "runtime_assurance_certificate_not_accepted" in rejected["physical_dispatch_blockers"]
    assert accepted["physical_dispatch_ready"] is True
    assert accepted["physical_dispatch_blockers"] == []


def test_mcp_descriptor_rug_pull_and_a2a_handoff_remain_unsettled() -> None:
    descriptor = {
        "auth_scope": ["read"],
        "descriptor_changed_after_approval": True,
        "descriptor_version": "1",
        "egress_policy": "none",
        "server_id": "srv",
        "server_trust_status": "trusted",
        "side_effect_class": "read_only",
        "tool_name": "read",
    }
    mcp = mcp_tool_descriptor_report(descriptor)
    handoff = a2a_task_handoff_report(
        {
            "agent_card_ref": "agent:srv",
            "declared_authority": {"scope": "read"},
            "handoff_scope": "read-only",
            "idempotency_key": "idem-1",
            "replay_nonce": "nonce-1",
            "task_schema": {"type": "object"},
        }
    )

    assert mcp["accepted"] is False
    assert mcp["descriptor_changed_after_approval"] is True
    assert "descriptor_rug_pull_blocked" in mcp["blockers"]
    assert handoff["accepted"] is True
    assert handoff["settled"] is False
    assert "a2a_message_does_not_grant_delegated_tool_execution" in handoff["non_claims"]


def test_phase_acceleration_fails_closed_without_baseline_and_proxy_only_is_non_contributing() -> (
    None
):
    report = phase_acceleration_report(
        {
            "authority_envelope": {"status": "approved"},
            "baseline_upper_envelope_ref": "baseline:missing",
            "capability_basis": ["capability:x"],
            "capability_envelope": {"status": "accepted"},
            "externality_law": {"status": "accepted"},
            "generated_law": {"status": "accepted"},
            "hazard_envelope": {"status": "accepted"},
            "horizon": "P7D",
            "mission_law": {"status": "accepted"},
            "raw_net_capital_floor": 0,
            "target_id": "target:v080",
            "target_set": {"thresholds": {"coord:x": 1}},
            "target_validity_certificate_ref": "tvc:1",
            "viability_set": {"status": "accepted"},
        },
        {},
        [
            {
                "baseline_ref": "baseline:missing",
                "coordinate": "coord:x",
                "finality_ref": "finality:x",
                "finality_valid": True,
                "gauge_compatible": True,
                "hazard_constrained": True,
                "mission_valid": True,
                "raw_net_solvent": True,
                "signed_surplus_lower_bound": 10,
                "transport_ref": "transport:x",
                "transport_valid": True,
                "value_estimand_type": "proxy_only",
            }
        ],
    )

    assert report["certified_acceleration_candidate"] is False
    assert report["ok"] is False
    assert "missing_baseline_policy_class" in report["blockers"]
    assert "proxy_only_non_contributing" in report["blockers"]


def test_target_validity_rejects_unapproved_authority() -> None:
    report = target_validity_check(
        {
            "authority_envelope": {"status": "present"},
            "baseline_upper_envelope_ref": "baseline:demo",
            "capability_basis": ["capability:x"],
            "capability_envelope": {"status": "accepted"},
            "externality_law": {"status": "accepted"},
            "generated_law": {"status": "accepted"},
            "hazard_envelope": {"status": "accepted"},
            "horizon": "P7D",
            "mission_law": {"status": "accepted"},
            "raw_net_capital_floor": 0,
            "target_id": "target:status",
            "target_set": {"thresholds": {"coord:x": 1}},
            "target_validity_certificate_ref": "tvc:1",
            "viability_set": {"status": "accepted"},
        }
    )

    assert report["ok"] is False
    assert report["authority_ok"] is False
    assert "authority_envelope_not_approved" in report["blockers"]


def test_sqot_protocol_mutation_blocks_and_bit_mec_returns_antichain() -> None:
    sqot = sqot_protocol_integrity_report(
        {
            "audit_fuel": 1,
            "checker_thresholds": {"root": 1},
            "diagnostic_reserve": {"min": 1},
            "hidden_protocol_mutation": True,
            "mandatory_obligations": ["root_checker"],
            "mechanism_compatibility_status": "accepted",
            "protocol_id": "sqot:v080",
            "root_checker_integrity": True,
            "semantic_egress_status": "accepted",
        }
    )
    mec = bit_mec_frontier_report(
        [
            {
                "certificate_id": "slow",
                "cost": 2,
                "finite_witness": True,
                "friction": 2,
                "load": 2,
                "unit_ledger": {"unit": "u"},
            },
            {
                "certificate_id": "fast",
                "cost": 1,
                "finite_witness": True,
                "friction": 1,
                "load": 1,
                "unit_ledger": {"unit": "u"},
            },
        ]
    )

    assert sqot["accepted"] is False
    assert "hidden_protocol_mutation" in sqot["blockers"]
    assert [item["certificate_id"] for item in mec["frontier"]] == ["fast"]


def test_dynamic_regime_missing_positivity_floor_blocks_report() -> None:
    report = dynamic_regime_acceleration_report(
        {
            "arrival_gain_lower_bound": 0.5,
            "competing_stop_charge": 0.1,
            "censoring_charge": 0.1,
            "dynamic_baseline_resource_matched": True,
            "surface_id": "surface:v080",
            "truncation_charge": 0.1,
        }
    )

    assert report["accepted"] is False
    assert "positivity_floor_required" in report["blockers"]
    assert report["arrival_gain_lower_bound"] is None
