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

    operation_blocker_kinds = _CORE_OPERATION_BLOCKERS | {
        "missing_causal_schedule_block",
        "missing_certificate_lifecycle",
        "missing_hazard_envelope",
    }
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
        "mcp_tool_gate": {
            "ok": not profile.get("requires_mcp_tool")
            or bool(profile.get("mcp_tool_gate_accepted")),
            "required": bool(profile.get("requires_mcp_tool")),
        },
        "a2a_agent_gate": {
            "ok": not profile.get("requires_a2a_agent")
            or bool(profile.get("a2a_agent_gate_accepted")),
            "required": bool(profile.get("requires_a2a_agent")),
        },
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
