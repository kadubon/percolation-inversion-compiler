"""Deterministic CCR interop reports.

The helpers in this module are data-only adapters.  They emit candidate tasks,
residuals, trace normal forms, and registry rows for CCR without granting
execution authority or changing PIC's checker/runtime boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from percolation_inversion_compiler.acceleration.records import (
    BottleneckCandidate,
    PhaseAccelerationPlan,
)
from percolation_inversion_compiler.io.tex import extract_mr_records

FIXED_CREATED_AT = "1970-01-01T00:00:00Z"
NON_CLAIMS = [
    "not_real_asi_proof",
    "not_model_weight_update",
    "not_execution_authority",
]
CCR_TASK_KINDS = {
    "packet_repair",
    "verifier_route",
    "alt_capital_check",
    "sqot_queue_repair",
    "trc_trace_normalization",
    "bit_witness_completion",
    "baseline_refresh",
    "identity_context_repair",
    "transport_certificate_repair",
    "hazard_envelope_repair",
    "residual_ledger_repair",
}
_MR_LITERAL_RE = re.compile(r"MRRecord\|([^|\s]+)\|([^|\s]+)\|?(.*)$")
_VALID_MR_TYPES = {
    "article",
    "artifact",
    "unit-ledger",
    "schema",
    "claim",
    "witness",
    "depends",
    "citation",
}


def jsonl_text(items: Iterable[Mapping[str, Any]]) -> str:
    """Serialize deterministic JSONL."""

    return (
        "\n".join(
            json.dumps(item, sort_keys=True, separators=(",", ":"), default=str) for item in items
        )
        + "\n"
    )


def ccr_tasks_from_phase_plan(plan: PhaseAccelerationPlan) -> list[dict[str, Any]]:
    """Emit deterministic CCR task objects from a phase plan."""

    tasks: list[dict[str, Any]] = []
    for bottleneck in plan.bottlenecks:
        kind = _task_kind_for_bottleneck(bottleneck)
        tasks.append(
            _ccr_task(
                kind=kind,
                title=f"PIC {kind.replace('_', ' ')}",
                objective=_bottleneck_objective(bottleneck),
                source_id=bottleneck.candidate_id,
                profile=plan.profile,
                priority=_priority(bottleneck.priority_score),
                role=_role_for_task_kind(kind),
                inputs=[
                    _input_ref(
                        ref=bottleneck.candidate_id,
                        kind="report",
                        notes=(
                            "PIC bottleneck candidate; candidate-only until CCR work verifies it."
                        ),
                    ),
                    *[
                        _input_ref(ref=reason, kind="text", notes="Cannot-promote reason.")
                        for reason in bottleneck.cannot_promote_because
                    ],
                ],
                safe_command_hints=bottleneck.next_safe_commands,
                residual_inputs=bottleneck.residual_coordinates,
                verifier_routes=bottleneck.next_verifier_routes,
                candidate_only=bottleneck.candidate_only,
            )
        )
    for index, reason in enumerate(plan.candidate_only_reasons):
        tasks.append(
            _ccr_task(
                kind="packet_repair",
                title="Preserve PIC candidate-only reason",
                objective=f"Repair or route candidate-only PIC input: {reason}",
                source_id=f"{plan.plan_id}:candidate-only:{index}",
                profile=plan.profile,
                priority=45,
                role="skeptic",
                inputs=[_input_ref(ref=reason, kind="text", notes="Candidate-only reason.")],
                candidate_only=True,
            )
        )
    for index, blocker in enumerate(plan.settled_blockers):
        tasks.append(
            _ccr_task(
                kind="residual_ledger_repair",
                title="Repair PIC settlement blocker",
                objective=f"Preserve and route PIC settlement blocker: {blocker}",
                source_id=f"{plan.plan_id}:settled-blocker:{index}",
                profile=plan.profile,
                priority=80,
                role="integrator",
                inputs=[
                    _input_ref(
                        ref=blocker,
                        kind="text",
                        notes="Blocking settlement residual.",
                    )
                ],
                residual_inputs=[blocker],
            )
        )
    for index, command in enumerate(plan.safe_commands):
        tasks.append(
            _ccr_task(
                kind="verifier_route",
                title="Review PIC safe command hint",
                objective="Review a PIC safe command as a non-executed hint.",
                source_id=f"{plan.plan_id}:safe-command:{index}",
                profile=plan.profile,
                priority=30,
                role="pic_adapter",
                inputs=[_input_ref(ref=command, kind="text", notes="Safe command hint only.")],
                safe_command_hints=[command],
                candidate_only=True,
            )
        )
    return sorted(tasks, key=lambda item: item["task_id"])


def ccr_residuals_from_phase_plan(plan: PhaseAccelerationPlan) -> list[dict[str, Any]]:
    """Emit deterministic CCR residual objects from phase plan blockers."""

    residuals: list[dict[str, Any]] = []
    for index, blocker in enumerate(plan.settled_blockers):
        residuals.append(
            _ccr_residual(
                kind="settlement_blocker",
                description=f"PIC settled blocker: {blocker}",
                blocking=True,
                object_type="phase",
                object_id=plan.plan_id,
                source_id=f"{plan.plan_id}:settled-blocker:{index}",
                source_field="settled_blockers",
            )
        )
    for index, reason in enumerate(plan.candidate_only_reasons):
        residuals.append(
            _ccr_residual(
                kind="candidate_only_reason",
                description=f"PIC candidate-only reason: {reason}",
                blocking=False,
                object_type="phase",
                object_id=plan.plan_id,
                source_id=f"{plan.plan_id}:candidate-only:{index}",
                source_field="candidate_only_reasons",
            )
        )
    for index, obligation in enumerate(plan.missing_obligations):
        residuals.append(
            _ccr_residual(
                kind="settlement_blocker",
                description=f"PIC missing obligation: {obligation}",
                blocking=True,
                object_type="phase",
                object_id=plan.plan_id,
                source_id=f"{plan.plan_id}:missing-obligation:{index}",
                source_field="missing_obligations",
            )
        )
    return sorted(residuals, key=lambda item: item["residual_id"])


def alt_ecpt_bridge_report(
    packet: Mapping[str, Any],
    *,
    profile: str = "development",
) -> dict[str, Any]:
    """Build a conservative ALT-to-ECPT bridge report from a packet-like object."""

    packet_id = _packet_id(packet)
    liquidity = _mapping(packet.get("liquidity_certificate"))
    token = _mapping(packet.get("token"))
    negative = _mapping(packet.get("negative_liquidity_certificate"))
    residuals: list[dict[str, Any]] = []
    candidate_only_reasons: list[str] = []
    settled_blockers: list[str] = []

    if not liquidity:
        residuals.append(_bridge_residual(packet_id, "missing_liquidity_certificate", True))
        settled_blockers.append("missing liquidity certificate")
    if not _has_cost_upper_bounds(packet, liquidity):
        residuals.append(_bridge_residual(packet_id, "missing_cost_upper_bounds", True))
        settled_blockers.append("missing cost upper bounds")
    transport_scope = _transport_scope(packet, liquidity)
    if not transport_scope:
        residuals.append(_bridge_residual(packet_id, "missing_transport_scope", True))
        settled_blockers.append("missing transport scope")
    if not _has_baseline(packet, liquidity):
        residuals.append(_bridge_residual(packet_id, "missing_baseline", True))
        settled_blockers.append("missing baseline")
    hazard = _list_field(packet, "hazard_envelope") or _list_field(
        _mapping(liquidity.get("hazard_envelope_certificate")), "hazard_refs"
    )
    if not hazard:
        residuals.append(_bridge_residual(packet_id, "missing_hazard_envelope", True))
        settled_blockers.append("missing hazard envelope")
    receiver = _list_field(packet, "receiver_family") or _list_field(token, "receiver_family")
    if not receiver:
        residuals.append(_bridge_residual(packet_id, "missing_receiver_admissibility", True))
        settled_blockers.append("missing receiver admissibility")

    value_level = str(
        liquidity.get("value_evidence_level")
        or packet.get("value_evidence_level")
        or _mapping(liquidity.get("value_bridge_report")).get("value_evidence_level")
        or "candidate"
    ).lower()
    proxy_only = value_level == "proxy-only" or bool(
        _mapping(liquidity.get("value_bridge_report")).get("proxy_only", False)
    )
    if proxy_only:
        candidate_only_reasons.append("proxy-only value evidence cannot increase safe capital")
        residuals.append(_bridge_residual(packet_id, "proxy_only_value_evidence", False))

    negative_signal = bool(negative) or "negative" in str(packet.get("alt_status", "")).lower()
    if negative_signal:
        residuals.append(_bridge_residual(packet_id, "negative_liquidity_preserved", True))
        settled_blockers.append("negative liquidity signal preserved")

    accepted = bool(packet)
    surplus_lower = _float_value(
        liquidity.get("signed_surplus_lower_bound"),
        liquidity.get("downstream_search_cost_reduction_lower_bound"),
        packet.get("signed_surplus_lower_bound"),
    )
    surplus_upper = _float_value(
        liquidity.get("signed_surplus_upper_bound"),
        liquidity.get("downstream_search_cost_reduction_upper_bound"),
        packet.get("signed_surplus_upper_bound"),
        surplus_lower,
    )
    capital_blockers = sorted(
        set(settled_blockers)
        | set(candidate_only_reasons)
        | (
            {"nonpositive_signed_surplus_lower_bound"}
            if liquidity and not negative_signal and surplus_lower <= 0.0
            else set()
        )
    )
    capital_admitted = accepted and not capital_blockers and surplus_lower > 0.0
    status = (
        "negative_liquidity"
        if negative_signal
        else "capital_admitted"
        if capital_admitted
        else "candidate"
    )
    if not liquidity and not packet:
        status = "diagnostic"
    return {
        "accepted": accepted,
        "alt_status": status,
        "capital_admission_blockers": capital_blockers,
        "capital_admitted": capital_admitted,
        "candidate_only_reasons": sorted(set(candidate_only_reasons)),
        "ecpt_contribution": {
            "hazard_envelope": sorted(set(hazard)),
            "liquidity_debt": [item["kind"] for item in residuals],
            "liquidity_lower_bound": surplus_lower if capital_admitted else None,
            "phase_components": {
                "alt_bridge_candidate": bool(packet_id),
                "receiver_scope_present": bool(receiver),
                "transport_scope_present": bool(transport_scope),
            },
            "receiver_admissibility": sorted(set(receiver)),
            "settlement_latency": None,
            "transport_scope": sorted(set(transport_scope)),
        },
        "non_claims": list(NON_CLAIMS),
        "ok": True,
        "packet_id": packet_id,
        "profile": profile,
        "residuals": residuals,
        "schema_version": "pic.alt_ecpt_bridge.v1",
        "settled": False,
        "settled_blockers": sorted(set(settled_blockers)),
        "signed_surplus_lower_bound": surplus_lower,
        "signed_surplus_upper_bound": surplus_upper,
    }


def diagnose_sqot_queue_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Diagnose SQOT queue/reserve state without treating missing data as zero."""

    reserve_available = _optional_float(
        _deep_get(state, "diagnostic_reserve.available"),
        _deep_get(state, "diagnostic_reserve_available"),
        _deep_get(state, "reserve_available"),
    )
    reserve_min = _optional_float(
        _deep_get(state, "diagnostic_reserve.required_min"),
        _deep_get(state, "diagnostic_reserve_required"),
        _deep_get(state, "required_min"),
    )
    reserve_max = _optional_float(
        _deep_get(state, "diagnostic_reserve.required_max"),
        _deep_get(state, "required_max"),
    )
    inflow = _optional_float(
        _deep_get(state, "verifier_capacity.inflow"),
        _deep_get(state, "queue.inflow"),
        _deep_get(state, "inflow"),
    )
    service = _optional_float(
        _deep_get(state, "verifier_capacity.service"),
        _deep_get(state, "queue.service"),
        _deep_get(state, "service"),
    )
    meta_score = _optional_float(
        _deep_get(state, "meta_occupation.score"),
        _deep_get(state, "meta_occupation"),
    )
    quarantine_load = _optional_float(
        _deep_get(state, "quarantine.load"),
        _deep_get(state, "quarantine_load"),
    )
    residuals: list[dict[str, Any]] = []
    blocking: list[str] = []

    reserve_status = "unknown"
    if reserve_available is None or reserve_min is None:
        residuals.append(_sqot_residual("missing_diagnostic_reserve", True))
        blocking.append("missing diagnostic reserve data")
    elif reserve_available < reserve_min:
        reserve_status = "below_band"
        residuals.append(_sqot_residual("diagnostic_reserve_below_band", True))
        blocking.append("diagnostic reserve below required band")
    elif reserve_max is not None and reserve_available > reserve_max:
        reserve_status = "above_band"
        residuals.append(_sqot_residual("diagnostic_reserve_above_band", False))
    else:
        reserve_status = "within_band"

    capacity_ratio = None
    capacity_status = "unknown"
    if inflow is None or service is None:
        residuals.append(_sqot_residual("missing_verifier_capacity", True))
        blocking.append("missing verifier capacity data")
    elif service <= 0:
        capacity_ratio = None
        capacity_status = "inadequate"
        residuals.append(_sqot_residual("verifier_service_nonpositive", True))
        blocking.append("verifier service capacity is nonpositive")
    else:
        capacity_ratio = inflow / service
        capacity_status = "adequate" if capacity_ratio <= 1.0 else "inadequate"
        if capacity_ratio > 1.0:
            residuals.append(_sqot_residual("verifier_queue_overloaded", True))
            blocking.append("verifier queue inflow exceeds service")

    meta_status = "unknown"
    if meta_score is None:
        residuals.append(_sqot_residual("missing_meta_occupation", False))
    else:
        meta_status = "over_band" if meta_score > 1.0 else "within_band"
        if meta_score > 1.0:
            residuals.append(_sqot_residual("meta_occupation_over_band", True))
            blocking.append("meta occupation is over band")
    quarantine_status = "unknown"
    if quarantine_load is not None:
        quarantine_status = "overloaded" if quarantine_load > 1.0 else "within_band"
        if quarantine_load > 1.0:
            residuals.append(_sqot_residual("quarantine_overloaded", True))
            blocking.append("quarantine overloaded")

    scalar_only = any(key in state for key in ("queue_score", "score")) and (
        reserve_available is None or inflow is None or service is None
    )
    if scalar_only:
        residuals.append(_sqot_residual("scalar_queue_score_incomplete", True))
        blocking.append("single scalar queue score omits mandatory SQOT coordinates")

    queue_status = "ok"
    if capacity_status == "inadequate":
        queue_status = "overloaded"
    elif reserve_status in {"below_band", "above_band"}:
        queue_status = "reserve_low" if reserve_status == "below_band" else "diagnostic"
    elif meta_status == "over_band":
        queue_status = "meta_occupied"
    elif quarantine_status == "overloaded":
        queue_status = "quarantine_overloaded"
    elif residuals:
        queue_status = "diagnostic"

    tasks: list[dict[str, Any]] = []
    if any(
        item["kind"] in {"verifier_queue_overloaded", "missing_verifier_capacity"}
        for item in residuals
    ):
        tasks.append(
            _ccr_task(
                kind="verifier_route",
                title="Repair verifier queue route",
                objective=(
                    "Route verifier capacity diagnostics without treating unknown budget as zero."
                ),
                source_id="sqot:verifier-capacity",
                profile="development",
                priority=75,
                role="scheduler",
                residual_inputs=[item["kind"] for item in residuals],
            )
        )
    if residuals:
        tasks.append(
            _ccr_task(
                kind="sqot_queue_repair",
                title="Repair SQOT queue ledger",
                objective=(
                    "Supply missing SQOT queue, reserve, meta-occupation, and quarantine ledgers."
                ),
                source_id="sqot:queue-report",
                profile="development",
                priority=70,
                role="scheduler",
                residual_inputs=[item["kind"] for item in residuals],
            )
        )

    return {
        "blocking_residuals": sorted(set(blocking)),
        "diagnostic_reserve": {
            "available": reserve_available,
            "required_max": reserve_max,
            "required_min": reserve_min,
            "status": reserve_status,
        },
        "meta_occupation": {"score": meta_score, "status": meta_status},
        "ok": True,
        "queue_status": queue_status,
        "repair_tasks": tasks,
        "residuals": residuals,
        "schema_version": "pic.sqot_queue_report.v1",
        "verifier_capacity": {
            "capacity_ratio": capacity_ratio,
            "inflow": inflow,
            "service": service,
            "status": capacity_status,
        },
    }


def trace_normal_form_report(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an agent trace into a finite practical TRC TraceNF subset."""

    raw_steps = _trace_steps(trace)
    steps: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    trace_id = str(trace.get("trace_id") or trace.get("id") or "agent-trace")
    for index, raw in enumerate(raw_steps):
        step_id = str(raw.get("step_id") or raw.get("event_id") or f"step:{index}")
        action_type = str(
            raw.get("action_type") or raw.get("action_kind") or raw.get("type") or "tool-call"
        )
        tool_call = str(
            raw.get("tool_call") or raw.get("tool_name") or raw.get("tool") or raw.get("name") or ""
        )
        step_residuals: list[dict[str, Any]] = []
        if not raw.get("witness") and not raw.get("evidence_refs") and not raw.get("output_ref"):
            step_residuals.append(_trace_residual(trace_id, step_id, "missing_step_witness", False))
        if not raw.get("authority_envelope") and not raw.get("authority_status"):
            step_residuals.append(
                _trace_residual(trace_id, step_id, "missing_authority_envelope", True)
            )
        if not raw.get("rollback_escrow_obligation") and not raw.get("rollback_status"):
            step_residuals.append(
                _trace_residual(
                    trace_id,
                    step_id,
                    "missing_rollback_escrow_obligation",
                    False,
                )
            )
        if not raw.get("resource_use") and not raw.get("resource_ledger"):
            step_residuals.append(
                _trace_residual(trace_id, step_id, "missing_resource_ledger", False)
            )
        if not raw.get("tolerance_ledger") and not raw.get("tolerance_budget"):
            step_residuals.append(
                _trace_residual(trace_id, step_id, "missing_tolerance_ledger", False)
            )
        residuals.extend(step_residuals)
        steps.append(
            {
                "action_type": action_type,
                "actuator_class": raw.get("actuator_class"),
                "authority_envelope": raw.get("authority_envelope")
                or {"status": str(raw.get("authority_status", "missing"))},
                "emergency_stop": raw.get("emergency_stop"),
                "hazard_envelope": raw.get("hazard_envelope")
                or raw.get("hazard_envelope_certificate"),
                "human_operator_authority": raw.get("human_operator_authority"),
                "causal_schedule_block": raw.get("causal_schedule_block"),
                "certificate_version_refs": _list_field(raw, "certificate_version_refs"),
                "clock_cell": raw.get("clock_cell"),
                "input_ref": str(
                    raw.get("input_ref") or _digest(raw.get("input", raw.get("arguments", {})))
                ),
                "output_ref": str(
                    raw.get("output_ref") or _digest(raw.get("output", raw.get("result", {})))
                ),
                "observation_window": raw.get("observation_window"),
                "physical_domain_profile": raw.get("physical_domain_profile"),
                "postcondition": raw.get("postcondition", {}),
                "precondition": raw.get("precondition", {}),
                "provider_target": raw.get("provider_target"),
                "runtime_assurance_certificate": raw.get("runtime_assurance_certificate")
                or raw.get("shield_certificate"),
                "residuals": step_residuals,
                "resource_use": raw.get("resource_use") or raw.get("resource_ledger") or None,
                "rollback_escrow_obligation": raw.get("rollback_escrow_obligation")
                or {"status": str(raw.get("rollback_status", "missing"))},
                "side_effect_policy": raw.get("side_effect_policy"),
                "step_id": step_id,
                "tolerance_ledger": raw.get("tolerance_ledger")
                or raw.get("tolerance_budget")
                or None,
                "tool_call": tool_call,
                "validity_domain": raw.get("validity_domain"),
            }
        )
    return {
        "accepted": bool(steps),
        "finite": True,
        "non_claims": list(NON_CLAIMS),
        "ok": True,
        "residuals": residuals,
        "schema_version": "pic.trc_trace_nf.v1",
        "settled": False,
        "trace_id": trace_id,
        "trc_trace_nf": {
            "evaluation_clock": trace.get("evaluation_clock")
            or trace.get("operation_evaluation_clock")
            or trace.get("reference_time"),
            "fixture_mode": bool(trace.get("fixture_mode", False)),
            "provider_target": trace.get("provider_target"),
            "side_effect_policy": trace.get("side_effect_policy"),
            "steps": steps,
            "validity_domain": trace.get("validity_domain"),
        },
    }


_ACTIVE_AUTHORITY_STATUSES = {"active", "approved"}
_CORE_OPERATION_BLOCKERS = {
    "authority_issuer_untrusted",
    "authority_scope_mismatch",
    "authority_status_not_active",
    "authority_time_unknown",
    "expired_authority_envelope",
    "fixture_only_authority_non_executable",
    "missing_authority_envelope",
    "missing_resource_ledger",
    "missing_rollback_escrow_obligation",
    "missing_steps",
    "missing_step_witness",
    "missing_tolerance_ledger",
}
_AUTHORITY_RESIDUAL_KINDS = {
    "authority_issuer_untrusted",
    "authority_scope_mismatch",
    "authority_status_not_active",
    "authority_time_unknown",
    "expired_authority_envelope",
    "fixture_only_authority_non_executable",
    "missing_authority_envelope",
}
_OPERATION_GATE_KINDS = {
    "capability_gate": {"missing_step_witness", "missing_steps"},
    "resource_gate": {"missing_resource_ledger"},
    "rollback_gate": {"missing_rollback_escrow_obligation"},
    "tolerance_gate": {"missing_tolerance_ledger"},
}
_PHYSICAL_PROFILE_FIELDS = {
    "actuator_class": "physical actuator class",
    "emergency_stop": "emergency stop or abort route",
    "hazard_envelope": "hazard envelope",
    "human_operator_authority": "human/operator authority",
    "observation_window": "observation window",
    "physical_domain_profile": "physical domain profile",
    "rollback_escrow": "rollback/escrow",
    "runtime_assurance_certificate": "runtime assurance or shield certificate",
}


def _context_value(
    trace_nf: Mapping[str, Any],
    nf: Mapping[str, Any],
    provider_profile: Mapping[str, Any],
    *keys: str,
) -> Any:
    for key in keys:
        value = provider_profile.get(key)
        if value not in (None, ""):
            return value
    for key in keys:
        value = nf.get(key)
        if value not in (None, ""):
            return value
    for key in keys:
        value = trace_nf.get(key)
        if value not in (None, ""):
            return value
    return None


def _bool_context(
    trace_nf: Mapping[str, Any],
    nf: Mapping[str, Any],
    provider_profile: Mapping[str, Any],
    *keys: str,
) -> bool:
    value = _context_value(trace_nf, nf, provider_profile, *keys)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "fixture", "fixture-only"}


def _side_effect_policy(
    trace_nf: Mapping[str, Any],
    nf: Mapping[str, Any],
    provider_profile: Mapping[str, Any],
) -> str:
    return str(
        _context_value(
            trace_nf,
            nf,
            provider_profile,
            "side_effect_policy",
            "default_side_effect_policy",
        )
        or "none_without_execute_flag"
    )


def _parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _status(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("status", "")).strip().lower()
    return str(value or "").strip().lower()


def _status_ok(value: Any, allowed: set[str]) -> bool:
    return _status(value) in allowed


def _fresh_until(value: Mapping[str, Any], reference: datetime | None) -> bool:
    if reference is None:
        return False
    expires_at = value.get("expires_at") or value.get("fresh_until")
    parsed = _parse_time(expires_at)
    return parsed is not None and parsed > reference


def _certificate_fresh(value: Any, reference: datetime | None) -> bool:
    cert = _mapping(value)
    status = _status(cert)
    if status in {"fresh", "recomputed"}:
        return True
    if status not in {"accepted", "approved", "available", "tested", "verified", "active"}:
        return False
    return _fresh_until(cert, reference) or bool(cert.get("fresh") is True)


def _reference_time(
    trace_nf: Mapping[str, Any],
    nf: Mapping[str, Any],
    provider_profile: Mapping[str, Any],
) -> datetime | None:
    for value in (
        _context_value(
            trace_nf,
            nf,
            provider_profile,
            "operation_evaluation_clock",
            "evaluation_clock",
            "reference_time",
            "checked_at",
        ),
        _deep_get(nf, "clock_cell.evaluation_time"),
        _deep_get(nf, "clock_cell.reference_time"),
    ):
        parsed = _parse_time(value)
        if parsed is not None:
            return parsed
    for step in [item for item in nf.get("steps", []) if isinstance(item, Mapping)]:
        clock_cell = _mapping(step.get("clock_cell"))
        for key in ("operation_evaluation_clock", "evaluation_time", "reference_time", "wall_time"):
            parsed = _parse_time(clock_cell.get(key))
            if parsed is not None:
                return parsed
    return None


def _scope_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if value in (None, ""):
        return tokens
    if isinstance(value, Mapping):
        for key, item in value.items():
            if item in (None, ""):
                continue
            tokens.add(str(item))
            tokens.add(f"{key}:{item}")
    elif isinstance(value, list | tuple | set):
        for item in value:
            tokens.update(_scope_tokens(item))
    else:
        tokens.add(str(value))
    return {token.strip().lower() for token in tokens if token.strip()}


def _authority_scope_tokens(authority: Mapping[str, Any]) -> set[str]:
    tokens = set()
    for key in (
        "scope",
        "scopes",
        "validity_domain",
        "validity_domains",
        "provider_target",
        "provider_targets",
        "provider",
        "providers",
    ):
        tokens.update(_scope_tokens(authority.get(key)))
    return tokens


def _scope_matches(authority: Mapping[str, Any], required: set[str]) -> bool:
    if not required:
        return True
    authority_tokens = _authority_scope_tokens(authority)
    if "*" in authority_tokens:
        return True
    return required.issubset(authority_tokens)


def _gate(ok: bool, residuals: Sequence[Mapping[str, Any]], *, note: str = "") -> dict[str, Any]:
    return {
        "ok": ok,
        "note": note,
        "residual_kinds": sorted({str(item.get("kind")) for item in residuals if item.get("kind")}),
    }


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _report_hash(report: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = report.get(key)
        if value not in (None, ""):
            return str(value)
    return _digest(report)


def _structured_report_accepted(report: Mapping[str, Any], ready_keys: set[str]) -> bool:
    if not report:
        return False
    if report.get("ok") is True or report.get("accepted") is True:
        return True
    if any(report.get(key) is True for key in ready_keys):
        return True
    return _status_ok(report, {"accepted", "approved", "valid", "ready", "fresh"})


def _gate_blocker(
    trace_id: str,
    step_id: str,
    kind: str,
    blockers: list[str],
    residuals: list[dict[str, Any]],
) -> None:
    blockers.append(kind)
    residuals.append(_trace_residual(trace_id, step_id, kind, True))


def _mcp_tool_gate_report(
    trace_id: str,
    provider_profile: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    descriptor = _mapping(provider_profile.get("mcp_tool_descriptor_report"))
    preflight = _mapping(provider_profile.get("mcp_tool_invocation_preflight"))
    structured_present = bool(descriptor or preflight)
    required = bool(provider_profile.get("requires_mcp_tool") or structured_present)
    legacy_present = "mcp_tool_gate_accepted" in provider_profile
    legacy_accepted = bool(provider_profile.get("mcp_tool_gate_accepted"))
    blockers: list[str] = []
    residuals: list[dict[str, Any]] = []
    descriptor_hash = (
        _report_hash(descriptor, "descriptor_hash", "tool_descriptor_hash", "hash")
        if descriptor
        else None
    )
    invocation_descriptor_hash = None
    if preflight:
        nested_descriptor = _mapping(preflight.get("descriptor_report"))
        invocation_descriptor_hash = (
            str(
                _first_value(
                    preflight.get("descriptor_hash"),
                    preflight.get("tool_descriptor_hash"),
                    preflight.get("descriptor_report_hash"),
                    nested_descriptor.get("descriptor_hash"),
                    nested_descriptor.get("tool_descriptor_hash"),
                )
                or ""
            )
            or None
        )
    if structured_present:
        if not descriptor:
            _gate_blocker(
                trace_id,
                "mcp-tool-gate",
                "mcp_tool_descriptor_report_required",
                blockers,
                residuals,
            )
        elif not _structured_report_accepted(descriptor, {"descriptor_ready", "tool_ready"}):
            _gate_blocker(
                trace_id,
                "mcp-tool-gate",
                "mcp_tool_descriptor_report_not_accepted",
                blockers,
                residuals,
            )
        if not preflight:
            _gate_blocker(
                trace_id,
                "mcp-tool-gate",
                "mcp_tool_invocation_preflight_required",
                blockers,
                residuals,
            )
        elif not _structured_report_accepted(
            preflight,
            {"invocation_ready", "preflight_ready", "dispatch_ready"},
        ):
            _gate_blocker(
                trace_id,
                "mcp-tool-gate",
                "mcp_tool_invocation_preflight_not_accepted",
                blockers,
                residuals,
            )
        if (
            descriptor_hash
            and invocation_descriptor_hash
            and descriptor_hash != invocation_descriptor_hash
        ):
            _gate_blocker(
                trace_id,
                "mcp-tool-gate",
                "mcp_descriptor_invocation_hash_mismatch",
                blockers,
                residuals,
            )
        structured_ok = not blockers
    else:
        structured_ok = False
        if required and not legacy_accepted:
            _gate_blocker(
                trace_id,
                "mcp-tool-gate",
                "mcp_tool_gate_not_accepted",
                blockers,
                residuals,
            )
    if structured_present and legacy_present and structured_ok != legacy_accepted:
        _gate_blocker(
            trace_id,
            "mcp-tool-gate",
            "mcp_gate_structured_legacy_mismatch",
            blockers,
            residuals,
        )
    ok = (structured_ok if structured_present else (not required or legacy_accepted)) and not any(
        item.get("kind") == "mcp_gate_structured_legacy_mismatch" for item in residuals
    )
    return (
        {
            "blockers": sorted(set(blockers)),
            "descriptor_hash": descriptor_hash,
            "invocation_descriptor_hash": invocation_descriptor_hash,
            "legacy_accepted": legacy_accepted,
            "legacy_present": legacy_present,
            "ok": ok,
            "refs": {
                "descriptor": provider_profile.get("mcp_tool_descriptor_report_ref"),
                "invocation_preflight": provider_profile.get("mcp_tool_invocation_preflight_ref"),
            },
            "required": required,
            "residual_kinds": sorted(
                {str(item.get("kind")) for item in residuals if item.get("kind")}
            ),
            "structured_present": structured_present,
        },
        residuals,
    )


def _a2a_agent_gate_report(
    trace_id: str,
    provider_profile: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    agent_card = _mapping(provider_profile.get("a2a_agent_card_report"))
    handoff = _mapping(provider_profile.get("a2a_task_handoff_report"))
    structured_present = bool(agent_card or handoff)
    required = bool(provider_profile.get("requires_a2a_agent") or structured_present)
    legacy_present = "a2a_agent_gate_accepted" in provider_profile
    legacy_accepted = bool(provider_profile.get("a2a_agent_gate_accepted"))
    blockers: list[str] = []
    residuals: list[dict[str, Any]] = []
    agent_card_hash = (
        _report_hash(agent_card, "agent_card_hash", "card_hash", "hash") if agent_card else None
    )
    handoff_hash = (
        _report_hash(handoff, "handoff_hash", "task_handoff_hash", "hash") if handoff else None
    )
    handoff_agent_card_hash = (
        str(_first_value(handoff.get("agent_card_hash"), handoff.get("card_hash")) or "")
        if handoff
        else ""
    ) or None
    if structured_present:
        if not agent_card:
            _gate_blocker(
                trace_id,
                "a2a-agent-gate",
                "a2a_agent_card_report_required",
                blockers,
                residuals,
            )
        elif not _structured_report_accepted(agent_card, {"agent_ready", "card_ready"}):
            _gate_blocker(
                trace_id,
                "a2a-agent-gate",
                "a2a_agent_card_report_not_accepted",
                blockers,
                residuals,
            )
        if not handoff:
            _gate_blocker(
                trace_id,
                "a2a-agent-gate",
                "a2a_task_handoff_report_required",
                blockers,
                residuals,
            )
        elif not _structured_report_accepted(
            handoff,
            {"handoff_ready", "task_handoff_ready", "delegation_ready"},
        ):
            _gate_blocker(
                trace_id,
                "a2a-agent-gate",
                "a2a_task_handoff_report_not_accepted",
                blockers,
                residuals,
            )
        if (
            agent_card_hash
            and handoff_agent_card_hash
            and agent_card_hash != handoff_agent_card_hash
        ):
            _gate_blocker(
                trace_id,
                "a2a-agent-gate",
                "a2a_agent_card_handoff_hash_mismatch",
                blockers,
                residuals,
            )
        structured_ok = not blockers
    else:
        structured_ok = False
        if required and not legacy_accepted:
            _gate_blocker(
                trace_id,
                "a2a-agent-gate",
                "a2a_agent_gate_not_accepted",
                blockers,
                residuals,
            )
    if structured_present and legacy_present and structured_ok != legacy_accepted:
        _gate_blocker(
            trace_id,
            "a2a-agent-gate",
            "a2a_gate_structured_legacy_mismatch",
            blockers,
            residuals,
        )
    ok = (structured_ok if structured_present else (not required or legacy_accepted)) and not any(
        item.get("kind") == "a2a_gate_structured_legacy_mismatch" for item in residuals
    )
    return (
        {
            "agent_card_hash": agent_card_hash,
            "blockers": sorted(set(blockers)),
            "handoff_agent_card_hash": handoff_agent_card_hash,
            "handoff_hash": handoff_hash,
            "legacy_accepted": legacy_accepted,
            "legacy_present": legacy_present,
            "ok": ok,
            "refs": {
                "agent_card": provider_profile.get("a2a_agent_card_report_ref"),
                "task_handoff": provider_profile.get("a2a_task_handoff_report_ref"),
            },
            "required": required,
            "residual_kinds": sorted(
                {str(item.get("kind")) for item in residuals if item.get("kind")}
            ),
            "structured_present": structured_present,
        },
        residuals,
    )


def _physical_dispatch_residuals(
    trace_id: str,
    provider_profile: Mapping[str, Any],
    reference: datetime | None,
    side_effect_policy: str,
) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    physical_domain = _mapping(provider_profile.get("physical_domain_profile"))
    actuator_class = str(provider_profile.get("actuator_class") or "")
    allowed_actuators = set(_list_field(provider_profile, "allowed_actuator_classes")) | set(
        _list_field(physical_domain, "allowed_actuator_classes")
    )
    human_authority = _mapping(provider_profile.get("human_operator_authority"))
    emergency_stop = _mapping(provider_profile.get("emergency_stop"))
    runtime_certificate = _mapping(provider_profile.get("runtime_assurance_certificate"))
    shield_certificate = _mapping(provider_profile.get("shield_certificate"))
    rollback_escrow = _mapping(provider_profile.get("rollback_escrow"))
    hazard_envelope = _mapping(
        provider_profile.get("hazard_envelope")
        or provider_profile.get("hazard_envelope_certificate")
    )
    observation_window = _mapping(provider_profile.get("observation_window"))
    tolerance_ledger = _mapping(provider_profile.get("tolerance_ledger"))
    resource_use = _mapping(provider_profile.get("resource_use"))
    resource_limit = _mapping(provider_profile.get("resource_limit"))

    checks: list[tuple[bool, str]] = [
        (
            _status_ok(physical_domain, {"accepted", "approved"}),
            "physical_profile_not_accepted",
        ),
        (
            not allowed_actuators or actuator_class in allowed_actuators,
            "actuator_class_not_allowed",
        ),
        (
            _status_ok(human_authority, {"approved", "active"})
            and _fresh_until(human_authority, reference),
            "human_operator_authority_not_approved",
        ),
        (
            _status_ok(emergency_stop, {"accepted", "tested", "available"}),
            "emergency_stop_not_tested",
        ),
        (
            _certificate_fresh(runtime_certificate, reference)
            and _status(runtime_certificate) in {"accepted", "fresh", "approved"},
            "runtime_assurance_certificate_not_accepted",
        ),
        (
            not (provider_profile.get("requires_shield_certificate") or shield_certificate)
            or (
                _certificate_fresh(shield_certificate, reference)
                and _status(shield_certificate) in {"accepted", "fresh", "approved"}
            ),
            "shield_certificate_not_accepted",
        ),
        (
            _status_ok(rollback_escrow, {"available", "verified"}),
            "rollback_escrow_not_verified",
        ),
        (
            _certificate_fresh(hazard_envelope, reference)
            and _status(hazard_envelope) in {"accepted", "fresh", "approved"},
            "hazard_envelope_not_accepted",
        ),
        (
            observation_window.get("has_verifier") is True
            or _status_ok(observation_window.get("verifier"), {"accepted", "approved", "active"}),
            "observation_verifier_required",
        ),
        (
            _within_numeric_budget(resource_use, resource_limit),
            "resource_use_exceeds_profile",
        ),
        (
            _tolerance_within_budget(tolerance_ledger),
            "tolerance_budget_exceeded",
        ),
        (
            _lifecycle_fresh(provider_profile, reference),
            "lifecycle_certificate_stale",
        ),
        (
            side_effect_policy
            in {
                "physical_provider_allowed",
                "provider_physical_allowed",
                "controlled_physical_allowed",
            },
            "side_effect_policy_not_dispatchable",
        ),
    ]
    for ok, kind in checks:
        if not ok:
            residuals.append(_trace_residual(trace_id, "physical-dispatch", kind, True))
    return residuals


def _within_numeric_budget(usage: Mapping[str, Any], limit: Mapping[str, Any]) -> bool:
    if not usage or not limit:
        return True
    for key, value in usage.items():
        if key not in limit:
            continue
        used = _optional_float(value)
        allowed = _optional_float(limit.get(key))
        if used is not None and allowed is not None and used > allowed:
            return False
    return True


def _tolerance_within_budget(tolerance: Mapping[str, Any]) -> bool:
    if not tolerance:
        return True
    for key, value in tolerance.items():
        if key.endswith("_budget"):
            continue
        budget = tolerance.get(f"{key}_budget") or tolerance.get("budget")
        observed = _optional_float(value)
        allowed = _optional_float(budget)
        if observed is not None and allowed is not None and observed > allowed:
            return False
    return True


def _lifecycle_fresh(provider_profile: Mapping[str, Any], reference: datetime | None) -> bool:
    cert = _mapping(
        provider_profile.get("lifecycle_certificate")
        or provider_profile.get("certificate_lifecycle")
    )
    if not cert:
        return bool(provider_profile.get("lifecycle_recomputed"))
    return _certificate_fresh(cert, reference)


def _authority_residuals(
    trace_id: str,
    trace_nf: Mapping[str, Any],
    nf: Mapping[str, Any],
    provider_profile: Mapping[str, Any],
) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    steps = [item for item in nf.get("steps", []) if isinstance(item, Mapping)]
    fixture_dry_run = _bool_context(trace_nf, nf, provider_profile, "fixture_mode") and (
        _side_effect_policy(trace_nf, nf, provider_profile) == "dry_run_only"
    )
    reference = _reference_time(trace_nf, nf, provider_profile)
    trusted_issuers = set(_list_field(provider_profile, "trusted_issuers"))
    provider_target_tokens = _scope_tokens(
        _context_value(trace_nf, nf, provider_profile, "provider_target", "provider")
    )

    for step in steps:
        step_id = str(step.get("step_id", "step"))
        authority = _mapping(step.get("authority_envelope"))
        if not authority or str(authority.get("status", "")).lower() == "missing":
            continue
        status = str(authority.get("status", "")).lower()
        if status not in _ACTIVE_AUTHORITY_STATUSES:
            residuals.append(
                _trace_residual(trace_id, step_id, "authority_status_not_active", True)
            )

        issuer = str(authority.get("issuer", ""))
        if trusted_issuers and issuer not in trusted_issuers:
            residuals.append(_trace_residual(trace_id, step_id, "authority_issuer_untrusted", True))

        expires_at = authority.get("expires_at")
        if expires_at in (None, ""):
            if not fixture_dry_run:
                residuals.append(_trace_residual(trace_id, step_id, "authority_time_unknown", True))
        else:
            expiry = _parse_time(expires_at)
            if expiry is None:
                residuals.append(_trace_residual(trace_id, step_id, "authority_time_unknown", True))
            elif reference is None:
                if not fixture_dry_run:
                    residuals.append(
                        _trace_residual(trace_id, step_id, "authority_time_unknown", True)
                    )
            elif expiry <= reference:
                residuals.append(
                    _trace_residual(trace_id, step_id, "expired_authority_envelope", True)
                )
            if str(expires_at) == FIXED_CREATED_AT and fixture_dry_run:
                residuals.append(
                    _trace_residual(
                        trace_id,
                        step_id,
                        "fixture_only_authority_non_executable",
                        True,
                    )
                )

        required_scope = _scope_tokens(step.get("validity_domain")) | provider_target_tokens
        if not _scope_matches(authority, required_scope):
            residuals.append(_trace_residual(trace_id, step_id, "authority_scope_mismatch", True))
    return residuals


def _gate_residuals(
    residuals: Sequence[Mapping[str, Any]],
    kinds: set[str],
) -> list[dict[str, Any]]:
    return [dict(item) for item in residuals if str(item.get("kind")) in kinds]


def trace_check_report(trace_nf: Mapping[str, Any]) -> dict[str, Any]:
    """Check a practical TraceNF report conservatively."""

    nf = _mapping(trace_nf.get("trc_trace_nf")) or trace_nf
    steps = [item for item in nf.get("steps", []) if isinstance(item, Mapping)]
    residuals: list[dict[str, Any]] = []
    for step in steps:
        for residual in step.get("residuals", []):
            if isinstance(residual, dict):
                residuals.append(dict(residual))
    if not steps:
        residuals.append(
            _trace_residual(
                str(trace_nf.get("trace_id", "trace")),
                "trace",
                "missing_steps",
                True,
            )
        )
    trace_id = str(trace_nf.get("trace_id") or nf.get("trace_id") or "trace")
    residuals.extend(_authority_residuals(trace_id, trace_nf, nf, {}))
    missing_authority = any(item.get("kind") == "missing_authority_envelope" for item in residuals)
    missing_resource = any(item.get("kind") == "missing_resource_ledger" for item in residuals)
    missing_rollback = any(
        item.get("kind") == "missing_rollback_escrow_obligation" for item in residuals
    )
    missing_tolerance = any(item.get("kind") == "missing_tolerance_ledger" for item in residuals)
    execution_blockers = sorted(
        {
            str(item.get("kind"))
            for item in residuals
            if item.get("kind") in _CORE_OPERATION_BLOCKERS
        }
    )
    execution_available = bool(steps) and not execution_blockers
    side_effect_policy = _side_effect_policy(trace_nf, nf, {})
    authority_gate_residuals = _gate_residuals(
        residuals,
        _AUTHORITY_RESIDUAL_KINDS,
    )
    return {
        "accepted": bool(steps) and not any(item.get("blocking") for item in residuals),
        "execution_available": execution_available,
        "execution_blockers": execution_blockers,
        "missing_obligations": [item["kind"] for item in residuals],
        "ok": True,
        "real_world_operation_gate": {
            "authority_gate": _gate(not authority_gate_residuals, authority_gate_residuals),
            "executed": False,
            "operation_ready": execution_available,
            "physical_dispatch_ready": False,
            "provider_dispatch_ready": False,
            "requires_explicit_authority": True,
            "requires_provider_config": True,
            "safe_commands_are_authority": False,
            "side_effect_policy": side_effect_policy,
        },
        "residuals": residuals,
        "schema_version": "pic.trc_trace_report.v1",
        "settled": False,
        "status": "diagnostic" if residuals else "provisional",
        "trace_id": trace_id,
        "trc_trace_nf": nf,
        "warnings": [
            warning
            for condition, warning in (
                (missing_resource, "missing resource ledger blocks resource/tolerance claims"),
                (missing_rollback, "missing rollback/escrow blocks real-world operation claims"),
                (missing_tolerance, "missing tolerance ledger blocks TRC operation claims"),
                (missing_authority, "missing authority envelope blocks operation claims"),
                (
                    bool(authority_gate_residuals),
                    "authority freshness/scope/trust blocks operation claims",
                ),
            )
            if condition
        ],
    }


def operation_gate_report(
    trace_nf: Mapping[str, Any],
    *,
    provider_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a detailed TRC operation gate report without executing anything."""

    profile = _mapping(provider_profile)
    nf = _mapping(trace_nf.get("trc_trace_nf")) or trace_nf
    steps = [item for item in nf.get("steps", []) if isinstance(item, Mapping)]
    trace_id = str(trace_nf.get("trace_id") or nf.get("trace_id") or "trace")
    checked = trace_check_report(trace_nf)
    base_residuals = [
        dict(item)
        for item in checked.get("residuals", [])
        if isinstance(item, Mapping) and str(item.get("kind")) not in _AUTHORITY_RESIDUAL_KINDS
    ]
    residuals = base_residuals + _authority_residuals(trace_id, trace_nf, nf, profile)
    side_effect_policy = _side_effect_policy(trace_nf, nf, profile)
    fixture_dry_run = _bool_context(trace_nf, nf, profile, "fixture_mode") and (
        side_effect_policy == "dry_run_only"
    )
    reference = _reference_time(trace_nf, nf, profile)

    additional_residuals: list[dict[str, Any]] = []
    if not fixture_dry_run:
        if any(not _mapping(step).get("causal_schedule_block") for step in steps):
            additional_residuals.append(
                _trace_residual(trace_id, "operation", "missing_causal_schedule_block", True)
            )
        has_hazard = bool(
            profile.get("hazard_envelope")
            or profile.get("hazard_envelope_certificate")
            or any(
                _mapping(step).get("hazard_envelope")
                or _mapping(step).get("hazard_envelope_certificate")
                for step in steps
            )
        )
        if not has_hazard:
            additional_residuals.append(
                _trace_residual(trace_id, "operation", "missing_hazard_envelope", True)
            )
        has_lifecycle = bool(
            profile.get("certificate_version_refs")
            or any(_list_field(_mapping(step), "certificate_version_refs") for step in steps)
        )
        if not has_lifecycle:
            additional_residuals.append(
                _trace_residual(trace_id, "operation", "missing_certificate_lifecycle", True)
            )
    residuals.extend(additional_residuals)
    mcp_tool_gate, mcp_tool_gate_residuals = _mcp_tool_gate_report(trace_id, profile)
    a2a_agent_gate, a2a_agent_gate_residuals = _a2a_agent_gate_report(trace_id, profile)
    residuals.extend(mcp_tool_gate_residuals)
    residuals.extend(a2a_agent_gate_residuals)
    structured_gate_blocker_kinds = {
        str(item.get("kind"))
        for item in [*mcp_tool_gate_residuals, *a2a_agent_gate_residuals]
        if item.get("blocking")
    }

    operation_blocker_kinds = (
        _CORE_OPERATION_BLOCKERS
        | {
            "missing_causal_schedule_block",
            "missing_certificate_lifecycle",
            "missing_hazard_envelope",
        }
        | structured_gate_blocker_kinds
    )
    execution_blockers = sorted(
        {
            str(item.get("kind"))
            for item in residuals
            if str(item.get("kind")) in operation_blocker_kinds
        }
    )
    operation_ready = bool(steps) and not execution_blockers
    provider_policy_allows = (
        operation_ready
        and not fixture_dry_run
        and side_effect_policy not in {"dry_run_only", "none", "none_without_execute_flag"}
        and bool(profile.get("allow_execute"))
        and bool(profile.get("explicit_execute"))
        and bool(mcp_tool_gate["ok"])
        and bool(a2a_agent_gate["ok"])
    )

    physical_requested = bool(
        profile.get("physical_dispatch_requested")
        or profile.get("physical_domain_profile")
        or profile.get("actuator_class")
    )
    physical_missing: list[dict[str, Any]] = []
    if physical_requested:
        for key, label in _PHYSICAL_PROFILE_FIELDS.items():
            if not profile.get(key):
                physical_missing.append(
                    {
                        **_trace_residual(trace_id, "physical-dispatch", f"missing_{key}", True),
                        "description": f"missing {label}",
                    }
                )
        physical_missing.extend(
            _physical_dispatch_residuals(trace_id, profile, reference, side_effect_policy)
        )
    physical_dispatch_ready = provider_policy_allows and physical_requested and not physical_missing

    authority_residuals = _gate_residuals(residuals, _AUTHORITY_RESIDUAL_KINDS)
    gates = {
        "authority_gate": _gate(not authority_residuals, authority_residuals),
        "capability_gate": _gate(
            not _gate_residuals(residuals, _OPERATION_GATE_KINDS["capability_gate"]),
            _gate_residuals(residuals, _OPERATION_GATE_KINDS["capability_gate"]),
        ),
        "hazard_gate": _gate(
            not _gate_residuals(residuals, {"missing_hazard_envelope"}),
            _gate_residuals(residuals, {"missing_hazard_envelope"}),
        ),
        "resource_gate": _gate(
            not _gate_residuals(residuals, _OPERATION_GATE_KINDS["resource_gate"]),
            _gate_residuals(residuals, _OPERATION_GATE_KINDS["resource_gate"]),
        ),
        "rollback_gate": _gate(
            not _gate_residuals(residuals, _OPERATION_GATE_KINDS["rollback_gate"]),
            _gate_residuals(residuals, _OPERATION_GATE_KINDS["rollback_gate"]),
        ),
        "tolerance_gate": _gate(
            not _gate_residuals(residuals, _OPERATION_GATE_KINDS["tolerance_gate"]),
            _gate_residuals(residuals, _OPERATION_GATE_KINDS["tolerance_gate"]),
        ),
        "schedule_gate": _gate(
            not _gate_residuals(residuals, {"missing_causal_schedule_block"}),
            _gate_residuals(residuals, {"missing_causal_schedule_block"}),
        ),
        "clock_gate": _gate(
            reference is not None or fixture_dry_run,
            _gate_residuals(residuals, {"authority_time_unknown"}),
        ),
        "observation_gate": _gate(
            not _gate_residuals(residuals, {"missing_step_witness"}),
            _gate_residuals(residuals, {"missing_step_witness"}),
        ),
        "lifecycle_gate": _gate(
            not _gate_residuals(residuals, {"missing_certificate_lifecycle"}),
            _gate_residuals(residuals, {"missing_certificate_lifecycle"}),
        ),
        "mcp_tool_gate": mcp_tool_gate,
        "a2a_agent_gate": a2a_agent_gate,
    }
    return {
        "accepted": bool(steps),
        "a2a_agent_gate": gates["a2a_agent_gate"],
        "authority_gate": gates["authority_gate"],
        "capability_gate": gates["capability_gate"],
        "clock_gate": gates["clock_gate"],
        "executed": False,
        "execution_blockers": execution_blockers,
        "hazard_gate": gates["hazard_gate"],
        "lifecycle_gate": gates["lifecycle_gate"],
        "mcp_tool_gate": gates["mcp_tool_gate"],
        "non_claims": [
            *list(NON_CLAIMS),
            "operation_ready_is_not_executed",
            "physical_dispatch_ready_is_not_physical_outcome_proof",
        ],
        "observation_gate": gates["observation_gate"],
        "ok": True,
        "operation_ready": operation_ready,
        "physical_dispatch_blockers": [
            str(item.get("kind")) for item in physical_missing if item.get("kind")
        ],
        "physical_dispatch_ready": physical_dispatch_ready,
        "provider_dispatch_ready": provider_policy_allows,
        "residuals": residuals + physical_missing,
        "resource_gate": gates["resource_gate"],
        "rollback_gate": gates["rollback_gate"],
        "schedule_gate": gates["schedule_gate"],
        "schema_version": "pic.trc_operation_gate_report.v1",
        "settled": False,
        "side_effect_policy": side_effect_policy,
        "tolerance_gate": gates["tolerance_gate"],
        "trace_id": trace_id,
        "trc_trace_nf": nf,
    }


def trace_packet_candidate(trace_nf: Mapping[str, Any]) -> dict[str, Any]:
    """Convert TraceNF into a candidate packet without settlement."""

    report = trace_check_report(trace_nf)
    trace_id = str(report["trace_id"])
    return {
        "accepted": bool(report["accepted"]),
        "candidate_only_reasons": [
            "TRC trace-to-packet output is candidate-only until verifier routes pass"
        ],
        "claims": [
            {
                "claim_id": f"claim:{trace_id}:trace-normal-form",
                "claim_text": "Agent trace has a finite practical TRC trace normal form.",
                "claim_type": "trace_normal_form",
                "status": "candidate",
            }
        ],
        "non_claims": list(NON_CLAIMS),
        "packet_id": f"trc-packet:{_short_hash(trace_id)}",
        "residuals": report["residuals"],
        "schema_version": "pic.packet_candidate.v1",
        "settled": False,
        "source_trace_id": trace_id,
        "status": "candidate",
        "trc_trace_nf": report["trc_trace_nf"],
    }


def bit_registry_report(source_text: str, *, source: str = "") -> dict[str, Any]:
    """Extract literal or macro MRRecord registry rows."""

    records: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    for line_number, line in enumerate(source_text.splitlines(), start=1):
        parsed = _parse_literal_mr(line, line_number)
        if parsed is not None:
            records.append(parsed)
            residuals.extend(parsed.get("parse_residuals", []))
    for mr_record in extract_mr_records(source_text):
        records.append(
            {
                "fields": mr_record.fields,
                "id": mr_record.identifier,
                "line_number": mr_record.line_number,
                "parse_residuals": [],
                "raw_line": mr_record.raw,
                "record_type": mr_record.record_type,
                "source_form": "tex_macro",
            }
        )
    unique: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for record in records:
        key = (
            str(record["record_type"]),
            str(record["id"]),
            int(record["line_number"]),
            str(record["raw_line"]),
        )
        unique[key] = record
    records = sorted(
        unique.values(),
        key=lambda item: (item["line_number"], item["record_type"], item["id"]),
    )
    edges = _bit_dependency_edges(records)
    missing = _bit_missing_witness_claims(records)
    return {
        "dependency_edges": edges,
        "missing_witness_claims": missing,
        "ok": True,
        "records": records,
        "residuals": residuals,
        "schema_version": "pic.bit_registry.v1",
        "source": source,
    }


def bit_tasks_from_registry(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Emit CCR witness-completion tasks for unwitnessed BIT claims."""

    tasks: list[dict[str, Any]] = []
    for claim_id in registry.get("missing_witness_claims", []):
        tasks.append(
            _ccr_task(
                kind="bit_witness_completion",
                title="Complete BIT witness record",
                objective=f"Supply a machine-readable witness for BIT claim {claim_id}.",
                source_id=f"bit:witness:{claim_id}",
                profile="development",
                priority=65,
                role="formalizer",
                inputs=[_input_ref(ref=str(claim_id), kind="claim", notes="Claim lacks witness.")],
                residual_inputs=[f"claim_without_witness:{claim_id}"],
            )
        )
    return sorted(tasks, key=lambda item: item["task_id"])


def _ccr_task(
    *,
    kind: str,
    title: str,
    objective: str,
    source_id: str,
    profile: str,
    priority: int,
    role: str,
    inputs: Sequence[dict[str, Any]] | None = None,
    residual_inputs: Sequence[str] | None = None,
    safe_command_hints: Sequence[str] | None = None,
    verifier_routes: Sequence[str] | None = None,
    candidate_only: bool = False,
) -> dict[str, Any]:
    if kind not in CCR_TASK_KINDS:
        kind = "packet_repair"
    safe_hints = sorted({str(item) for item in safe_command_hints or [] if str(item)})
    residual_refs = sorted({str(item) for item in residual_inputs or [] if str(item)})
    routes = sorted({str(item) for item in verifier_routes or [] if str(item)})
    task_id = f"task:pic:{kind}:{_short_hash([source_id, objective, residual_refs, safe_hints])}"
    return {
        "blackboard_refs": [],
        "completion": {},
        "constraints": {
            "allowed_commands": [],
            "authority_policy": "read_only",
            "forbidden_actions": ["automatic_execution", "shell_expansion"],
            "max_runtime_minutes": 30,
            "network_policy": "none",
            "side_effect_policy": "dry_run_only",
        },
        "created_at": FIXED_CREATED_AT,
        "dependencies": [],
        "expected_outputs": [
            {
                "acceptance_criteria": [
                    "Preserve residuals and do not treat PIC accepted=true as CCR settlement."
                ],
                "destination": "tasks/open",
                "kind": "json",
                "schema_ref": "schemas/task.schema.json",
            }
        ],
        "extensions": {
            "x_candidate_only": candidate_only,
            "x_pic_residual_inputs": residual_refs,
            "x_pic_safe_command_hints": safe_hints,
            "x_pic_source_id": source_id,
            "x_pic_task_kind": kind,
        },
        "inputs": list(inputs or []),
        "lease": {
            "lease_required": True,
            "leased_at": None,
            "leased_by": None,
            "renewal_allowed": True,
            "ttl_minutes": 30,
        },
        "objective": objective,
        "pic_interop": {
            "candidate_only_until_checked": True,
            "enabled": True,
            "identity_context_required": kind == "identity_context_repair",
            "input_mapping": "report_to_phase_plan",
            "output_mapping": "pic_phase_plan_to_tasks",
            "pic_profile": profile
            if profile
            in {
                "development",
                "research",
                "controlled",
                "federated",
                "production",
                "adversarial",
            }
            else "development",
            "recommended_pic_commands": safe_hints,
        },
        "priority": max(0, min(100, int(priority))),
        "residual_policy": {
            "blocking_residuals_prevent_settlement": True,
            "minimum_residual_fields": ["residual_id", "kind", "description", "blocking"],
            "preserve_residuals": True,
            "residual_destination": "residuals/open",
        },
        "role": role,
        "schema_version": "ccr.task.v0.1",
        "status": "open",
        "task_id": task_id,
        "title": title,
        "verifier_plan": {
            "failure_route": "residual",
            "optional_verifiers": routes or ["pic"],
            "promotion_gate": "pic_checked" if routes else "none",
            "required_verifiers": routes,
        },
    }


def _ccr_residual(
    *,
    kind: str,
    description: str,
    blocking: bool,
    object_type: str,
    object_id: str,
    source_id: str,
    source_field: str,
) -> dict[str, Any]:
    residual_id = f"residual:pic:{_short_hash([kind, description, object_id, source_id])}"
    return {
        "blocking": blocking,
        "created_at": FIXED_CREATED_AT,
        "description": description,
        "extensions": {"x_pic_source_field": source_field, "x_pic_source_id": source_id},
        "kind": kind,
        "object_id": object_id,
        "object_type": object_type,
        "refs": [source_id],
        "repair_hint": "Route as CCR repair work; do not discard PIC residual context.",
        "residual_id": residual_id,
        "schema_version": "ccr.residual.v0.1",
        "severity": "high" if blocking else "medium",
        "source": "pic",
        "status": "open",
    }


def _input_ref(ref: str, kind: str, notes: str) -> dict[str, Any]:
    return {"kind": kind, "notes": notes, "ref": ref, "required": True}


def _task_kind_for_bottleneck(bottleneck: BottleneckCandidate) -> str:
    text = " ".join(
        [
            bottleneck.bottleneck_kind,
            bottleneck.target_component,
            " ".join(bottleneck.reasons),
            " ".join(bottleneck.cannot_promote_because),
        ]
    ).lower()
    if "identity" in text:
        return "identity_context_repair"
    if "transport" in text:
        return "transport_certificate_repair"
    if "hazard" in text or "risk" in text:
        return "hazard_envelope_repair"
    if "queue" in text or "sqot" in text or "salience" in text:
        return "sqot_queue_repair"
    if "alt" in text or "liquidity" in text or bottleneck.target_component == "ALT":
        return "alt_capital_check"
    if "trace" in text or "trc" in text:
        return "trc_trace_normalization"
    if "witness" in text or "bit" in text:
        return "bit_witness_completion"
    if "baseline" in text:
        return "baseline_refresh"
    if "route" in text or bottleneck.next_verifier_routes:
        return "verifier_route"
    if "residual" in text:
        return "residual_ledger_repair"
    return "packet_repair"


def _role_for_task_kind(kind: str) -> str:
    return {
        "alt_capital_check": "verifier",
        "baseline_refresh": "benchmark_runner",
        "bit_witness_completion": "formalizer",
        "hazard_envelope_repair": "skeptic",
        "identity_context_repair": "security_reviewer",
        "packet_repair": "implementer",
        "residual_ledger_repair": "integrator",
        "sqot_queue_repair": "scheduler",
        "transport_certificate_repair": "verifier",
        "trc_trace_normalization": "formalizer",
        "verifier_route": "verifier",
    }.get(kind, "integrator")


def _priority(score: float) -> int:
    return max(10, min(95, round(50 + score * 3)))


def _bottleneck_objective(bottleneck: BottleneckCandidate) -> str:
    parts = [bottleneck.bottleneck_kind]
    if bottleneck.target_component:
        parts.append(f"target={bottleneck.target_component}")
    if bottleneck.reasons:
        parts.append("; ".join(bottleneck.reasons[:3]))
    return "Repair PIC phase bottleneck without promoting settlement: " + " | ".join(parts)


def _bridge_residual(packet_id: str, kind: str, blocking: bool) -> dict[str, Any]:
    return {
        "blocking": blocking,
        "description": kind.replace("_", " "),
        "kind": kind,
        "packet_id": packet_id,
        "residual_id": f"alt-ecpt:{_short_hash([packet_id, kind])}",
    }


def _sqot_residual(kind: str, blocking: bool) -> dict[str, Any]:
    return {
        "blocking": blocking,
        "description": kind.replace("_", " "),
        "kind": kind,
        "residual_id": f"sqot:{_short_hash(kind)}",
    }


def _trace_residual(trace_id: str, step_id: str, kind: str, blocking: bool) -> dict[str, Any]:
    return {
        "blocking": blocking,
        "description": kind.replace("_", " "),
        "kind": kind,
        "residual_id": f"trc:{_short_hash([trace_id, step_id, kind])}",
        "step_id": step_id,
    }


def _parse_literal_mr(line: str, line_number: int) -> dict[str, Any] | None:
    stripped = line.strip()
    marker = stripped.find("MRRecord|")
    if marker < 0:
        return None
    raw = stripped[marker:]
    match = _MR_LITERAL_RE.match(raw)
    residuals: list[dict[str, Any]] = []
    if match is None:
        return {
            "fields": {},
            "id": f"malformed:{line_number}",
            "line_number": line_number,
            "parse_residuals": [
                {"kind": "malformed_mrrecord", "line_number": line_number, "raw_line": stripped}
            ],
            "raw_line": stripped,
            "record_type": "malformed",
            "source_form": "literal",
        }
    record_type, identifier, field_text = match.groups()
    if record_type not in _VALID_MR_TYPES:
        residuals.append(
            {"kind": "unknown_record_type", "line_number": line_number, "record_type": record_type}
        )
    fields, field_residuals = _parse_mr_fields(field_text, line_number)
    residuals.extend(field_residuals)
    return {
        "fields": fields,
        "id": identifier,
        "line_number": line_number,
        "parse_residuals": residuals,
        "raw_line": stripped,
        "record_type": record_type,
        "source_form": "literal",
    }


def _parse_mr_fields(
    text: str,
    line_number: int,
) -> tuple[dict[str, str | list[str]], list[dict[str, Any]]]:
    fields: dict[str, str | list[str]] = {}
    residuals: list[dict[str, Any]] = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, sep, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key or not sep:
            residuals.append(
                {"kind": "partial_field", "line_number": line_number, "raw_field": part}
            )
            if key:
                fields[key] = value
            continue
        fields[key] = (
            [item.strip() for item in value.split(",") if item.strip()] if "," in value else value
        )
    return fields, residuals


def _bit_dependency_edges(records: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for record in records:
        if record.get("record_type") != "depends":
            continue
        fields = _mapping(record.get("fields"))
        deps = (
            _list_field(fields, "depends_on")
            or _list_field(fields, "depends")
            or _list_field(fields, "requires")
        )
        if not deps:
            deps = [str(value) for key, value in fields.items() if key and value]
        for dep in deps:
            edges.append(
                {"source": str(dep), "target": str(record.get("id", "")), "type": "depends"}
            )
    return sorted(edges, key=lambda item: (item["target"], item["source"]))


def _bit_missing_witness_claims(records: Sequence[Mapping[str, Any]]) -> list[str]:
    claims = {str(record.get("id")) for record in records if record.get("record_type") == "claim"}
    witnessed: set[str] = set()
    for record in records:
        if record.get("record_type") != "witness":
            continue
        fields = _mapping(record.get("fields"))
        for key in ("claim", "claim_id", "for", "witness_for"):
            witnessed.update(_list_field(fields, key))
        if str(record.get("id")) in claims:
            witnessed.add(str(record.get("id")))
    return sorted(claims - witnessed)


def _trace_steps(trace: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("steps", "events", "tool_calls", "calls", "trace"):
        value = trace.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return [trace]


def _has_cost_upper_bounds(packet: Mapping[str, Any], liquidity: Mapping[str, Any]) -> bool:
    cost = _mapping(liquidity.get("cost_ledger")) or _mapping(packet.get("cost_ledger"))
    if not cost:
        return False
    numeric = [
        value
        for key, value in cost.items()
        if key.endswith("_cost") or key.endswith("_upper_bound") or key in {"formation_cost"}
    ]
    return bool(numeric)


def _transport_scope(packet: Mapping[str, Any], liquidity: Mapping[str, Any]) -> list[str]:
    transport = _mapping(liquidity.get("transport_certificate")) or _mapping(
        packet.get("transport_certificate")
    )
    return (
        _list_field(packet, "transport_scope")
        or _list_field(transport, "target_receiver_family")
        or _list_field(transport, "transport_scope_refs")
        or _list_field(packet, "transport_scope_refs")
    )


def _has_baseline(packet: Mapping[str, Any], liquidity: Mapping[str, Any]) -> bool:
    opportunity = _mapping(liquidity.get("opportunity_contract")) or _mapping(
        packet.get("opportunity_contract")
    )
    return bool(
        packet.get("baseline_ref")
        or liquidity.get("baseline_ref")
        or opportunity.get("baseline_ref")
        or _list_field(packet, "baseline_refs")
    )


def _deep_get(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_field(data: Mapping[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def _report_residual(
    prefix: str,
    subject: Any,
    kind: str,
    blocking: bool = True,
    *,
    description: str | None = None,
) -> dict[str, Any]:
    return {
        "blocking": blocking,
        "description": description or kind.replace("_", " "),
        "kind": kind,
        "residual_id": f"{prefix}:{_short_hash([subject, kind])}",
    }


def _blocking_kinds(residuals: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({str(item.get("kind")) for item in residuals if item.get("blocking")})


def _required_residuals(
    prefix: str,
    subject: Any,
    data: Mapping[str, Any],
    fields: Sequence[str],
) -> list[dict[str, Any]]:
    return [
        _report_residual(prefix, subject, f"missing_{field}")
        for field in fields
        if data.get(field) in (None, "", [], {})
    ]


def _profile_settings(profile: str | Mapping[str, Any]) -> dict[str, Any]:
    defaults = {
        "allowed_auth_scopes": ["read", "local", "local_fixture", "fixture"],
        "allowed_egress_policies": ["none", "disabled", "allowlist"],
        "allowed_side_effect_classes": ["read_only", "none", "diagnostic"],
        "max_byte_limit": 1_000_000,
        "max_timeout_budget": 30,
        "require_descriptor_provenance": False,
        "require_signature": False,
        "trusted_server_statuses": ["trusted", "approved", "accepted"],
    }
    if isinstance(profile, Mapping):
        return {**defaults, "profile": "custom", **dict(profile)}
    normalized = str(profile or "development").lower()
    strict = normalized in {"production", "adversarial"}
    return {
        **defaults,
        "profile": normalized,
        "require_descriptor_provenance": strict,
        "require_signature": strict,
    }


def _list_any(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _lower_tokens(value: Any) -> set[str]:
    return {item.strip().lower() for item in _list_any(value) if item.strip()}


def _dangerous_text(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    markers = [
        "ignore previous",
        "system prompt",
        "developer message",
        "rm -rf",
        "powershell",
        "bash -lc",
        "curl ",
        "wget ",
        "ssh ",
        "http://",
        "https://",
        "subprocess",
        "exec(",
        "eval(",
    ]
    return any(marker in text for marker in markers)


def _records_any(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def mcp_tool_descriptor_report(
    descriptor: Mapping[str, Any],
    *,
    profile: str | Mapping[str, Any] = "development",
) -> dict[str, Any]:
    """Check an MCP tool descriptor as untrusted candidate evidence."""

    settings = _profile_settings(profile)
    server_id = str(descriptor.get("server_id") or descriptor.get("server") or "")
    tool_name = str(descriptor.get("tool_name") or descriptor.get("name") or "")
    canonical_name = f"{server_id}/{tool_name}" if server_id and tool_name else ""
    descriptor_version = str(
        descriptor.get("descriptor_version") or descriptor.get("version") or ""
    )
    server_status = str(
        descriptor.get("server_trust_status") or descriptor.get("trust_status") or ""
    ).lower()
    side_effect_class = str(descriptor.get("side_effect_class") or "unknown").lower()
    egress_policy = str(descriptor.get("egress_policy") or "unknown").lower()
    auth_scope = _list_any(descriptor.get("auth_scope") or descriptor.get("auth_scopes"))
    subject = canonical_name or _digest(descriptor)
    residuals = _required_residuals(
        "mcp",
        subject,
        descriptor,
        ("server_id", "tool_name", "descriptor_version", "side_effect_class"),
    )
    if server_status not in _lower_tokens(settings["trusted_server_statuses"]):
        residuals.append(_report_residual("mcp", subject, "server_trust_not_accepted"))
    if settings["require_descriptor_provenance"] and not (
        descriptor.get("provenance") or descriptor.get("signature")
    ):
        residuals.append(_report_residual("mcp", subject, "descriptor_provenance_required"))
    if settings["require_signature"] and not descriptor.get("signature"):
        residuals.append(_report_residual("mcp", subject, "descriptor_signature_required"))
    if side_effect_class not in _lower_tokens(settings["allowed_side_effect_classes"]):
        residuals.append(_report_residual("mcp", subject, "side_effect_class_not_allowed"))
    if egress_policy not in _lower_tokens(settings["allowed_egress_policies"]):
        residuals.append(_report_residual("mcp", subject, "egress_policy_not_allowed"))
    if not set(token.lower() for token in auth_scope).issubset(
        _lower_tokens(settings["allowed_auth_scopes"])
    ):
        residuals.append(_report_residual("mcp", subject, "auth_scope_not_allowed"))

    diagnostic_residuals: list[dict[str, Any]] = []
    dangerous_keys = sorted(
        key
        for key in descriptor
        if str(key).lower()
        in {"system_prompt", "developer_message", "secrets", "password", "shell", "exec"}
    )
    if dangerous_keys:
        residuals.append(
            {
                **_report_residual("mcp", subject, "dangerous_metadata_fields"),
                "fields": dangerous_keys,
            }
        )
    if _dangerous_text(descriptor.get("description")):
        diagnostic_residuals.append(
            _report_residual(
                "mcp",
                subject,
                "prompt_injection_bearing_description_risk",
                False,
            )
        )
    if descriptor.get("descriptor_changed_after_approval") is True:
        residuals.append(_report_residual("mcp", subject, "descriptor_rug_pull_blocked"))

    input_schema = descriptor.get("input_schema") or descriptor.get("inputSchema")
    output_schema = descriptor.get("output_schema") or descriptor.get("outputSchema")
    blockers = _blocking_kinds([*residuals, *diagnostic_residuals])
    return {
        "accepted": not blockers,
        "auth_scope": auth_scope,
        "blockers": blockers,
        "canonical_tool_name": canonical_name,
        "descriptor_changed_after_approval": bool(
            descriptor.get("descriptor_changed_after_approval")
        ),
        "descriptor_hash": _digest(descriptor),
        "descriptor_version": descriptor_version,
        "egress_policy": egress_policy,
        "input_schema_hash": _digest(input_schema) if input_schema else None,
        "non_claims": [
            *NON_CLAIMS,
            "mcp_descriptor_is_candidate_evidence_not_execution_authority",
        ],
        "ok": True,
        "output_schema_hash": _digest(output_schema) if output_schema else None,
        "profile": settings["profile"],
        "residuals": sorted([*residuals, *diagnostic_residuals], key=lambda item: item["kind"]),
        "schema_version": "pic.mcp_tool_descriptor_report.v1",
        "server_id": server_id,
        "server_trust_status": server_status,
        "settled": False,
        "side_effect_class": side_effect_class,
        "tool_name": tool_name,
    }


def mcp_tool_invocation_preflight(
    descriptor: Mapping[str, Any],
    call: Mapping[str, Any],
    *,
    profile: str | Mapping[str, Any] = "development",
) -> dict[str, Any]:
    """Preflight an MCP tool call without dispatching it."""

    descriptor_report = mcp_tool_descriptor_report(descriptor, profile=profile)
    settings = _profile_settings(profile)
    canonical = str(descriptor_report.get("canonical_tool_name") or "")
    requested = str(
        call.get("canonical_tool_name") or call.get("tool") or call.get("tool_name") or ""
    )
    side_effect_class = str(descriptor_report.get("side_effect_class") or "unknown").lower()
    residuals = [
        dict(item)
        for item in descriptor_report.get("residuals", [])
        if isinstance(item, Mapping) and item.get("blocking")
    ]
    subject = requested or canonical or _digest(call)
    if not descriptor_report.get("accepted"):
        residuals.append(_report_residual("mcp-call", subject, "descriptor_not_accepted"))
    if canonical and requested and requested not in {canonical, canonical.split("/", 1)[-1]}:
        residuals.append(_report_residual("mcp-call", subject, "canonical_tool_name_mismatch"))
    if side_effect_class not in {"read_only", "none", "diagnostic"} and not call.get(
        "approval_ref"
    ):
        residuals.append(_report_residual("mcp-call", subject, "per_call_approval_required"))
    if side_effect_class not in _lower_tokens(settings["allowed_side_effect_classes"]):
        residuals.append(_report_residual("mcp-call", subject, "side_effect_class_not_allowed"))
    if not call.get("output_redaction_policy"):
        residuals.append(_report_residual("mcp-call", subject, "output_redaction_policy_required"))
    if call.get("trace_logging_enabled") is not True:
        residuals.append(_report_residual("mcp-call", subject, "trace_logging_required"))
    if descriptor_report.get("descriptor_changed_after_approval"):
        residuals.append(_report_residual("mcp-call", subject, "descriptor_rug_pull_blocked"))
    if call.get("tool_name_collision") is True:
        residuals.append(_report_residual("mcp-call", subject, "tool_name_collision"))
    if _dangerous_text(call.get("arguments") or call.get("input") or call):
        residuals.append(_report_residual("mcp-call", subject, "hidden_escalation_in_arguments"))
    timeout = _optional_float(call.get("timeout_budget"))
    byte_limit = _optional_float(call.get("byte_limit"))
    if timeout is not None and timeout > _float_value(settings.get("max_timeout_budget"), 30):
        residuals.append(_report_residual("mcp-call", subject, "timeout_budget_exceeded"))
    if byte_limit is not None and byte_limit > _float_value(
        settings.get("max_byte_limit"), 1_000_000
    ):
        residuals.append(_report_residual("mcp-call", subject, "byte_limit_exceeded"))

    blockers = _blocking_kinds(residuals)
    return {
        "blockers": blockers,
        "canonical_tool_name": canonical,
        "descriptor_report": descriptor_report,
        "executed": False,
        "invocation_ready": not blockers,
        "network_call_performed": False,
        "non_claims": [
            *NON_CLAIMS,
            "mcp_invocation_preflight_is_not_tool_dispatch",
        ],
        "ok": True,
        "profile": settings["profile"],
        "requested_tool_name": requested,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.mcp_tool_invocation_preflight.v1",
        "settled": False,
    }


def a2a_agent_card_report(
    card: Mapping[str, Any],
    *,
    profile: str | Mapping[str, Any] = "development",
) -> dict[str, Any]:
    """Check an A2A agent card without inferring delegated authority."""

    settings = _profile_settings(profile)
    agent_id = str(card.get("agent_id") or card.get("id") or "")
    residuals = _required_residuals(
        "a2a-card",
        agent_id or _digest(card),
        card,
        ("agent_id", "endpoint", "task_schema", "declared_authority"),
    )
    endpoint = _mapping(card.get("endpoint"))
    if not (endpoint.get("provenance") or endpoint.get("url")):
        residuals.append(_report_residual("a2a-card", agent_id, "endpoint_provenance_required"))
    if settings["require_signature"] and not card.get("signature"):
        residuals.append(_report_residual("a2a-card", agent_id, "agent_card_signature_required"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "agent_id": agent_id,
        "blockers": blockers,
        "endpoint_hash": _digest(endpoint) if endpoint else None,
        "non_claims": [
            *NON_CLAIMS,
            "a2a_agent_card_is_not_delegated_tool_authority",
        ],
        "ok": True,
        "profile": settings["profile"],
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.a2a_agent_card_report.v1",
        "settled": False,
    }


def a2a_task_handoff_report(
    handoff: Mapping[str, Any],
    *,
    profile: str | Mapping[str, Any] = "development",
) -> dict[str, Any]:
    """Check an A2A task handoff as provider evidence, not settlement."""

    settings = _profile_settings(profile)
    handoff_id = str(handoff.get("handoff_id") or handoff.get("task_id") or _short_hash(handoff))
    residuals = _required_residuals(
        "a2a-handoff",
        handoff_id,
        handoff,
        ("agent_card_ref", "task_schema", "handoff_scope", "replay_nonce", "idempotency_key"),
    )
    if not handoff.get("declared_authority"):
        residuals.append(_report_residual("a2a-handoff", handoff_id, "declared_authority_required"))
    if handoff.get("delegated_tool_execution") is True:
        residuals.append(
            _report_residual("a2a-handoff", handoff_id, "delegated_execution_not_inferred")
        )
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "handoff_id": handoff_id,
        "non_claims": [
            *NON_CLAIMS,
            "a2a_handoff_result_is_provider_evidence_not_settlement",
            "a2a_message_does_not_grant_delegated_tool_execution",
        ],
        "ok": True,
        "profile": settings["profile"],
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.a2a_task_handoff_report.v1",
        "settled": False,
    }


def _target_status_residuals(target_id: str, target: Mapping[str, Any]) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    for field in ("mission_law", "generated_law", "externality_law"):
        if not _status_ok(target.get(field), {"accepted", "approved", "fresh", "active"}):
            residuals.append(_report_residual("target", target_id, f"{field}_not_accepted"))
    if not _status_ok(target.get("hazard_envelope"), {"accepted", "approved", "active"}):
        residuals.append(_report_residual("target", target_id, "hazard_envelope_not_accepted"))
    if not _status_ok(target.get("authority_envelope"), {"accepted", "approved", "active"}):
        residuals.append(_report_residual("target", target_id, "authority_envelope_not_approved"))
    if not _status_ok(target.get("capability_envelope"), {"accepted", "approved", "active"}):
        residuals.append(_report_residual("target", target_id, "capability_envelope_not_accepted"))
    if not _status_ok(target.get("viability_set"), {"accepted", "approved", "active"}):
        residuals.append(_report_residual("target", target_id, "viability_set_not_accepted"))
    if target.get("target_set_changed_after_observation") is True:
        residuals.append(_report_residual("target", target_id, "target_changed_after_observation"))
    return residuals


def target_validity_check(target: Mapping[str, Any]) -> dict[str, Any]:
    target_id = str(target.get("target_id") or "target")
    required = (
        "capability_basis",
        "target_set",
        "mission_law",
        "generated_law",
        "externality_law",
        "hazard_envelope",
        "authority_envelope",
        "capability_envelope",
        "viability_set",
        "raw_net_capital_floor",
        "horizon",
        "target_validity_certificate_ref",
        "baseline_upper_envelope_ref",
    )
    residuals = _required_residuals("target", target_id, target, required)
    if target.get("observed_outcome_ref") and not target.get(
        "target_set_locked_before_observation"
    ):
        residuals.append(_report_residual("target", target_id, "target_changed_after_observation"))
    residuals.extend(_target_status_residuals(target_id, target))
    blockers = _blocking_kinds(residuals)
    authority_ok = _status_ok(target.get("authority_envelope"), {"accepted", "approved", "active"})
    hazard_ok = _status_ok(target.get("hazard_envelope"), {"accepted", "approved", "active"})
    opportunity_law_ok = all(
        _status_ok(target.get(field), {"accepted", "approved", "fresh", "active"})
        for field in ("mission_law", "generated_law", "externality_law")
    )
    viability_ok = _status_ok(target.get("viability_set"), {"accepted", "approved", "active"})
    return {
        "authority_ok": authority_ok,
        "blockers": blockers,
        "hazard_ok": hazard_ok,
        "non_claims": [*NON_CLAIMS, "target_validity_is_protocol_relative"],
        "ok": not blockers,
        "opportunity_law_ok": opportunity_law_ok,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.target_validity_certificate.v1",
        "settled": False,
        "target_id": target_id,
        "target_validity_ok": not blockers,
        "viability_ok": viability_ok,
    }


def baseline_envelope_check(baseline: Mapping[str, Any]) -> dict[str, Any]:
    baseline_id = str(baseline.get("baseline_id") or "baseline")
    required = (
        "baseline_policy_class",
        "resource_envelope",
        "model_toolchain_environment_versions",
        "control_observability",
        "upper_bound_method",
        "confidence_budget",
        "refresh_contract",
        "path_law_refs",
        "envelope_coordinates",
    )
    residuals = _required_residuals("baseline", baseline_id, baseline, required)
    if baseline.get("stale") is True:
        residuals.append(_report_residual("baseline", baseline_id, "baseline_refresh_required"))
    if baseline.get("resource_matched") is False:
        residuals.append(_report_residual("baseline", baseline_id, "baseline_not_resource_matched"))
    control_observability = baseline.get("control_observability")
    if isinstance(control_observability, Mapping) and not _status_ok(
        control_observability, {"accepted", "approved", "active"}
    ):
        residuals.append(
            _report_residual("baseline", baseline_id, "control_observability_not_accepted")
        )
    blockers = _blocking_kinds(residuals)
    return {
        "baseline_envelope_ok": not blockers,
        "baseline_id": baseline_id,
        "blockers": blockers,
        "non_claims": [*NON_CLAIMS, "baseline_upper_envelope_is_not_oracle_truth"],
        "ok": not blockers,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.baseline_upper_envelope_check.v1",
        "settled": False,
    }


def capital_witness_report(packet: Mapping[str, Any]) -> dict[str, Any]:
    packet_id = _packet_id(packet)
    coordinate = str(
        packet.get("coordinate") or _mapping(packet.get("capital")).get("coordinate") or packet_id
    )
    capital_lower = _float_value(packet.get("capital_lower_bound"), packet.get("capital_lower"))
    cost_upper = _float_value(packet.get("cost_upper_bound"), packet.get("cost_upper"))
    hazard_upper = _float_value(
        packet.get("hazard_charge_upper_bound"),
        packet.get("hazard_upper"),
    )
    transport_upper = _float_value(
        packet.get("transport_charge_upper_bound"),
        packet.get("transport_upper"),
    )
    signed_surplus = _float_value(
        packet.get("signed_surplus_lower_bound"),
        capital_lower - cost_upper - hazard_upper - transport_upper,
    )
    value_type = str(packet.get("value_estimand_type") or "proxy_only")
    residuals = _required_residuals(
        "capital",
        packet_id,
        packet,
        ("coordinate", "baseline_ref", "transport_ref", "finality_ref"),
    )
    boolean_fields = (
        "mission_valid",
        "transport_valid",
        "finality_valid",
        "hazard_constrained",
        "gauge_compatible",
        "raw_net_solvent",
    )
    for field in boolean_fields:
        if packet.get(field) is not True:
            residuals.append(_report_residual("capital", packet_id, f"{field}_not_verified"))
    if value_type == "proxy_only":
        residuals.append(_report_residual("capital", packet_id, "proxy_only_not_admitted"))
    if signed_surplus <= 0:
        residuals.append(_report_residual("capital", packet_id, "nonpositive_signed_surplus"))
    if packet.get("negative_liquidity") is True:
        residuals.append(_report_residual("capital", packet_id, "negative_liquidity"))
    if packet.get("lifecycle_stale") is True:
        residuals.append(_report_residual("capital", packet_id, "stale_lifecycle"))
    if packet.get("authority_fresh") is False:
        residuals.append(_report_residual("capital", packet_id, "authority_not_fresh"))
    blockers = _blocking_kinds(residuals)
    admitted = not blockers
    return {
        "blockers": blockers,
        "capital_admitted": admitted,
        "capital_lower_bound": capital_lower,
        "coordinate": coordinate,
        "cost_upper_bound": cost_upper,
        "evidence_refs": _list_any(packet.get("evidence_refs")),
        "finality_valid": packet.get("finality_valid") is True,
        "gauge_compatible": packet.get("gauge_compatible") is True,
        "hazard_charge_upper_bound": hazard_upper,
        "hazard_constrained": packet.get("hazard_constrained") is True,
        "mission_valid": packet.get("mission_valid") is True,
        "non_claims": [
            *NON_CLAIMS,
            "accepted_report_does_not_imply_capital_admitted",
            "proxy_only_cannot_increase_safe_capital",
        ],
        "ok": True,
        "packet_refs": _list_any(packet.get("packet_refs") or packet_id),
        "raw_net_solvent": packet.get("raw_net_solvent") is True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.runtime_capital_witness.v1",
        "settled": False,
        "signed_surplus_lower_bound": signed_surplus,
        "transport_charge_upper_bound": transport_upper,
        "transport_valid": packet.get("transport_valid") is True,
        "value_estimand_type": value_type,
        "verifier_refs": _list_any(packet.get("verifier_refs")),
        "witness_id": str(packet.get("witness_id") or f"capital:{_short_hash(packet)}"),
    }


def deployment_admissibility_report(
    packet: Mapping[str, Any],
    *,
    profile: str | Mapping[str, Any] = "development",
) -> dict[str, Any]:
    packet_id = _packet_id(packet)
    residuals = _required_residuals(
        "deployment",
        packet_id,
        packet,
        ("guard_certificate", "current_certificate", "authority_envelope"),
    )
    if not _status_ok(_mapping(packet.get("guard_certificate")), {"accepted", "fresh", "approved"}):
        residuals.append(
            _report_residual("deployment", packet_id, "guard_certificate_not_accepted")
        )
    if not _certificate_fresh(packet.get("current_certificate"), datetime.now(UTC)):
        residuals.append(_report_residual("deployment", packet_id, "current_certificate_not_fresh"))
    if not _status_ok(_mapping(packet.get("authority_envelope")), {"approved", "active"}):
        residuals.append(_report_residual("deployment", packet_id, "authority_not_approved"))
    blockers = _blocking_kinds(residuals)
    return {
        "admissible": not blockers,
        "blockers": blockers,
        "non_claims": [*NON_CLAIMS, "deployment_admissible_is_not_provider_dispatch"],
        "ok": True,
        "packet_id": packet_id,
        "profile": _profile_settings(profile)["profile"],
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.deployment_admissibility_report.v1",
        "settled": False,
    }


_PHASE_CHARGE_FIELDS = (
    "transport_error_upper_bound",
    "calibration_error_upper_bound",
    "hazard_charge_upper_bound",
    "authority_charge_upper_bound",
    "censoring_charge_upper_bound",
    "competing_stop_charge_upper_bound",
)


def _phase_interval_evidence(
    *,
    target: Mapping[str, Any],
    baseline: Mapping[str, Any],
    margin_delta: float | None,
    certified_candidate: bool,
) -> dict[str, Any]:
    confidence_budget = _first_value(
        target.get("confidence_budget"),
        baseline.get("confidence_budget"),
    )
    baseline_refresh_age = _first_value(
        baseline.get("baseline_refresh_age"),
        baseline.get("refresh_age"),
        baseline.get("age"),
    )
    baseline_stale = bool(
        baseline.get("baseline_stale") is True
        or baseline.get("stale") is True
        or baseline.get("lifecycle_stale") is True
    )
    time_uniform_evidence = bool(
        target.get("time_uniform_evidence") is True or baseline.get("time_uniform_evidence") is True
    )
    subject = target.get("target_id") or baseline.get("baseline_id") or "phase"
    residuals: list[dict[str, Any]] = []
    if confidence_budget is None:
        residuals.append(_report_residual("phase-interval", subject, "missing_confidence_budget"))
    if baseline_stale:
        residuals.append(_report_residual("phase-interval", subject, "baseline_stale"))
    if not time_uniform_evidence:
        residuals.append(
            _report_residual("phase-interval", subject, "missing_time_uniform_evidence")
        )

    declared_missing_charge = _optional_float(
        _first_value(
            target.get("declared_missing_charge_upper_bound"),
            baseline.get("declared_missing_charge_upper_bound"),
        )
    )
    charge_upper_bounds: dict[str, float] = {}
    for field in _PHASE_CHARGE_FIELDS:
        value = _optional_float(_first_value(target.get(field), baseline.get(field)))
        if value is None and declared_missing_charge is not None:
            value = declared_missing_charge
        if value is None:
            residuals.append(_report_residual("phase-interval", subject, f"missing_{field}"))
            continue
        charge_upper_bounds[field] = value
    total_charge = sum(charge_upper_bounds.values())
    margin_interval = (
        [margin_delta - total_charge, margin_delta] if margin_delta is not None else None
    )
    interval_candidate = bool(
        certified_candidate
        and margin_interval is not None
        and margin_interval[0] > 0
        and confidence_budget is not None
        and time_uniform_evidence
        and not baseline_stale
        and not _blocking_kinds(residuals)
    )
    if interval_candidate:
        evidence_status = "interval_candidate"
    elif certified_candidate:
        evidence_status = "point_candidate_interval_blocked"
    elif residuals:
        evidence_status = "interval_diagnostic"
    else:
        evidence_status = "diagnostic"
    return {
        "acceleration_interval": margin_interval,
        "baseline_refresh_age": baseline_refresh_age,
        "baseline_stale": baseline_stale,
        "certified_acceleration_interval_candidate": interval_candidate,
        "charge_upper_bounds": dict(sorted(charge_upper_bounds.items())),
        "confidence_budget": confidence_budget,
        "dynamic_regime_surface_ref": _first_value(
            target.get("dynamic_regime_surface_ref"),
            baseline.get("dynamic_regime_surface_ref"),
        ),
        "evidence_status": evidence_status,
        "interval_residuals": sorted(residuals, key=lambda item: item["kind"]),
        "margin_interval": margin_interval,
        "stopped_evidence_sheaf_ref": _first_value(
            target.get("stopped_evidence_sheaf_ref"),
            baseline.get("stopped_evidence_sheaf_ref"),
        ),
        "time_uniform_evidence": time_uniform_evidence,
        "total_charge_upper_bound": total_charge,
    }


def phase_acceleration_report(
    target: Mapping[str, Any],
    baseline: Mapping[str, Any],
    capital_witnesses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    target_report = target_validity_check(target)
    baseline_report = baseline_envelope_check(baseline)
    witnesses = [
        dict(item)
        if str(item.get("schema_version")) == "pic.runtime_capital_witness.v1"
        else capital_witness_report(item)
        for item in capital_witnesses
    ]
    residuals: list[dict[str, Any]] = [
        *[dict(item) for item in target_report["residuals"]],
        *[dict(item) for item in baseline_report["residuals"]],
    ]
    k_alt: dict[str, float] = {}
    for witness in witnesses:
        if witness.get("capital_admitted") is True:
            coord = str(witness.get("coordinate"))
            k_alt[coord] = k_alt.get(coord, 0.0) + _float_value(
                witness.get("signed_surplus_lower_bound")
            )
        elif witness.get("value_estimand_type") == "proxy_only":
            residuals.append(
                _report_residual("phase", witness.get("witness_id"), "proxy_only_non_contributing")
            )
    k_baseline = _baseline_coordinates(baseline)
    thresholds = _target_thresholds(target)
    if not k_alt:
        residuals.append(
            _report_residual(
                "phase",
                target.get("target_id") or "target",
                "runtime_capital_witness_required",
            )
        )
    raw_net_floor = _float_value(target.get("raw_net_capital_floor"))
    if sum(k_alt.values()) < raw_net_floor:
        residuals.append(
            _report_residual(
                "phase",
                target.get("target_id") or "target",
                "raw_net_capital_floor_not_met",
            )
        )
    if not thresholds:
        residuals.append(
            _report_residual(
                "phase",
                target.get("target_id") or "target",
                "target_set_evaluator_required",
            )
        )
    margin_values = [
        k_alt.get(coord, 0.0) - k_baseline.get(coord, 0.0)
        for coord in sorted(set(k_alt) | set(k_baseline) | set(thresholds))
    ]
    margin_delta = min(margin_values) if margin_values else None
    tau_alt = {
        coord: 0 if k_alt.get(coord, 0.0) >= threshold else None
        for coord, threshold in sorted(thresholds.items())
    }
    tau_baseline = {
        coord: 0 if k_baseline.get(coord, 0.0) >= threshold else None
        for coord, threshold in sorted(thresholds.items())
    }
    blockers = _blocking_kinds(residuals)
    certified_candidate = (
        bool(thresholds)
        and target_report["ok"]
        and baseline_report["ok"]
        and not blockers
        and margin_delta is not None
        and margin_delta > 0
        and any(value == 0 for value in tau_alt.values())
        and not all(value == 0 for value in tau_baseline.values())
    )
    report_ok = bool(target_report["ok"] and baseline_report["ok"] and not blockers)
    interval_evidence = _phase_interval_evidence(
        target=target,
        baseline=baseline,
        margin_delta=margin_delta,
        certified_candidate=certified_candidate,
    )
    return {
        "acceleration_interval": interval_evidence["acceleration_interval"],
        "authority_ok": target_report["authority_ok"],
        "baseline_envelope_ok": baseline_report["ok"],
        "baseline_refresh_age": interval_evidence["baseline_refresh_age"],
        "baseline_stale": interval_evidence["baseline_stale"],
        "blockers": blockers,
        "capital_witnesses": witnesses,
        "certified_acceleration_candidate": certified_candidate,
        "certified_acceleration_interval_candidate": interval_evidence[
            "certified_acceleration_interval_candidate"
        ],
        "charge_upper_bounds": interval_evidence["charge_upper_bounds"],
        "confidence_budget": interval_evidence["confidence_budget"],
        "dynamic_regime_surface_ref": interval_evidence["dynamic_regime_surface_ref"],
        "evidence_status": interval_evidence["evidence_status"],
        "finality_ok": all(item.get("finality_valid") is True for item in witnesses)
        if witnesses
        else False,
        "hazard_ok": target_report["hazard_ok"],
        "horizon": target.get("horizon"),
        "interval_residuals": interval_evidence["interval_residuals"],
        "k_alt_lower": dict(sorted(k_alt.items())),
        "k_baseline_upper": dict(sorted(k_baseline.items())),
        "margin_interval": interval_evidence["margin_interval"],
        "margin_delta": margin_delta,
        "non_claims": [
            *NON_CLAIMS,
            "certified_acceleration_candidate_is_not_real_asi_proof",
            "target_baseline_and_witnesses_are_protocol_relative",
        ],
        "ok": report_ok,
        "opportunity_law_ok": target_report["opportunity_law_ok"],
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.phase_acceleration_report.v1",
        "settled": False,
        "stopped_evidence_sheaf_ref": interval_evidence["stopped_evidence_sheaf_ref"],
        "target_id": target.get("target_id"),
        "target_validity_ok": target_report["ok"],
        "tau_alt": tau_alt,
        "tau_baseline_upper": tau_baseline,
        "time_uniform_evidence": interval_evidence["time_uniform_evidence"],
        "total_charge_upper_bound": interval_evidence["total_charge_upper_bound"],
        "transport_error_upper_bound": interval_evidence["charge_upper_bounds"].get(
            "transport_error_upper_bound"
        ),
        "viability_ok": target_report["viability_ok"],
    }


def activation_construction_report(state_or_graph: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state_or_graph.get("state_id") or state_or_graph.get("graph_id") or "state")
    configs = _records_any(
        state_or_graph.get("configurations")
        or state_or_graph.get("states")
        or state_or_graph.get("nodes")
    )
    residuals: list[dict[str, Any]] = []
    if not configs:
        residuals.append(_report_residual("ecpt", state_id, "finite_configuration_set_required"))
    if len(configs) > 64 and not state_or_graph.get("factor_graph"):
        residuals.append(_report_residual("ecpt", state_id, "factor_graph_required"))
    if state_or_graph.get("sampler_mode") and not state_or_graph.get("sample_ledger"):
        residuals.append(_report_residual("ecpt", state_id, "sampler_ledger_required"))
    utilities = [
        _float_value(cfg.get("gain"))
        - _float_value(cfg.get("burden"))
        - _float_value(cfg.get("debt"))
        - _float_value(cfg.get("queue_cost"))
        - _float_value(cfg.get("capacity_price"))
        - _float_value(cfg.get("incompatibility"))
        + _float_value(cfg.get("acceleration_drive"))
        for cfg in configs
    ]
    weights = [max(0.0, utility) + 1.0 for utility in utilities]
    total = sum(weights) or 1.0
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "activation_probabilities": [
            {
                "configuration_id": str(configs[index].get("configuration_id") or index),
                "probability": round(weight / total, 12),
                "utility": utilities[index],
            }
            for index, weight in enumerate(weights)
        ],
        "blockers": blockers,
        "certified_intervals": bool(state_or_graph.get("error_ledger")),
        "non_claims": [*NON_CLAIMS, "no_global_gibbs_claim_without_certificate"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.activation_construction_certificate.v1",
        "settled": False,
        "state_id": state_id,
    }


def phase_response_control_step(
    state: Mapping[str, Any],
    control: Mapping[str, Any],
) -> dict[str, Any]:
    report = activation_construction_report(state)
    control_id = str(control.get("control_id") or control.get("action_id") or "control")
    residuals = [dict(item) for item in report["residuals"]]
    if not control.get("control_surface"):
        residuals.append(_report_residual("ecpt-control", control_id, "control_surface_required"))
    utility = (
        _float_value(control.get("gain"))
        - _float_value(control.get("burden"))
        - _float_value(control.get("debt"))
        - _float_value(control.get("queue_cost"))
        - _float_value(control.get("capacity_price"))
        - _float_value(control.get("incompatibility"))
        + _float_value(control.get("acceleration_drive"))
    )
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "control_id": control_id,
        "non_claims": [*NON_CLAIMS, "phase_response_step_is_advisory"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.phase_response_control_step.v1",
        "settled": False,
        "utility_interval": [utility, utility]
        if not state.get("error_ledger")
        else [utility - 1, utility + 1],
    }


def path_law_response_policy_report(trajectory: Mapping[str, Any]) -> dict[str, Any]:
    trajectory_id = str(trajectory.get("trajectory_id") or "trajectory")
    residuals = _required_residuals(
        "ecpt-policy",
        trajectory_id,
        trajectory,
        ("path_law_refs", "response_policy", "control_surface"),
    )
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "non_claims": [*NON_CLAIMS, "response_policy_is_not_execution_authority"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.path_law_response_policy.v1",
        "settled": False,
        "trajectory_id": trajectory_id,
    }


def sqot_protocol_integrity_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("protocol_id") or state.get("state_id") or "protocol")
    residuals = _required_residuals(
        "sqot-protocol",
        state_id,
        state,
        ("mandatory_obligations", "checker_thresholds", "audit_fuel", "diagnostic_reserve"),
    )
    if state.get("hidden_protocol_mutation") or state.get("protocol_mutation_edges"):
        residuals.append(_report_residual("sqot-protocol", state_id, "hidden_protocol_mutation"))
    if not state.get("root_checker_integrity"):
        residuals.append(
            _report_residual("sqot-protocol", state_id, "root_checker_integrity_missing")
        )
    if state.get("semantic_egress_status") not in {"accepted", "closed", "not_applicable"}:
        residuals.append(_report_residual("sqot-protocol", state_id, "semantic_egress_unresolved"))
    if state.get("verification_cost_status") == "over_band":
        residuals.append(_report_residual("sqot-protocol", state_id, "verification_cost_over_band"))
    if state.get("mechanism_compatibility_status") in {None, "", "missing"}:
        residuals.append(_report_residual("sqot-protocol", state_id, "mechanism_witness_missing"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "audit_fuel": state.get("audit_fuel"),
        "blockers": blockers,
        "checker_thresholds": state.get("checker_thresholds"),
        "diagnostic_reserve": state.get("diagnostic_reserve"),
        "mandatory_obligations": state.get("mandatory_obligations"),
        "mechanism_compatibility_status": state.get("mechanism_compatibility_status"),
        "meta_vulnerability": state.get("meta_vulnerability"),
        "non_claims": [*NON_CLAIMS, "single_scalar_cannot_certify_sqot_safety"],
        "ok": True,
        "protocol_mutation_edges": state.get("protocol_mutation_edges", []),
        "protocol_state_hash": _digest(state),
        "queue_morphism_status": state.get("queue_morphism_status"),
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "root_checker_integrity": state.get("root_checker_integrity"),
        "schema_version": "pic.sqot_protocol_integrity_report.v1",
        "semantic_egress_status": state.get("semantic_egress_status"),
        "settled": False,
        "verification_cost_status": state.get("verification_cost_status"),
    }


def sqot_resource_exchange_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("exchange_id") or state.get("state_id") or "resource-exchange")
    conversions = _records_any(state.get("conversions") or state.get("resource_conversions"))
    residuals: list[dict[str, Any]] = []
    if not conversions:
        residuals.append(
            _report_residual("sqot-exchange", state_id, "resource_conversion_required")
        )
    for conversion in conversions:
        subject = conversion.get("conversion_id") or state_id
        if not conversion.get("from") or not conversion.get("to"):
            residuals.append(_report_residual("sqot-exchange", subject, "unknown_conversion"))
        if conversion.get("rate") in (None, "") or conversion.get("loss") in (None, ""):
            residuals.append(
                _report_residual("sqot-exchange", subject, "conversion_rate_loss_required")
            )
        if _float_value(conversion.get("meta_occupation_charge")) <= 0:
            residuals.append(
                _report_residual("sqot-exchange", subject, "meta_occupation_charge_required")
            )
        if conversion.get("arbitrage_obstruction") is True:
            residuals.append(
                _report_residual("sqot-exchange", subject, "exchange_arbitrage_obstruction")
            )
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "conversions": conversions,
        "non_claims": [*NON_CLAIMS, "local_resource_safety_does_not_imply_cross_modal_safety"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.sqot_resource_exchange_report.v1",
        "settled": False,
    }


def probe_stop_report(probe_tree: Mapping[str, Any]) -> dict[str, Any]:
    probe_id = str(probe_tree.get("probe_id") or "probe")
    reserve = _float_value(probe_tree.get("diagnostic_reserve"), 0)
    cost = _float_value(probe_tree.get("probe_cost"), probe_tree.get("cost"))
    meta_band = _float_value(probe_tree.get("meta_occupation_band"), 1)
    meta_charge = _float_value(probe_tree.get("meta_occupation_charge"), 0)
    residuals: list[dict[str, Any]] = []
    if cost > reserve:
        residuals.append(_report_residual("probe", probe_id, "probe_cost_exceeds_reserve"))
    if meta_charge > meta_band:
        residuals.append(_report_residual("probe", probe_id, "meta_occupation_band_exceeded"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "no_action_certificate": bool(blockers),
        "non_claims": [*NON_CLAIMS, "probe_plan_is_not_provider_execution"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.probe_stop_report.v1",
        "settled": False,
    }


def bit_mec_frontier_report(certificates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for index, certificate in enumerate(certificates):
        cert_id = str(certificate.get("certificate_id") or f"certificate:{index}")
        if not certificate.get("finite_witness"):
            residuals.append(_report_residual("bit-mec", cert_id, "finite_witness_required"))
            continue
        if not certificate.get("unit_ledger"):
            residuals.append(_report_residual("bit-mec", cert_id, "unit_ledger_required"))
            continue
        accepted.append(dict(certificate))
    frontier = _pareto_frontier(accepted)
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "frontier": frontier,
        "non_claims": [*NON_CLAIMS, "mec_frontier_reports_only_finite_witnesses"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.bit_mec_frontier_report.v1",
        "settled": False,
    }


def bit_certificate_compiler_report(certificates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    frontier = bit_mec_frontier_report(certificates)
    return {
        "accepted": frontier["accepted"],
        "blockers": frontier["blockers"],
        "compiled_certificate_count": len(frontier["frontier"]),
        "non_claims": [*NON_CLAIMS, "compiler_report_does_not_promote_diagnostic_clauses"],
        "ok": True,
        "residuals": frontier["residuals"],
        "schema_version": "pic.bit_certificate_compiler_report.v1",
        "settled": False,
    }


def bit_unit_compatibility_report(certificates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    units = {
        json.dumps(certificate.get("unit_ledger"), sort_keys=True, default=str)
        for certificate in certificates
        if certificate.get("unit_ledger") is not None
    }
    residuals = []
    if len(units) > 1:
        residuals.append(_report_residual("bit-unit", "unit-ledger", "unit_mixing_blocked"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "non_claims": [*NON_CLAIMS, "unit_compatibility_is_coordinate_local"],
        "ok": True,
        "residuals": residuals,
        "schema_version": "pic.bit_unit_compatibility_report.v1",
        "settled": False,
    }


def cegar_simulation_barrier_report(barrier: Mapping[str, Any]) -> dict[str, Any]:
    barrier_id = str(barrier.get("barrier_id") or "barrier")
    residuals: list[dict[str, Any]] = []
    if not (barrier.get("finite_transition_table") or barrier.get("interval_table")):
        residuals.append(_report_residual("cegar", barrier_id, "finite_transition_table_required"))
    if not (barrier.get("simulation_contraction") or barrier.get("refinement_record")):
        residuals.append(_report_residual("cegar", barrier_id, "refinement_record_required"))
    if barrier.get("uncovered_counterexamples"):
        residuals.append(_report_residual("cegar", barrier_id, "uncovered_counterexample"))
    if not barrier.get("bad_state_bound_certified"):
        residuals.append(_report_residual("cegar", barrier_id, "bad_state_bound_uncertified"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "non_claims": [*NON_CLAIMS, "simulation_barrier_is_not_real_physical_outcome_proof"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.cegar_simulation_barrier_report.v1",
        "settled": False,
    }


def dynamic_regime_acceleration_report(surface: Mapping[str, Any]) -> dict[str, Any]:
    surface_id = str(surface.get("surface_id") or "surface")
    residuals: list[dict[str, Any]] = []
    if surface.get("dynamic_baseline_resource_matched") is not True:
        residuals.append(
            _report_residual("dynamic", surface_id, "dynamic_baseline_not_resource_matched")
        )
    if _float_value(surface.get("positivity_floor")) <= 0:
        residuals.append(_report_residual("dynamic", surface_id, "positivity_floor_required"))
    for key in ("censoring_charge", "competing_stop_charge", "truncation_charge"):
        if surface.get(key) in (None, ""):
            residuals.append(_report_residual("dynamic", surface_id, f"{key}_required"))
    arrival_gain_lower = _float_value(surface.get("arrival_gain_lower_bound"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "arrival_gain_lower_bound": arrival_gain_lower if not blockers else None,
        "blockers": blockers,
        "non_claims": [*NON_CLAIMS, "arrival_gain_is_local_to_declared_risk_set_convention"],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.dynamic_regime_acceleration_report.v1",
        "settled": False,
    }


def token_extraction_pipeline_report(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Emit a finite ALT trace-to-token pipeline report without executing a token."""

    trace_id = str(trace.get("trace_id") or trace.get("id") or _short_hash(trace))
    residuals = _required_residuals(
        "token-pipeline",
        trace_id,
        trace,
        ["trace_id", "steps", "provenance", "task_context"],
    )
    steps = _records_any(trace.get("steps") or trace.get("events"))
    if not steps:
        residuals.append(_report_residual("token-pipeline", trace_id, "trace_steps_required"))
    if not trace.get("instrumentation_contract_ref") and not trace.get("instrumentation_contract"):
        residuals.append(
            _report_residual("token-pipeline", trace_id, "instrumentation_contract_required")
        )
    stage_names = [
        "segmentation",
        "candidate_mining",
        "canonicalization",
        "ablation_design",
        "leakage_check",
        "dependency_graph",
        "minimal_interface",
        "verifier_binding",
        "packet_proposal",
    ]
    blockers = _blocking_kinds(residuals)
    candidate_id = f"token-candidate:{_short_hash([trace_id, steps])}"
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "ccr_tasks": [
            _ccr_task(
                kind="alt_capital_check",
                title="Check extracted token candidate",
                objective=(
                    "Route the candidate token through admissibility, leakage, verifier, "
                    "and cost checks before any capital admission."
                ),
                source_id=candidate_id,
                profile="development",
                priority=70,
                role="verifier",
                residual_inputs=blockers,
                candidate_only=True,
            )
        ],
        "candidate_token": {
            "candidate_only": True,
            "content_hash": _digest(trace),
            "token_id": candidate_id,
            "trace_id": trace_id,
        },
        "non_claims": [
            *NON_CLAIMS,
            "token_extraction_is_not_token_execution",
            "token_extraction_is_not_settlement",
        ],
        "ok": True,
        "pipeline_stages": [
            {"name": name, "status": "candidate" if not blockers else "residual"}
            for name in stage_names
        ],
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.token_extraction_pipeline_report.v1",
        "settled": False,
        "trace_id": trace_id,
    }


def token_admissibility_report(token: Mapping[str, Any]) -> dict[str, Any]:
    """Check ALT token admissibility clauses as a JSON-level public report."""

    token_id = str(token.get("token_id") or token.get("id") or _short_hash(token))
    clauses = {
        "authority_capability_envelope": bool(
            token.get("authority_envelope")
            or token.get("authority_refs")
            or token.get("capability_envelope_refs")
        ),
        "counterfactual_deployment_contrast": bool(
            token.get("counterfactual_contrast") or token.get("deployment_contrast")
        ),
        "cost_risk_accounting": bool(token.get("cost_ledger") or token.get("risk_ledger")),
        "deprecation_resurrection_conditions": bool(
            token.get("deprecation_conditions") or token.get("resurrection_conditions")
        ),
        "dependency_closure": bool(
            token.get("dependency_graph") or token.get("dependency_closure_ref")
        ),
        "expiry_lifecycle": bool(token.get("expiry") or token.get("lifecycle")),
        "guard_failure_contract": bool(token.get("guard") or token.get("failure_contract")),
        "leakage_exclusion": bool(
            token.get("leakage_audit_ref") or token.get("leakage_exclusion") is True
        ),
        "mechanism_mediated_reuse": bool(token.get("mechanism") or token.get("mechanism_ref")),
        "provenance_origin": bool(
            token.get("trace_id") or token.get("provenance") or token.get("origin")
        ),
        "reusable_handle": bool(token.get("token_id") or token.get("handle")),
        "transport_scope": bool(token.get("transport_scope") or token.get("scope")),
        "verifier_binding": bool(token.get("verifier_binding") or token.get("verifier_ref")),
    }
    residuals = [
        _report_residual("token-admissibility", token_id, f"{clause}_required")
        for clause, ok in clauses.items()
        if not ok
    ]
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "admissibility_clauses": dict(sorted(clauses.items())),
        "blockers": blockers,
        "capital_admitted": False,
        "non_claims": [
            *NON_CLAIMS,
            "token_admissibility_is_not_capital_admission",
            "useful_intervention_is_not_automatically_a_token",
        ],
        "ok": True,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.token_admissibility_report.v1",
        "settled": False,
        "token_id": token_id,
    }


def token_lineage_report(token: Mapping[str, Any]) -> dict[str, Any]:
    token_id = str(token.get("token_id") or token.get("id") or _short_hash(token))
    parents = _list_field(token, "parents") or _list_field(token, "lineage_refs")
    residuals = []
    if not parents and not token.get("trace_id"):
        residuals.append(_report_residual("token-lineage", token_id, "lineage_origin_required"))
    if token.get("lineage_closed") is not True:
        residuals.append(_report_residual("token-lineage", token_id, "lineage_closure_required"))
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "content_hash": _digest(token),
        "dependency_aware_hash": _digest([token, sorted(parents)]),
        "lineage_refs": sorted(parents),
        "non_claims": [*NON_CLAIMS, "lineage_report_is_not_settlement"],
        "normalized_claim_hash": _digest(_normalized_claim(token)),
        "ok": True,
        "residuals": residuals,
        "schema_version": "pic.token_lineage_report.v1",
        "settled": False,
        "token_id": token_id,
    }


def token_dedup_report(tokens: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[str]] = {}
    near_duplicates: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        token_id = str(token.get("token_id") or token.get("id") or f"token:{index}")
        claim_hash = _digest(_normalized_claim(token))
        groups.setdefault(claim_hash, []).append(token_id)
    token_list = list(tokens)
    for left_index, left in enumerate(token_list):
        for right_index in range(left_index + 1, len(token_list)):
            right = token_list[right_index]
            left_text = _normalized_claim(left)
            right_text = _normalized_claim(right)
            similarity = _jaccard_similarity(left_text, right_text)
            if 0.82 <= similarity < 1.0:
                near_duplicates.append(
                    {
                        "left": str(left.get("token_id") or f"token:{left_index}"),
                        "right": str(right.get("token_id") or f"token:{right_index}"),
                        "similarity": similarity,
                    }
                )
    exact_aliases = [
        {"canonical_id": ids[0], "alias_ids": ids[1:]} for ids in groups.values() if len(ids) > 1
    ]
    residuals = [
        _report_residual(
            "token-dedup",
            f"{item['left']}:{item['right']}",
            "near_duplicate_requires_review",
            blocking=False,
        )
        for item in near_duplicates
    ]
    return {
        "accepted": True,
        "alias_ledger": exact_aliases,
        "blockers": [],
        "canonical_representative_count": len(groups),
        "duplicate_mass_report": {
            "duplicate_mass_count": sum(len(item["alias_ids"]) for item in exact_aliases),
            "exact_duplicate_count": len(exact_aliases),
            "near_duplicate_candidate_count": len(near_duplicates),
        },
        "near_duplicate_candidates": near_duplicates,
        "non_claims": [
            *NON_CLAIMS,
            "string_similarity_is_not_semantic_identity",
            "duplicate_mass_cannot_increase_support",
        ],
        "ok": True,
        "residuals": residuals,
        "schema_version": "pic.token_dedup_report.v1",
        "settled": False,
    }


def token_interface_standard_report(
    token: Mapping[str, Any],
    standard: Mapping[str, Any],
) -> dict[str, Any]:
    token_id = str(token.get("token_id") or token.get("id") or _short_hash(token))
    required = _list_field(standard, "required_fields") or [
        "token_id",
        "interface",
        "verifier_binding",
    ]
    residuals = [
        _report_residual("token-interface", token_id, f"missing_{field}")
        for field in required
        if token.get(field) in (None, "", [], {})
    ]
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.token_interface_standard_report.v1",
        not blockers,
        residuals,
        "token_interface_check_is_not_execution_authority",
        token_id=token_id,
        required_fields=sorted(required),
    )


def trace_instrumentation_contract_report(
    trace: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    trace_id = str(trace.get("trace_id") or trace.get("id") or _short_hash(trace))
    required = _list_field(contract, "required_fields") or ["trace_id", "events", "provenance"]
    residuals = [
        _report_residual("trace-instrumentation", trace_id, f"missing_{field}")
        for field in required
        if trace.get(field) in (None, "", [], {})
    ]
    if contract.get("requires_clock") and not trace.get("clock"):
        residuals.append(_report_residual("trace-instrumentation", trace_id, "clock_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.trace_instrumentation_contract_report.v1",
        not blockers,
        residuals,
        "instrumentation_check_is_not_trace_truth",
        required_fields=sorted(required),
        trace_id=trace_id,
    )


def trace_sufficiency_report(
    trace: Mapping[str, Any], estimand: Mapping[str, Any]
) -> dict[str, Any]:
    trace_id = str(trace.get("trace_id") or trace.get("id") or _short_hash(trace))
    residuals = _required_residuals(
        "trace-sufficiency",
        trace_id,
        estimand,
        ["estimand_id", "target_quantity", "identification_assumptions"],
    )
    if not (trace.get("events") or trace.get("steps")):
        residuals.append(_report_residual("trace-sufficiency", trace_id, "trace_events_required"))
    if not estimand.get("negative_controls") and not estimand.get("support_ledger"):
        residuals.append(
            _report_residual("trace-sufficiency", trace_id, "support_or_negative_controls_required")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.trace_sufficiency_report.v1",
        not blockers,
        residuals,
        "trace_sufficiency_is_estimand_relative",
        trace_id=trace_id,
    )


def mechanism_ablation_report(
    token: Mapping[str, Any], ablation: Mapping[str, Any]
) -> dict[str, Any]:
    token_id = str(token.get("token_id") or token.get("id") or _short_hash(token))
    residuals = _required_residuals(
        "mechanism-ablation",
        token_id,
        ablation,
        ["control_condition", "treatment_condition", "metric", "verifier_binding"],
    )
    for key in ("confound_charge", "proxy_charge", "transport_charge", "surface_charge"):
        if ablation.get(key) in (None, ""):
            residuals.append(_report_residual("mechanism-ablation", token_id, f"{key}_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.mechanism_ablation_report.v1",
        not blockers,
        residuals,
        "mechanism_ablation_is_not_mechanism_truth",
        token_id=token_id,
        total_charge_upper_bound=sum(
            _float_value(ablation.get(key))
            for key in ("confound_charge", "proxy_charge", "transport_charge", "surface_charge")
        ),
    )


def leakage_audit_report(token: Mapping[str, Any]) -> dict[str, Any]:
    token_id = str(token.get("token_id") or token.get("id") or _short_hash(token))
    residuals = []
    text = json.dumps(token, sort_keys=True, default=str).lower()
    if any(marker in text for marker in ("answer_key", "heldout_answer", "benchmark_solution")):
        residuals.append(_report_residual("leakage-audit", token_id, "benchmark_answer_leakage"))
    if token.get("leakage_exclusion") is not True and not token.get("leakage_audit_ref"):
        residuals.append(_report_residual("leakage-audit", token_id, "leakage_exclusion_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.leakage_audit_report.v1",
        not blockers,
        residuals,
        "leakage_audit_is_finite_and_scope_limited",
        token_id=token_id,
    )


def mission_validity_report(packet: Mapping[str, Any]) -> dict[str, Any]:
    packet_id = _packet_id(packet)
    residuals = _required_residuals(
        "mission-validity",
        packet_id,
        packet,
        ["mission_law", "construct_evidence", "target_scope", "hazard_ledger"],
    )
    if packet.get("generated_law_gain") and not packet.get("mission_bridge"):
        residuals.append(
            _report_residual("mission-validity", packet_id, "generated_law_bridge_required")
        )
    if packet.get("externality_hazards") and not packet.get("externality_hazard_ledger"):
        residuals.append(
            _report_residual("mission-validity", packet_id, "externality_hazard_ledger_required")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.mission_validity_certificate.v1",
        not blockers,
        residuals,
        "mission_validity_is_protocol_relative",
        packet_id=packet_id,
    )


def opportunity_measure_report(target: Mapping[str, Any]) -> dict[str, Any]:
    target_id = str(target.get("target_id") or "target")
    residuals = _required_residuals(
        "opportunity-law",
        target_id,
        target,
        ["mission_law", "population", "sampling_frame", "cost_model"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.opportunity_measure_constructor.v1",
        not blockers,
        residuals,
        "opportunity_measure_is_not_oracle_truth",
        target_id=target_id,
    )


def transport_certificate_report(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    certificate_id = str(certificate.get("certificate_id") or _short_hash(certificate))
    residuals = _required_residuals(
        "transport",
        certificate_id,
        certificate,
        ["source_scope", "target_scope", "support_ledger", "density_ratio_bound"],
    )
    if source.get("scope") and target.get("scope") and source.get("scope") == target.get("scope"):
        pass
    elif not certificate.get("bridge_evidence"):
        residuals.append(_report_residual("transport", certificate_id, "bridge_evidence_required"))
    if certificate.get("support_miss") is True:
        residuals.append(_report_residual("transport", certificate_id, "support_miss"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.transport_certificate_report.v1",
        not blockers,
        residuals,
        "source_liquidity_is_not_target_liquidity_without_transport",
        certificate_id=certificate_id,
    )


def construct_validity_report(packet: Mapping[str, Any]) -> dict[str, Any]:
    packet_id = _packet_id(packet)
    residuals = _required_residuals(
        "construct-validity",
        packet_id,
        packet,
        ["construct_definition", "measurement_protocol", "negative_controls"],
    )
    if packet.get("aggregate_benchmark_success") and not packet.get("construct_evidence"):
        residuals.append(
            _report_residual("construct-validity", packet_id, "construct_evidence_required")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.construct_validity_report.v1",
        not blockers,
        residuals,
        "aggregate_success_is_not_construct_validity",
        packet_id=packet_id,
    )


def fcu_check_report(cost: Mapping[str, Any]) -> dict[str, Any]:
    cost_id = str(cost.get("cost_id") or _short_hash(cost))
    residuals = _required_residuals(
        "fcu",
        cost_id,
        cost,
        ["cost_coordinates", "scalarization", "upper_bounds"],
    )
    if cost.get("irreversible_loss_absent") is not True and not cost.get(
        "irreversible_loss_ledger"
    ):
        residuals.append(_report_residual("fcu", cost_id, "irreversible_loss_ledger_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.fcu_exchange_table_report.v1",
        not blockers,
        residuals,
        "missing_cost_coordinate_is_not_zero",
        cost_id=cost_id,
    )


def lifecycle_cost_report(packet: Mapping[str, Any]) -> dict[str, Any]:
    packet_id = _packet_id(packet)
    ledger = _mapping(packet.get("lifecycle_cost_ledger") or packet.get("cost_ledger"))
    residuals = _required_residuals(
        "lifecycle-cost",
        packet_id,
        ledger,
        ["formation", "deployment", "validation", "maintenance", "depreciation"],
    )
    if not packet.get("telemetry_contract_ref") and not packet.get("telemetry_contract"):
        residuals.append(
            _report_residual("lifecycle-cost", packet_id, "telemetry_contract_required")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.lifecycle_cost_ledger_report.v1",
        not blockers,
        residuals,
        "lifecycle_cost_report_is_not_settlement",
        packet_id=packet_id,
    )


def telemetry_check_report(
    telemetry: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    telemetry_id = str(telemetry.get("telemetry_id") or _short_hash(telemetry))
    required = _list_field(contract, "required_fields") or ["events", "clock", "resource_use"]
    residuals = [
        _report_residual("telemetry", telemetry_id, f"missing_{field}")
        for field in required
        if telemetry.get(field) in (None, "", [], {})
    ]
    if telemetry.get("status") == "failed" and not (
        telemetry.get("worst_case_charge") or telemetry.get("claim_suspended")
    ):
        residuals.append(
            _report_residual("telemetry", telemetry_id, "telemetry_failure_charge_required")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.closed_loop_telemetry_report.v1",
        not blockers,
        residuals,
        "telemetry_report_is_not_physical_outcome_proof",
        telemetry_id=telemetry_id,
    )


def dynamic_risk_report(ledger: Mapping[str, Any]) -> dict[str, Any]:
    ledger_id = str(ledger.get("ledger_id") or _short_hash(ledger))
    residuals = _required_residuals(
        "dynamic-risk",
        ledger_id,
        ledger,
        ["risk_coordinates", "update_rule", "hazard_charge_upper_bound"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.dynamic_risk_ledger_report.v1",
        not blockers,
        residuals,
        "dynamic_risk_is_not_status_promotion",
        ledger_id=ledger_id,
    )


def stopped_sheaf_report(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    for index, item in enumerate(evidence):
        subject = item.get("evidence_id") or f"evidence:{index}"
        if item.get("stopped") is not True:
            residuals.append(_report_residual("stopped-sheaf", subject, "stopped_event_required"))
        if not item.get("resource_event"):
            residuals.append(
                _report_residual("stopped-sheaf", subject, "stopped_resource_event_required")
            )
        if not item.get("closure_witness"):
            residuals.append(_report_residual("stopped-sheaf", subject, "closure_witness_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.stopped_evidence_sheaf_report.v1",
        not blockers,
        residuals,
        "stopped_evidence_supports_interval_reports_only_with_declared_witnesses",
        evidence_count=len(evidence),
    )


def confidence_sequence_report(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    for index, item in enumerate(evidence):
        subject = item.get("evidence_id") or f"evidence:{index}"
        if item.get("predictable") is not True:
            residuals.append(
                _report_residual("confidence-sequence", subject, "predictability_witness_required")
            )
        if item.get("alpha") in (None, ""):
            residuals.append(
                _report_residual("confidence-sequence", subject, "alpha_budget_required")
            )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.confidence_sequence_report.v1",
        not blockers,
        residuals,
        "confidence_sequence_is_protocol_relative",
        evidence_count=len(evidence),
    )


def evidence_product_report(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    product = 1.0
    for index, item in enumerate(evidence):
        subject = item.get("evidence_id") or f"evidence:{index}"
        product *= max(_float_value(item.get("e_value"), 1), 0.0)
        if item.get("conditional_witness") is not True:
            residuals.append(
                _report_residual("evidence-product", subject, "conditional_witness_required")
            )
        if item.get("closed_testing_witness") is not True:
            residuals.append(
                _report_residual("evidence-product", subject, "closed_testing_witness_required")
            )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.evidence_product_report.v1",
        not blockers,
        residuals,
        "plain_e_value_product_without_closure_is_residual_only",
        e_value_product=product,
        evidence_count=len(evidence),
    )


def ecpt_quotient_report(
    packets: Sequence[Mapping[str, Any]],
    *,
    profile: str = "development",
) -> dict[str, Any]:
    dedup = token_dedup_report(packets)
    residuals = list(dedup["residuals"])
    if profile not in {"development", "research", "production", "adversarial"}:
        residuals.append(
            _report_residual("ecpt-quotient", profile, "profile_unknown", blocking=False)
        )
    if not any(
        packet.get("held_out_ledger") or packet.get("uniform_class_ledger") for packet in packets
    ):
        residuals.append(
            _report_residual("ecpt-quotient", "packets", "held_out_or_uniform_ledger_required")
        )
    blockers = _blocking_kinds(residuals)
    return {
        "accepted": not blockers,
        "alias_ledger": dedup["alias_ledger"],
        "blockers": blockers,
        "canonical_packet_count": dedup["canonical_representative_count"],
        "duplicate_mass": dedup["duplicate_mass_report"],
        "non_claims": [*NON_CLAIMS, "quotient_identity_is_context_relative"],
        "ok": True,
        "profile": profile,
        "residuals": sorted(residuals, key=lambda item: item["kind"]),
        "schema_version": "pic.split_certified_quotient_report.v1",
        "settled": False,
    }


def boundary_quotient_report(
    quotient: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    quotient_id = str(quotient.get("quotient_id") or _short_hash(quotient))
    residuals = _required_residuals(
        "boundary-quotient",
        quotient_id,
        quotient,
        ["boundary_error_ledger", "coupling_error_ledger", "context", "tolerance"],
    )
    if (
        target.get("target_id")
        and quotient.get("target_id")
        and target.get("target_id") != quotient.get("target_id")
    ):
        residuals.append(
            _report_residual("boundary-quotient", quotient_id, "target_profile_mismatch")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.boundary_aware_quotient_report.v1",
        not blockers,
        residuals,
        "boundary_errors_must_be_subtracted_from_target_claims",
        quotient_id=quotient_id,
    )


def duplicate_inflation_report(packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dedup = token_dedup_report(packets)
    duplicate_count = int(dedup["duplicate_mass_report"]["duplicate_mass_count"])
    residuals = (
        [
            _report_residual(
                "duplicate-inflation", "packets", "duplicate_mass_excluded", blocking=False
            )
        ]
        if duplicate_count
        else []
    )
    return {
        "accepted": True,
        "blockers": [],
        "duplicate_mass_count": duplicate_count,
        "inflated_support_allowed": False,
        "non_claims": [*NON_CLAIMS, "duplicate_representative_mass_cannot_create_support"],
        "ok": True,
        "residuals": residuals,
        "schema_version": "pic.duplicate_inflation_report.v1",
        "settled": False,
    }


def atlas_check_report(atlas: Mapping[str, Any]) -> dict[str, Any]:
    atlas_id = str(atlas.get("atlas_id") or _short_hash(atlas))
    residuals = _required_residuals(
        "atlas",
        atlas_id,
        atlas,
        ["strata", "transition_maps", "boundary_ledger"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.stratified_packet_atlas_report.v1",
        not blockers,
        residuals,
        "atlas_check_is_not_phase_settlement",
        atlas_id=atlas_id,
    )


def activation_cache_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("state_id") or _short_hash(state))
    residuals = _required_residuals(
        "activation-cache",
        state_id,
        state,
        ["activation_mode", "dependency_hash", "invalidation_keys"],
    )
    mode = str(state.get("activation_mode") or "")
    if mode == "sampler" and not state.get("sample_error_ledger"):
        residuals.append(
            _report_residual("activation-cache", state_id, "sample_error_ledger_required")
        )
    if mode == "factorized" and not state.get("factor_graph"):
        residuals.append(_report_residual("activation-cache", state_id, "factor_graph_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.activation_construction_cache_report.v1",
        not blockers,
        residuals,
        "activation_cache_hit_is_not_proof",
        state_id=state_id,
    )


def queue_morphism_report(source: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    morphism_id = _short_hash([source, target])
    residuals: list[dict[str, Any]] = []
    for coordinate in ("diagnostic_reserve", "rollback_priority", "blocking_residuals"):
        if source.get(coordinate) != target.get(coordinate):
            residuals.append(
                _report_residual("queue-morphism", morphism_id, f"{coordinate}_not_preserved")
            )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.queue_morphism_report.v1",
        not blockers,
        residuals,
        "queue_reencoding_is_not_equivalence_without_preservation",
        morphism_id=morphism_id,
    )


def resource_tensor_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("state_id") or _short_hash(state))
    modalities = _mapping(state.get("modalities") or state.get("resource_modalities"))
    residuals = []
    if not modalities:
        residuals.append(
            _report_residual("resource-tensor", state_id, "resource_modalities_required")
        )
    if state.get("unknown_budget_is_zero") is True:
        residuals.append(
            _report_residual("resource-tensor", state_id, "unknown_budget_cannot_be_zero")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.resource_tensor_report.v1",
        not blockers,
        residuals,
        "resource_tensor_is_not_scalar_budget",
        modality_count=len(modalities),
        state_id=state_id,
    )


def exchange_tensor_report(state: Mapping[str, Any]) -> dict[str, Any]:
    base = sqot_resource_exchange_report(state)
    return {**base, "schema_version": "pic.exchange_tensor_report.v1"}


def diagnostic_reserve_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("state_id") or _short_hash(state))
    reserve = _float_value(state.get("diagnostic_reserve"))
    lower = _float_value(state.get("diagnostic_reserve_lower_bound"))
    upper = _float_value(state.get("diagnostic_reserve_upper_bound"), float("inf"))
    residuals = []
    if reserve <= 0:
        residuals.append(
            _report_residual("diagnostic-reserve", state_id, "diagnostic_reserve_required")
        )
    if reserve and lower and reserve < lower:
        residuals.append(
            _report_residual("diagnostic-reserve", state_id, "diagnostic_reserve_below_band")
        )
    if reserve and upper != float("inf") and reserve > upper:
        residuals.append(
            _report_residual(
                "diagnostic-reserve", state_id, "diagnostic_reserve_above_band", blocking=False
            )
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.diagnostic_reserve_report.v1",
        not blockers,
        residuals,
        "diagnostic_reserve_is_finite_and_protocol_relative",
        diagnostic_reserve=reserve,
        state_id=state_id,
    )


def protocol_mutation_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("state_id") or _short_hash(state))
    residuals = []
    if state.get("protocol_mutated") is True and not (
        state.get("non_salience_induced_certificate") or state.get("quarantined")
    ):
        residuals.append(
            _report_residual("protocol-mutation", state_id, "protocol_mutation_not_certified")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.protocol_mutation_report.v1",
        not blockers,
        residuals,
        "protocol_mutation_blocks_acceptance_without_certificate_or_quarantine",
        state_id=state_id,
    )


def checker_cost_report(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id = str(state.get("state_id") or _short_hash(state))
    residuals = _required_residuals(
        "checker-cost",
        state_id,
        state,
        ["checker_cost", "cost_budget", "verification_queue"],
    )
    if _float_value(state.get("checker_cost")) > _float_value(state.get("cost_budget")):
        residuals.append(_report_residual("checker-cost", state_id, "checker_cost_budget_exceeded"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.checker_cost_ledger_report.v1",
        not blockers,
        residuals,
        "checker_cost_is_queue_occupation",
        state_id=state_id,
    )


def trc_observation_window_report(window: Mapping[str, Any]) -> dict[str, Any]:
    window_id = str(window.get("window_id") or _short_hash(window))
    residuals = _required_residuals(
        "observation-window",
        window_id,
        window,
        ["observer", "start", "end", "relative_scope", "verifier"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.observation_window_report.v1",
        not blockers,
        residuals,
        "observation_window_is_relative_not_hidden_physical_truth",
        window_id=window_id,
    )


def trc_observation_consistency_report(window: Mapping[str, Any]) -> dict[str, Any]:
    base = trc_observation_window_report(window)
    residuals = list(base["residuals"])
    if window.get("postcondition_observed") is False:
        residuals.append(
            _report_residual(
                "observation-consistency", base["window_id"], "postcondition_not_observed"
            )
        )
    if window.get("resource_use_observed") is False:
        residuals.append(
            _report_residual(
                "observation-consistency", base["window_id"], "resource_use_not_observed"
            )
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.observation_consistency_report.v1",
        not blockers,
        residuals,
        "observation_consistency_is_not_physical_outcome_proof",
        window_id=base["window_id"],
    )


def trc_resource_flow_report(trace: Mapping[str, Any]) -> dict[str, Any]:
    trace_id = str(trace.get("trace_id") or trace.get("id") or _short_hash(trace))
    flows = _records_any(trace.get("resource_flows") or trace.get("resources"))
    residuals = []
    if not flows:
        residuals.append(
            _report_residual("resource-flow", trace_id, "trace_indexed_resource_flow_required")
        )
    for index, flow in enumerate(flows):
        subject = flow.get("flow_id") or f"{trace_id}:{index}"
        if flow.get("trace_index") in (None, ""):
            residuals.append(_report_residual("resource-flow", subject, "trace_index_required"))
        if flow.get("rollback_compensation_free") is True:
            residuals.append(
                _report_residual("resource-flow", subject, "rollback_compensation_not_free")
            )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.trace_indexed_resource_flow_report.v1",
        not blockers,
        residuals,
        "resource_flow_ledger_is_trace_indexed",
        flow_count=len(flows),
        trace_id=trace_id,
    )


def lifecycle_scheduler_report(certificates: Mapping[str, Any]) -> dict[str, Any]:
    return _scheduler_report(
        certificates,
        "pic.lifecycle_recomputation_scheduler_report.v1",
        "lifecycle",
        "stale_lifecycle_witness_routes_to_diagnostic",
    )


def tolerance_scheduler_report(certificates: Mapping[str, Any]) -> dict[str, Any]:
    return _scheduler_report(
        certificates,
        "pic.tolerance_recomputation_scheduler_report.v1",
        "tolerance",
        "tolerance_charge_cannot_reduce_physical_residual",
    )


def efficiency_archive_report(frontier: Mapping[str, Any]) -> dict[str, Any]:
    frontier_id = str(frontier.get("frontier_id") or _short_hash(frontier))
    residuals = []
    if frontier.get("promotes_risk_provisional") is True:
        residuals.append(
            _report_residual(
                "efficiency-archive", frontier_id, "risk_provisional_promotion_blocked"
            )
        )
    if not (frontier.get("frontier") or frontier.get("certificates")):
        residuals.append(
            _report_residual("efficiency-archive", frontier_id, "frontier_entries_required")
        )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.resource_efficiency_archive_report.v1",
        not blockers,
        residuals,
        "efficiency_archive_cannot_promote_relaxed_or_risk_provisional_status",
        frontier_id=frontier_id,
    )


def unseen_frontier_report(discoveries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    unseen = sum(_float_value(item.get("unseen_mass")) for item in discoveries)
    duplicate = sum(_float_value(item.get("duplicate_mass")) for item in discoveries)
    false_entry = sum(_float_value(item.get("false_entry_bound")) for item in discoveries)
    residuals = []
    if not discoveries:
        residuals.append(_report_residual("unseen-frontier", "discoveries", "discoveries_required"))
    return _simple_report(
        "pic.unseen_frontier_report.v1",
        not _blocking_kinds(residuals),
        residuals,
        "unseen_duplicate_false_and_unawakened_frontiers_are_separate",
        duplicate_frontier_mass=duplicate,
        false_entry_bound=false_entry,
        unseen_frontier_mass=unseen,
    )


def mechanism_cube_report(cube: Mapping[str, Any]) -> dict[str, Any]:
    cube_id = str(cube.get("cube_id") or _short_hash(cube))
    charges = [
        "direct_supply_charge",
        "observation_drift_charge",
        "logging_drift_charge",
        "factorization_error_charge",
        "rank_failure_charge",
        "proxy_bridge_charge",
    ]
    residuals = [
        _report_residual("mechanism-cube", cube_id, f"{charge}_required")
        for charge in charges
        if cube.get(charge) in (None, "")
    ]
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.mechanism_factorized_channel_cube_report.v1",
        not blockers,
        residuals,
        "mechanism_factorization_must_subtract_declared_charges",
        cube_id=cube_id,
        total_charge=sum(_float_value(cube.get(charge)) for charge in charges),
    )


def release_interval_report(program: Mapping[str, Any]) -> dict[str, Any]:
    program_id = str(program.get("program_id") or _short_hash(program))
    residuals = _required_residuals(
        "release-interval",
        program_id,
        program,
        ["unit_ledger", "primal_witness", "dual_witness", "solver_gap"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.exactness_certified_release_interval_report.v1",
        not blockers,
        residuals,
        "release_interval_requires_unit_primal_dual_solver_gap_witnesses",
        program_id=program_id,
    )


def martingale_partition_report(audit: Mapping[str, Any]) -> dict[str, Any]:
    audit_id = str(audit.get("audit_id") or _short_hash(audit))
    residuals = _required_residuals(
        "martingale-partition",
        audit_id,
        audit,
        ["partition", "filtration", "deficiency_bound"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.martingale_partition_deficiency_report.v1",
        not blockers,
        residuals,
        "martingale_partition_deficiency_is_finite_evidence",
        audit_id=audit_id,
    )


def anchor_transfer_report(certificate: Mapping[str, Any]) -> dict[str, Any]:
    certificate_id = str(certificate.get("certificate_id") or _short_hash(certificate))
    residuals = _required_residuals(
        "anchor-transfer",
        certificate_id,
        certificate,
        ["source_anchor", "target_anchor", "cross_validation", "transfer_error_bound"],
    )
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        "pic.cross_validated_anchor_transfer_report.v1",
        not blockers,
        residuals,
        "anchor_transfer_is_not_target_truth",
        certificate_id=certificate_id,
    )


def performance_report(*, fixture: Mapping[str, Any] | None = None) -> dict[str, Any]:
    fixture = fixture or {}
    return {
        "cache_bytes": int(_float_value(fixture.get("cache_bytes"))),
        "cache_entries": int(_float_value(fixture.get("cache_entries"))),
        "capital_witness_index_entries": int(
            _float_value(fixture.get("capital_witness_index_entries"))
        ),
        "cli_startup_ms": 0,
        "duplicate_hash_count": int(_float_value(fixture.get("duplicate_hash_count"))),
        "graph_edges": int(_float_value(fixture.get("graph_edges"))),
        "graph_nodes": int(_float_value(fixture.get("graph_nodes"))),
        "index_rebuild_required": bool(fixture.get("index_rebuild_required", False)),
        "json_read_count": int(_float_value(fixture.get("json_read_count"))),
        "json_write_count": int(_float_value(fixture.get("json_write_count"))),
        "jsonl_lines_processed": int(_float_value(fixture.get("jsonl_lines_processed"))),
        "non_claims": [*NON_CLAIMS, "performance_report_is_local_diagnostic"],
        "ok": True,
        "p50_command_ms": 0,
        "p95_command_ms": 0,
        "p99_command_ms": 0,
        "recommended_speedups": [
            "stream_jsonl",
            "reuse_schema_validators",
            "content_hash_invalidation",
        ],
        "residual_index_entries": int(_float_value(fixture.get("residual_index_entries"))),
        "schema_validator_cache_hits": int(
            _float_value(fixture.get("schema_validator_cache_hits"))
        ),
        "schema_validator_cache_misses": int(
            _float_value(fixture.get("schema_validator_cache_misses"))
        ),
        "schema_version": "pic.performance_report.v1",
        "settled": False,
        "sqlite_query_count": int(_float_value(fixture.get("sqlite_query_count"))),
        "sqlite_write_count": int(_float_value(fixture.get("sqlite_write_count"))),
    }


def performance_bench_report(fixture: Mapping[str, Any]) -> dict[str, Any]:
    report = performance_report(fixture=fixture)
    return {
        **report,
        "bench_fixture_hash": _digest(fixture),
        "local_only": True,
        "network_call_performed": False,
        "provider_executed": False,
        "schema_version": "pic.performance_bench_report.v1",
    }


def cache_status_report() -> dict[str, Any]:
    return {
        "cache_entries": 0,
        "cache_hit_requires_schema_dependency_profile_hash": True,
        "index_rebuild_required": False,
        "non_claims": [*NON_CLAIMS, "cache_hit_is_not_proof"],
        "ok": True,
        "schema_version": "pic.cache_status_report.v1",
        "settled": False,
    }


def cache_rebuild_report() -> dict[str, Any]:
    return {
        **cache_status_report(),
        "mutated_runtime": False,
        "rebuilt": True,
        "schema_version": "pic.cache_rebuild_report.v1",
    }


def cache_invalidation_report(file_data: Mapping[str, Any]) -> dict[str, Any]:
    dependency_hash = _digest(file_data)
    coordinates = sorted(_list_field(file_data, "coordinates"))
    return {
        "affected_coordinates": coordinates,
        "dependency_hash": dependency_hash,
        "dirty_set": coordinates or ["unknown"],
        "non_claims": [*NON_CLAIMS, "cache_invalidation_is_not_status_promotion"],
        "ok": True,
        "schema_version": "pic.cache_invalidation_report.v1",
        "settled": False,
    }


def _baseline_coordinates(baseline: Mapping[str, Any]) -> dict[str, float]:
    raw = baseline.get("envelope_coordinates")
    if isinstance(raw, Mapping):
        return {str(key): _float_value(value) for key, value in raw.items()}
    coords: dict[str, float] = {}
    for item in _records_any(raw):
        coords[str(item.get("coordinate"))] = _float_value(
            item.get("upper_bound"), item.get("value")
        )
    return coords


def _target_thresholds(target: Mapping[str, Any]) -> dict[str, float]:
    target_set = _mapping(target.get("target_set"))
    raw = target_set.get("thresholds") or target_set.get("coordinate_thresholds")
    if isinstance(raw, Mapping):
        return {str(key): _float_value(value) for key, value in raw.items()}
    thresholds: dict[str, float] = {}
    for item in _records_any(raw):
        thresholds[str(item.get("coordinate"))] = _float_value(
            item.get("threshold"), item.get("value")
        )
    return thresholds


def _pareto_frontier(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    frontier: list[dict[str, Any]] = []
    for candidate in items:
        candidate_metrics = _mec_metrics(candidate)
        dominated = False
        for other in items:
            if other is candidate:
                continue
            other_metrics = _mec_metrics(other)
            if all(
                other_metrics[key] <= candidate_metrics[key] for key in candidate_metrics
            ) and any(other_metrics[key] < candidate_metrics[key] for key in candidate_metrics):
                dominated = True
                break
        if not dominated:
            frontier.append(dict(candidate))
    return sorted(
        frontier,
        key=lambda item: str(item.get("certificate_id") or item.get("witness_id") or item),
    )


def _mec_metrics(item: Mapping[str, Any]) -> dict[str, float]:
    return {
        "cost": _float_value(item.get("cost")),
        "friction": _float_value(item.get("friction")),
        "load": _float_value(item.get("load")),
    }


def _simple_report(
    schema_version: str,
    accepted: bool,
    residuals: Sequence[Mapping[str, Any]],
    non_claim: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        **dict(sorted(extra.items())),
        "accepted": accepted,
        "blockers": _blocking_kinds(residuals),
        "non_claims": [*NON_CLAIMS, non_claim],
        "ok": True,
        "residuals": sorted((dict(item) for item in residuals), key=lambda item: str(item["kind"])),
        "schema_version": schema_version,
        "settled": False,
    }


def _normalized_claim(item: Mapping[str, Any]) -> str:
    raw = (
        item.get("claim")
        or item.get("claim_text")
        or item.get("summary")
        or item.get("description")
        or item.get("token_id")
        or item
    )
    text = json.dumps(raw, sort_keys=True, default=str) if not isinstance(raw, str) else raw
    return " ".join(text.casefold().split())


def _jaccard_similarity(left: str, right: str) -> float:
    left_set = {token for token in re.split(r"\W+", left) if token}
    right_set = {token for token in re.split(r"\W+", right) if token}
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _scheduler_report(
    certificates: Mapping[str, Any],
    schema_version: str,
    prefix: str,
    non_claim: str,
) -> dict[str, Any]:
    certificate_rows = _records_any(certificates.get("certificates") or certificates.get("items"))
    residuals: list[dict[str, Any]] = []
    recompute: list[str] = []
    for index, certificate in enumerate(certificate_rows):
        cert_id = str(certificate.get("certificate_id") or f"certificate:{index}")
        if certificate.get("stale") is True or certificate.get("fresh") is False:
            residuals.append(_report_residual(prefix, cert_id, f"{prefix}_recompute_required"))
            recompute.append(cert_id)
        if certificate.get("lower_fidelity") is True and certificate.get("tolerance_charge") in (
            None,
            "",
        ):
            residuals.append(_report_residual(prefix, cert_id, "tolerance_charge_required"))
            recompute.append(cert_id)
    if not certificate_rows:
        residuals.append(_report_residual(prefix, "certificates", "certificates_required"))
    blockers = _blocking_kinds(residuals)
    return _simple_report(
        schema_version,
        not blockers,
        residuals,
        non_claim,
        recompute_certificate_ids=sorted(set(recompute)),
    )


def _optional_float(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _float_value(*values: Any) -> float:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _packet_id(packet: Mapping[str, Any]) -> str:
    return str(
        packet.get("packet_id")
        or packet.get("decision_id")
        or packet.get("token_id")
        or _mapping(packet.get("token")).get("token_id")
        or "alt-packet"
    )


def _digest(value: Any) -> str:
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
    )


def _short_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:16]
