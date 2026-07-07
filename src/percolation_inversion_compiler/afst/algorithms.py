"""Deterministic AFST satisfaction-flux algorithms."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from math import isfinite
from typing import Any, TypeVar

from pydantic import BaseModel

from percolation_inversion_compiler.afst.records import (
    ACCEPTED_AUTHORITY_STATUSES,
    AFST_NON_CLAIMS,
    AFSTFluxStabilizationReport,
    AFSTProfilePolicy,
    AuthorityEnvelope,
    BoundedFrictionHandover,
    CandidateFlux,
    CertifiedAbundanceCoordinate,
    ConsentChannel,
    NonMarketLiquidityCertificate,
    RawInputAudit,
    RefusalChannel,
    ResourceBalanceWitness,
    SatisfactionCoordinate,
    SatisfactionDeficit,
    SatisfactionEffectWitness,
    SatisfactionFluxRecord,
    StabilizationBuffer,
    UnitFrame,
    afst_profile_policy,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.status import ClaimStatus

ModelT = TypeVar("ModelT", bound=BaseModel)

_REQUIRED_RECORD_FIELDS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "satisfaction_coordinates": (
        "satisfaction_coordinate",
        (
            "coordinate_id",
            "cell_id",
            "resource_type",
            "value",
            "floor_min",
            "unit",
        ),
        ("coordinate_id", "cell_id"),
    ),
    "abundance_coordinates": (
        "certified_abundance_coordinate",
        (
            "abundance_id",
            "cell_id",
            "resource_type",
            "available_amount",
            "safe_floor",
            "reserve_amount",
            "unit",
            "authority_refs",
            "evidence_refs",
        ),
        ("abundance_id", "cell_id"),
    ),
    "candidate_fluxes": (
        "candidate_flux",
        (
            "flux_id",
            "source_cell_id",
            "target_cell_id",
            "resource_type",
            "amount",
            "unit",
            "loss_upper_bound",
            "liquidity_mode",
        ),
        ("flux_id", "source_cell_id", "target_cell_id"),
    ),
    "authority_envelopes": (
        "authority_envelope",
        ("authority_id", "scope", "action", "resource_type", "status"),
        ("authority_id", "subject"),
    ),
    "consent_channels": (
        "consent_channel",
        ("consent_id", "subject_cell_id", "consent_granted", "scope", "resource_type", "action"),
        ("consent_id", "subject_cell_id"),
    ),
    "refusal_channels": (
        "refusal_channel",
        (
            "channel_id",
            "subject_cell_id",
            "active_refusal",
            "legal_hold",
            "stop_threshold",
            "observed_signal",
        ),
        ("channel_id", "subject_cell_id"),
    ),
    "balance_witnesses": (
        "resource_balance_witness",
        (
            "witness_id",
            "flux_id",
            "source_debit",
            "target_credit",
            "loss_upper_bound",
            "conversion_factor",
            "unit",
        ),
        ("witness_id", "flux_id"),
    ),
    "effect_witnesses": (
        "satisfaction_effect_witness",
        ("witness_id", "flux_id", "target_cell_id", "resource_type", "predicted_delta"),
        ("witness_id", "flux_id"),
    ),
    "stabilization_buffers": (
        "stabilization_buffer",
        ("buffer_id", "cell_id", "resource_type", "unit", "components", "shock_envelope"),
        ("buffer_id", "cell_id"),
    ),
    "handover_protocols": (
        "bounded_friction_handover",
        (
            "handover_id",
            "from_controller",
            "to_controller",
            "mode",
            "dual_run",
            "shadow_mode",
            "rollback_available",
            "override_live",
            "authority_valid",
            "telemetry_fresh",
            "explanation_channel_available",
            "skill_debt_upper_bound",
            "skill_debt_budget",
        ),
        ("handover_id", "from_controller", "to_controller"),
    ),
}

_REQUIRED_BUFFER_COMPONENT_FIELDS = (
    "component_id",
    "kind",
    "amount",
    "resource_type",
    "unit",
)
_REQUIRED_SHOCK_ENVELOPE_FIELDS = (
    "envelope_id",
    "resource_type",
    "unit",
    "shock_upper_bound",
    "panic_load",
    "queue_load",
    "residual_charge",
)


def unit_compatible(left: UnitFrame, right: UnitFrame) -> bool:
    """Return true when two AFST v1 unit frames can be compared directly."""

    if left.resource_type != right.resource_type:
        return False
    if left.unit != right.unit:
        return False
    return not (left.unit_family and right.unit_family and left.unit_family != right.unit_family)


def audit_afst_raw_input(data: Mapping[str, Any], policy: AFSTProfilePolicy) -> RawInputAudit:
    """Audit raw AFST input paths before model defaults are applied."""

    required = [
        "satisfaction_coordinates",
        "abundance_coordinates",
        "candidate_fluxes",
        "stabilization_buffers",
    ]
    if policy.require_authority:
        required.append("authority_envelopes")
    if policy.require_consent_channel:
        required.append("consent_channels")
    if policy.require_refusal_channel:
        required.append("refusal_channels")
    if policy.require_handover_for_controller_change:
        required.append("handover_protocols")
    if policy.require_balance_witness:
        required.append("balance_witnesses")

    supplied = sorted(str(key) for key in data)
    missing = [path for path in required if not _nonempty_list(data.get(path))]
    known = {
        "report_id",
        "schema_version",
        "profile",
        "reference_time",
        "satisfaction_coordinates",
        "abundance_coordinates",
        "candidate_fluxes",
        "authority_envelopes",
        "consent_channels",
        "refusal_channels",
        "balance_witnesses",
        "effect_witnesses",
        "stabilization_buffers",
        "handover_protocols",
        "observation_window_refs",
        "trc_report_refs",
        "alt_report_refs",
    }
    unknown = sorted(key for key in supplied if key not in known)
    reasons = [f"missing_{path}" for path in missing]
    if unknown:
        reasons.append("unknown_top_level_paths_preserved")
    return RawInputAudit(
        supplied_paths=supplied,
        missing_required_paths=missing,
        unknown_paths=unknown,
        accepted=not missing,
        reasons=reasons,
    )


def compute_satisfaction_deficit(coord: SatisfactionCoordinate) -> SatisfactionDeficit:
    """Compute a finite satisfaction deficit without subtracting residuals."""

    reasons: list[str] = []
    for field in ("value", "floor_critical", "floor_min", "floor_safe"):
        _finite(getattr(coord, field), f"satisfaction_{field}", reasons)
    if coord.floor_critical > coord.floor_min or coord.floor_min > coord.floor_safe:
        reasons.append("satisfaction_floor_order_violation")
    if not coord.coordinate_id:
        reasons.append("missing_satisfaction_coordinate_id")
    if not coord.cell_id:
        reasons.append("missing_satisfaction_cell_id")
    if not coord.resource_type:
        reasons.append("missing_satisfaction_resource_type")
    amount = max(0.0, coord.floor_min - coord.value)
    uncertainty = coord.residual_ledger.burden_sum()
    return SatisfactionDeficit(
        deficit_id=f"deficit:{coord.coordinate_id or _short_hash(coord.model_dump(mode='json'))}",
        coordinate_id=coord.coordinate_id,
        cell_id=coord.cell_id,
        resource_type=coord.resource_type,
        amount=amount,
        uncertainty_charge=uncertainty,
        unit=coord.unit,
        unit_family=coord.unit_family,
        floor_ref="floor_min",
        evidence_refs=list(coord.evidence_refs),
        residual_ledger=_ledger_from_reasons(reasons, "satisfaction"),
        accepted=not reasons,
        reasons=sorted(set(reasons)),
    )


def compute_certified_abundance(
    record: CertifiedAbundanceCoordinate,
) -> CertifiedAbundanceCoordinate:
    """Recompute local certified abundance after all declared residual charges."""

    reasons: list[str] = []
    numeric_fields = [
        "available_amount",
        "safe_floor",
        "reserve_amount",
        "legal_hold_amount",
        "spoilage_upper_bound",
        "transfer_loss_upper_bound",
        "observation_residual",
        "lifecycle_residual",
        "other_hard_residual",
    ]
    for field in numeric_fields:
        value = getattr(record, field)
        if _finite(value, f"abundance_{field}", reasons):
            _nonnegative(value, f"abundance_{field}", reasons)
    certified = max(
        0.0,
        record.available_amount
        - record.safe_floor
        - record.reserve_amount
        - record.legal_hold_amount
        - record.spoilage_upper_bound
        - record.transfer_loss_upper_bound
        - record.observation_residual
        - record.lifecycle_residual
        - record.other_hard_residual,
    )
    if not record.abundance_id:
        reasons.append("missing_abundance_id")
    if not record.cell_id:
        reasons.append("missing_abundance_cell_id")
    if not record.resource_type:
        reasons.append("missing_abundance_resource_type")
    if not record.authority_refs:
        reasons.append("missing_authority_ref")
    if not record.evidence_refs:
        reasons.append("missing_evidence_ref")
    if certified <= 0.0:
        reasons.append("certified_abundance_nonpositive")
    return record.model_copy(
        update={
            "certified_amount": certified,
            "accepted": not reasons,
            "reasons": sorted(set(record.reasons) | set(reasons)),
            "residual_ledger": record.residual_ledger.combine(
                _ledger_from_reasons(reasons, record.abundance_id or "abundance")
            ),
        },
        deep=True,
    )


def check_authority_envelope(
    envelope: AuthorityEnvelope,
    *,
    required_scope: set[str],
    required_resource_type: str,
    required_action: str,
    reference_time: datetime | None,
    dry_run: bool = True,
) -> AuthorityEnvelope:
    """Check one authority envelope without granting execution authority."""

    reasons: list[str] = []
    status = envelope.status.lower()
    if status not in ACCEPTED_AUTHORITY_STATUSES:
        reasons.append("authority_status_not_active")
    if required_resource_type and envelope.resource_type != required_resource_type:
        reasons.append("authority_resource_mismatch")
    if required_action and envelope.action != required_action:
        reasons.append("authority_action_mismatch")
    scope = {item.lower() for item in envelope.scope}
    if not {item.lower() for item in required_scope}.issubset(scope):
        reasons.append("authority_scope_mismatch")
    if _is_expired(envelope.expires_at, reference_time):
        reasons.append("authority_expired")
    if envelope.fixture_only and not dry_run:
        reasons.append("fixture_only_authority_non_executable")
    if not envelope.authority_id:
        reasons.append("missing_authority_envelope")
    return envelope.model_copy(
        update={
            "accepted": not reasons,
            "reasons": sorted(set(envelope.reasons) | set(reasons)),
            "residual_ledger": envelope.residual_ledger.combine(
                _ledger_from_reasons(reasons, envelope.authority_id or "authority")
            ),
        },
        deep=True,
    )


def check_consent_channel(
    channel: ConsentChannel,
    *,
    flux: CandidateFlux,
    reference_time: datetime | None,
) -> ConsentChannel:
    """Check one consent channel for a target-receive flux gate."""

    reasons: list[str] = []
    if not channel.consent_granted:
        reasons.append("consent_not_granted")
    if channel.resource_type and channel.resource_type != flux.resource_type:
        reasons.append("consent_resource_mismatch")
    required_scope = {flux.target_cell_id, flux.resource_type, "receive"}
    scope = {item.lower() for item in channel.scope}
    if not {item.lower() for item in required_scope if item}.issubset(scope):
        reasons.append("consent_scope_mismatch")
    if channel.action and channel.action != "receive":
        reasons.append("consent_action_mismatch")
    if _is_expired(channel.expires_at, reference_time):
        reasons.append("consent_expired")
    if not channel.consent_id:
        reasons.append("missing_consent_channel")
    return channel.model_copy(
        update={
            "accepted": not reasons,
            "reasons": sorted(set(channel.reasons) | set(reasons)),
            "residual_ledger": channel.residual_ledger.combine(
                _ledger_from_reasons(reasons, channel.consent_id or "consent")
            ),
        },
        deep=True,
    )


def check_refusal_channel(channel: RefusalChannel) -> RefusalChannel:
    """Check one refusal channel and preserve active refusal blockers."""

    reasons: list[str] = []
    if not channel.channel_id:
        reasons.append("refusal_channel_missing")
    if channel.active_refusal:
        reasons.append("refusal_active")
    if channel.legal_hold:
        reasons.append("legal_hold_present")
    if channel.observed_signal >= channel.stop_threshold:
        reasons.append("refusal_stop_threshold_crossed")
    return channel.model_copy(
        update={
            "accepted": not reasons,
            "reasons": sorted(set(channel.reasons) | set(reasons)),
            "residual_ledger": channel.residual_ledger.combine(
                _ledger_from_reasons(reasons, channel.channel_id or "refusal")
            ),
        },
        deep=True,
    )


def check_resource_balance(witness: ResourceBalanceWitness) -> ResourceBalanceWitness:
    """Check finite source-debit / target-credit resource balance."""

    reasons: list[str] = []
    for field in (
        "source_debit",
        "target_credit",
        "loss_upper_bound",
        "conversion_factor",
        "conservation_residual",
    ):
        value = getattr(witness, field)
        if _finite(value, f"balance_{field}", reasons):
            if field == "conversion_factor":
                if value <= 0.0:
                    reasons.append("resource_balance_conversion_nonpositive")
            else:
                _nonnegative(value, f"balance_{field}", reasons)
    upper_credit = witness.source_debit * witness.conversion_factor - witness.loss_upper_bound
    if witness.target_credit > max(0.0, upper_credit) + witness.conservation_residual:
        reasons.append("resource_balance_violation")
    if not witness.witness_id:
        reasons.append("missing_balance_witness_id")
    if not witness.flux_id:
        reasons.append("physical_balance_unknown")
    return witness.model_copy(
        update={
            "accepted": not reasons,
            "reasons": sorted(set(witness.reasons) | set(reasons)),
            "residual_ledger": witness.residual_ledger.combine(
                _ledger_from_reasons(reasons, witness.witness_id or "balance")
            ),
        },
        deep=True,
    )


def check_stabilization_buffer(buffer: StabilizationBuffer) -> StabilizationBuffer:
    """Check typed buffer capacity against a finite shock envelope."""

    reasons: list[str] = []
    available = 0.0
    frame = UnitFrame(
        resource_type=buffer.resource_type,
        unit=buffer.unit,
        unit_family=buffer.unit_family,
    )
    if not buffer.components:
        reasons.append("missing_buffer_component")
    for component in buffer.components:
        component_frame = UnitFrame(
            resource_type=component.resource_type,
            unit=component.unit,
            unit_family=component.unit_family,
        )
        if not unit_compatible(frame, component_frame):
            reasons.append("buffer_unit_mismatch")
        if component.amount < 0.0 or not isfinite(component.amount):
            reasons.append("buffer_negative_component")
        else:
            available += component.amount
    required = 0.0
    shock = buffer.shock_envelope
    if shock is None:
        reasons.append("missing_shock_envelope")
    else:
        shock_frame = UnitFrame(
            resource_type=shock.resource_type,
            unit=shock.unit,
            unit_family=shock.unit_family,
        )
        if not unit_compatible(frame, shock_frame):
            reasons.append("buffer_unit_mismatch")
        shock_values = [
            shock.shock_upper_bound,
            shock.panic_load,
            shock.queue_load,
            shock.legal_hold_load,
            shock.spoilage_upper_bound,
            shock.residual_charge,
        ]
        if any(value < 0.0 or not isfinite(value) for value in shock_values):
            reasons.append("shock_negative_component")
        else:
            required = sum(shock_values)
    if shock is not None and available < required:
        reasons.append("buffer_insufficient")
    coverage = available / required if required > 0.0 else None
    return buffer.model_copy(
        update={
            "available_buffer": available,
            "required_buffer": required,
            "coverage_ratio": coverage,
            "accepted": not reasons,
            "reasons": sorted(set(buffer.reasons) | set(reasons)),
            "residual_ledger": buffer.residual_ledger.combine(
                _ledger_from_reasons(reasons, buffer.buffer_id or "buffer")
            ),
        },
        deep=True,
    )


def check_bounded_friction_handover(
    handover: BoundedFrictionHandover,
) -> BoundedFrictionHandover:
    """Check bounded-friction handover without promoting execution authority."""

    reasons: list[str] = []
    if not handover.authority_valid:
        reasons.append("handover_authority_invalid")
    if not handover.telemetry_fresh:
        reasons.append("handover_telemetry_stale")
    if not handover.rollback_available:
        reasons.append("handover_rollback_missing")
    if not handover.override_live:
        reasons.append("handover_override_missing")
    if not handover.explanation_channel_available:
        reasons.append("handover_explanation_channel_missing")
    if handover.covert_transition:
        reasons.append("handover_covert_transition")
    if handover.irreversible_transition:
        reasons.append("handover_irreversible_transition")
    if handover.skill_debt_upper_bound > handover.skill_debt_budget:
        reasons.append("handover_skill_debt_unbounded")
    if handover.mode not in {"diagnostic-only", "manual-review"} and not (
        handover.dual_run or handover.shadow_mode
    ):
        reasons.append("handover_no_shadow_or_dual_run")
    if handover.settled:
        reasons.append("handover_settlement_blocked")
    return handover.model_copy(
        update={
            "accepted": not reasons,
            "settled": False,
            "reasons": sorted(set(handover.reasons) | set(reasons)),
            "residual_ledger": handover.residual_ledger.combine(
                _ledger_from_reasons(reasons, handover.handover_id or "handover")
            ),
        },
        deep=True,
    )


def check_non_market_liquidity(
    abundance: CertifiedAbundanceCoordinate,
    deficit: SatisfactionDeficit,
    flux: CandidateFlux,
    *,
    policy: AFSTProfilePolicy,
    authority_envelopes: list[AuthorityEnvelope] | None = None,
    consent_channels: list[ConsentChannel] | None = None,
    refusal_channels: list[RefusalChannel] | None = None,
    balance_witnesses: list[ResourceBalanceWitness] | None = None,
    effect_witnesses: list[SatisfactionEffectWitness] | None = None,
    reference_time: datetime | None = None,
) -> NonMarketLiquidityCertificate:
    """Check one source-abundance, target-deficit, and candidate-flux binding."""

    reasons: list[str] = []
    amount_positive = flux.amount > 0.0 and isfinite(flux.amount)
    if not amount_positive:
        reasons.append("flux_amount_nonpositive")
    if flux.conversion_factor <= 0.0 or not isfinite(flux.conversion_factor):
        reasons.append("flux_conversion_nonpositive")
    for field in ("latency", "loss_upper_bound", "transfer_residual"):
        value = getattr(flux, field)
        if value < 0.0 or not isfinite(value):
            reasons.append("negative_numeric_field")

    abundance_frame = UnitFrame(
        resource_type=abundance.resource_type,
        unit=abundance.unit,
        unit_family=abundance.unit_family,
    )
    deficit_frame = UnitFrame(
        resource_type=deficit.resource_type,
        unit=deficit.unit,
        unit_family=deficit.unit_family,
    )
    flux_frame = UnitFrame(
        resource_type=flux.resource_type,
        unit=flux.unit,
        unit_family=flux.unit_family,
    )
    if not unit_compatible(abundance_frame, flux_frame) or not unit_compatible(
        deficit_frame, flux_frame
    ):
        reasons.append("unit_mismatch")
    if abundance.resource_type != flux.resource_type or deficit.resource_type != flux.resource_type:
        reasons.append("resource_type_mismatch")
    source_floor_preserved = amount_positive and flux.amount <= abundance.certified_amount
    if not source_floor_preserved:
        reasons.append("source_floor_violation")
    if abundance.certified_amount <= 0.0:
        reasons.append("certified_abundance_nonpositive")
    target_deficit_positive = deficit.amount > 0.0
    if not target_deficit_positive:
        reasons.append("target_deficit_not_positive")

    effective_amount = max(
        0.0,
        flux.amount * flux.conversion_factor - flux.loss_upper_bound - flux.transfer_residual,
    )
    effect = _effect_for_flux(flux, effect_witnesses or [])
    effect_delta = (
        effect.observed_delta
        if effect is not None and effect.observed_delta is not None
        else effect.predicted_delta
        if effect is not None
        else effective_amount
    )
    target_deficit_reduced = target_deficit_positive and effect_delta > 0.0
    if not target_deficit_reduced:
        reasons.append("target_deficit_not_reduced")

    price_not_primary = flux.liquidity_mode != "market_signal_only"
    if not price_not_primary:
        reasons.append("price_only_signal")

    authority_valid = _authority_valid(
        flux,
        abundance,
        policy,
        authority_envelopes or [],
        reference_time,
        reasons,
    )
    consent_valid = _consent_valid(
        flux,
        policy,
        consent_channels or [],
        reference_time,
        reasons,
    )
    refusal_preserved = _refusal_preserved(flux, policy, refusal_channels or [], reasons)
    balance = _balance_for_flux(flux, balance_witnesses or [])
    physical_balance_preserved = False
    if balance is None:
        if policy.require_balance_witness:
            reasons.append("physical_balance_unknown")
    else:
        checked_balance = check_resource_balance(balance)
        physical_balance_preserved = checked_balance.accepted
        reasons.extend(checked_balance.reasons)
        if checked_balance.unit != flux.unit or checked_balance.unit_family != flux.unit_family:
            reasons.append("unit_mismatch")
    lifecycle_fresh = bool(abundance.observation_window_ref or abundance.evidence_refs)
    if policy.require_lifecycle_freshness and not lifecycle_fresh:
        reasons.append("lifecycle_stale")

    gates = {
        "amount_positive": amount_positive,
        "unit_compatible": "unit_mismatch" not in reasons,
        "source_floor_preserved": source_floor_preserved,
        "target_deficit_reduced": target_deficit_reduced,
        "physical_balance_preserved": physical_balance_preserved,
        "authority_valid": authority_valid,
        "refusal_preserved": refusal_preserved,
        "lifecycle_fresh": lifecycle_fresh,
        "price_not_primary": price_not_primary,
    }
    if policy.require_consent_channel:
        gates["consent_valid"] = consent_valid
    accepted = all(gates.values()) and not _blocking_reasons(reasons)
    status = _liquidity_status(accepted, reasons)
    certificate_id = "afst-liquidity:" + _short_hash(
        [abundance.abundance_id, deficit.deficit_id, flux.flux_id]
    )
    return NonMarketLiquidityCertificate(
        certificate_id=certificate_id,
        abundance_id=abundance.abundance_id,
        deficit_id=deficit.deficit_id,
        flux_id=flux.flux_id,
        balance_witness_id=balance.witness_id if balance is not None else None,
        effect_witness_id=effect.witness_id if effect is not None else None,
        source_floor_preserved=source_floor_preserved,
        target_deficit_reduced=target_deficit_reduced,
        physical_balance_preserved=physical_balance_preserved,
        authority_valid=authority_valid,
        consent_valid=consent_valid,
        refusal_preserved=refusal_preserved,
        lifecycle_fresh=lifecycle_fresh,
        price_not_primary=price_not_primary,
        residual_ledger=_ledger_from_reasons(reasons, flux.flux_id or certificate_id),
        missing_obligations=sorted(set(reasons)),
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted and not policy.operationally_usable_requires_observed_effect,
        settled=False,
        status=status,
        reasons=sorted(set(reasons)),
    )


def build_satisfaction_flux_record(
    certificate: NonMarketLiquidityCertificate,
    abundance: CertifiedAbundanceCoordinate,
    deficit: SatisfactionDeficit,
    flux: CandidateFlux,
    effect: SatisfactionEffectWitness | None = None,
) -> SatisfactionFluxRecord:
    """Build one deterministic AFST flux ledger record."""

    effective_amount = max(
        0.0,
        flux.amount * flux.conversion_factor - flux.loss_upper_bound - flux.transfer_residual,
    )
    effect_delta = (
        effect.observed_delta
        if effect is not None and effect.observed_delta is not None
        else effect.predicted_delta
        if effect is not None
        else effective_amount
    )
    pre = {deficit.coordinate_id: deficit.amount}
    post = {deficit.coordinate_id: max(0.0, deficit.amount - max(0.0, effect_delta))}
    observed = (
        {deficit.coordinate_id: max(0.0, deficit.amount - effect.observed_delta)}
        if effect is not None and effect.observed_delta is not None
        else {}
    )
    return SatisfactionFluxRecord(
        record_id=f"afst-flux:{_short_hash([certificate.certificate_id, flux.flux_id])}",
        flux_id=flux.flux_id,
        certificate_id=certificate.certificate_id,
        trace_id=flux.trace_refs[0] if flux.trace_refs else None,
        resource_type=flux.resource_type,
        source_cell_id=flux.source_cell_id,
        target_cell_id=flux.target_cell_id,
        amount=flux.amount,
        effective_amount=effective_amount,
        unit=flux.unit,
        unit_family=flux.unit_family,
        latency=flux.latency,
        loss_upper_bound=flux.loss_upper_bound,
        predicted_satisfaction_pre=pre,
        predicted_satisfaction_post=post,
        observed_satisfaction_post=observed,
        authority_refs=list(flux.authority_envelope_refs or abundance.authority_refs),
        consent_refs=list(flux.consent_refs),
        refusal_refs=list(flux.refusal_refs),
        evidence_refs=sorted(set(flux.evidence_refs) | set(abundance.evidence_refs)),
        residual_ledger=certificate.residual_ledger,
        status=certificate.status,
        accepted=certificate.accepted,
        settled=False,
        reasons=list(certificate.reasons),
    )


def build_afst_flux_stabilization_report(
    data: Mapping[str, Any],
    *,
    profile: str = "development",
) -> AFSTFluxStabilizationReport:
    """Build a deterministic AFST flux stabilization report from raw case data."""

    policy = afst_profile_policy(profile)
    raw_audit = audit_afst_raw_input(data, policy)
    reference_time = (
        _parse_time(str(data.get("reference_time"))) if data.get("reference_time") else None
    )
    residuals = [
        _residual(f"missing_{path}", True, object_id="raw-input")
        for path in raw_audit.missing_required_paths
    ]
    residuals.extend(_raw_record_missing_residuals(data))

    satisfaction_coordinates = _models(
        SatisfactionCoordinate,
        data.get("satisfaction_coordinates"),
    )
    deficits = [compute_satisfaction_deficit(coord) for coord in satisfaction_coordinates]
    abundances = [
        compute_certified_abundance(item)
        for item in _models(CertifiedAbundanceCoordinate, data.get("abundance_coordinates"))
    ]
    fluxes = _models(CandidateFlux, data.get("candidate_fluxes"))
    authority_envelopes = _models(AuthorityEnvelope, data.get("authority_envelopes"))
    consent_channels = _models(ConsentChannel, data.get("consent_channels"))
    refusal_channels = _models(RefusalChannel, data.get("refusal_channels"))
    balance_witnesses = _models(ResourceBalanceWitness, data.get("balance_witnesses"))
    effect_witnesses = _models(SatisfactionEffectWitness, data.get("effect_witnesses"))
    buffers = [
        check_stabilization_buffer(item)
        for item in _models(StabilizationBuffer, data.get("stabilization_buffers"))
    ]
    handovers = [
        check_bounded_friction_handover(item)
        for item in _models(BoundedFrictionHandover, data.get("handover_protocols"))
    ]

    residuals.extend(_model_reason_residuals(buffers, "buffer"))
    residuals.extend(_model_reason_residuals(handovers, "handover"))

    certificates: list[NonMarketLiquidityCertificate] = []
    flux_records: list[SatisfactionFluxRecord] = []
    for flux in sorted(fluxes, key=lambda item: item.flux_id):
        abundance = _bind_abundance(flux, abundances)
        deficit = _bind_deficit(flux, deficits)
        if abundance is None:
            certificate = _diagnostic_certificate(flux, "missing_certified_abundance")
            certificates.append(certificate)
            residuals.append(_residual("missing_certified_abundance", True, object_id=flux.flux_id))
            continue
        if deficit is None:
            certificate = _diagnostic_certificate(flux, "missing_target_deficit")
            certificates.append(certificate)
            residuals.append(_residual("missing_target_deficit", True, object_id=flux.flux_id))
            continue
        certificate = check_non_market_liquidity(
            abundance,
            deficit,
            flux,
            policy=policy,
            authority_envelopes=authority_envelopes,
            consent_channels=consent_channels,
            refusal_channels=refusal_channels,
            balance_witnesses=balance_witnesses,
            effect_witnesses=effect_witnesses,
            reference_time=reference_time,
        )
        effect = _effect_for_flux(flux, effect_witnesses)
        certificates.append(certificate)
        flux_records.append(
            build_satisfaction_flux_record(certificate, abundance, deficit, flux, effect)
        )
        residuals.extend(
            _residual(reason, _reason_blocking(reason), object_id=flux.flux_id)
            for reason in certificate.reasons
        )

    residuals = _sorted_residuals(residuals)
    blockers = _sorted_unique(
        str(item.get("kind"))
        for item in residuals
        if item.get("blocking") is True and item.get("kind")
    )
    raw_ok = raw_audit.accepted
    liquidity_ok = bool(certificates) and all(cert.accepted for cert in certificates)
    buffer_ok = bool(buffers) and all(buffer.accepted for buffer in buffers)
    if not policy.require_buffer:
        buffer_ok = True
    handover_ok = (
        all(handover.accepted for handover in handovers)
        if handovers
        else (not policy.require_handover_for_controller_change)
    )
    accepted = raw_ok and liquidity_ok and buffer_ok and handover_ok and not blockers
    status = ClaimStatus.PROVISIONAL if accepted else _report_status(certificates, blockers)
    report_id = str(data.get("report_id") or "afst-flux-stabilization")
    return AFSTFluxStabilizationReport(
        report_id=report_id,
        profile=policy.profile,
        raw_input_audit=raw_audit,
        observation_window_refs=_string_list(data.get("observation_window_refs")),
        trc_report_refs=_string_list(data.get("trc_report_refs")),
        alt_report_refs=_string_list(data.get("alt_report_refs")),
        liquidity_certificates=sorted(certificates, key=lambda item: item.certificate_id),
        satisfaction_flux_ledger=sorted(flux_records, key=lambda item: item.record_id),
        stabilization_buffers=sorted(buffers, key=lambda item: item.buffer_id),
        handover_protocols=sorted(handovers, key=lambda item: item.handover_id),
        accepted=accepted,
        finite_checks_passed=accepted,
        diagnostic_usable=bool(certificates) or bool(residuals),
        operationally_usable=accepted and not policy.operationally_usable_requires_observed_effect,
        flux_admissible=accepted,
        operation_ready=False,
        provider_dispatch_ready=False,
        physical_dispatch_ready=False,
        settled=False,
        status=status,
        blockers=blockers,
        missing_obligations=blockers,
        residuals=residuals,
        residual_ledger=_ledger_from_residual_dicts(residuals, report_id),
        next_safe_actions=_next_safe_actions(blockers),
        non_claims=list(AFST_NON_CLAIMS),
        reasons=_sorted_unique([*raw_audit.reasons, *blockers]),
    )


def _models(model: type[ModelT], value: Any) -> list[ModelT]:
    return [model.model_validate(item) for item in _records(value)]


def _records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _raw_record_missing_residuals(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    for path, (record_type, fields, id_fields) in _REQUIRED_RECORD_FIELDS.items():
        for index, record in enumerate(_records(data.get(path))):
            residuals.extend(
                _missing_field_residuals(
                    record,
                    record_type,
                    fields,
                    object_id=_record_object_id(record, id_fields, f"{record_type}:{index}"),
                )
            )
            if path == "stabilization_buffers":
                residuals.extend(_buffer_nested_missing_residuals(record, index))
    return residuals


def _buffer_nested_missing_residuals(
    buffer: Mapping[str, Any],
    buffer_index: int,
) -> list[dict[str, Any]]:
    buffer_id = _record_object_id(
        buffer,
        ("buffer_id", "cell_id"),
        f"stabilization_buffer:{buffer_index}",
    )
    residuals: list[dict[str, Any]] = []
    for component_index, component in enumerate(_records(buffer.get("components"))):
        residuals.extend(
            _missing_field_residuals(
                component,
                "buffer_component",
                _REQUIRED_BUFFER_COMPONENT_FIELDS,
                object_id=_record_object_id(
                    component,
                    ("component_id", "kind"),
                    f"{buffer_id}:component:{component_index}",
                ),
            )
        )
    shock = buffer.get("shock_envelope")
    if isinstance(shock, Mapping):
        residuals.extend(
            _missing_field_residuals(
                shock,
                "shock_envelope",
                _REQUIRED_SHOCK_ENVELOPE_FIELDS,
                object_id=_record_object_id(
                    shock,
                    ("envelope_id",),
                    f"{buffer_id}:shock_envelope",
                ),
            )
        )
    return residuals


def _missing_field_residuals(
    record: Mapping[str, Any],
    record_type: str,
    fields: Sequence[str],
    *,
    object_id: str,
) -> list[dict[str, Any]]:
    return [
        _residual(f"missing_{record_type}_{field}", True, object_id=object_id)
        for field in fields
        if _field_missing(record, field)
    ]


def _record_object_id(
    record: Mapping[str, Any],
    id_fields: Sequence[str],
    fallback: str,
) -> str:
    for field in id_fields:
        value = record.get(field)
        if value is not None and value != "":
            return str(value)
    return fallback


def _field_missing(record: Mapping[str, Any], field: str) -> bool:
    if field not in record:
        return True
    value = record[field]
    if value is None or value == "":
        return True
    return isinstance(value, list) and not value


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item) for item in value if str(item)})


def _finite(value: float, name: str, reasons: list[str]) -> bool:
    if not isfinite(value):
        reasons.append("nonfinite_numeric_field")
        reasons.append(f"nonfinite_{name}")
        return False
    return True


def _nonnegative(value: float, name: str, reasons: list[str]) -> bool:
    if value < 0.0:
        reasons.append("negative_numeric_field")
        reasons.append(f"negative_{name}")
        return False
    return True


def _short_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:16]


def _sorted_unique(items: Iterable[str]) -> list[str]:
    return sorted({item for item in items if item})


def _residual(
    kind: str,
    blocking: bool,
    *,
    object_id: str = "",
    description: str | None = None,
) -> dict[str, Any]:
    subject = object_id or kind
    return {
        "blocking": blocking,
        "description": description or kind.replace("_", " "),
        "kind": kind,
        "object_id": subject,
        "residual_id": f"afst:{_short_hash([kind, subject, blocking])}",
        "residual_preserved": True,
    }


def _ledger_from_reasons(reasons: Sequence[str], subject: str) -> Ledger:
    ledger = Ledger()
    for reason in sorted(set(reasons)):
        ledger = ledger.add_coordinate(
            f"{subject}:{reason}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
            description=reason.replace("_", " "),
        )
    return ledger


def _ledger_from_residual_dicts(residuals: Sequence[Mapping[str, Any]], subject: str) -> Ledger:
    ledger = Ledger()
    for residual in residuals:
        kind = str(residual.get("kind") or "residual")
        ledger = ledger.add_coordinate(
            f"{subject}:{kind}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
            description=str(residual.get("description") or kind),
        )
    return ledger


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_expired(value: str | None, reference_time: datetime | None) -> bool:
    if not value or reference_time is None:
        return False
    parsed = _parse_time(value)
    if parsed is None:
        return False
    return parsed < reference_time


def _scope_for_flux(flux: CandidateFlux) -> set[str]:
    return {flux.source_cell_id, flux.target_cell_id, flux.resource_type, "allocate"}


def _authority_valid(
    flux: CandidateFlux,
    abundance: CertifiedAbundanceCoordinate,
    policy: AFSTProfilePolicy,
    envelopes: Sequence[AuthorityEnvelope],
    reference_time: datetime | None,
    reasons: list[str],
) -> bool:
    refs = _sorted_unique([*flux.authority_envelope_refs, *abundance.authority_refs])
    if not refs:
        if policy.require_authority:
            reasons.append("missing_authority_envelope")
        return not policy.require_authority
    by_id = {item.authority_id: item for item in envelopes}
    accepted = True
    for ref in refs:
        envelope = by_id.get(ref)
        if envelope is None:
            reasons.append("missing_authority_envelope")
            accepted = False
            continue
        checked = check_authority_envelope(
            envelope,
            required_scope=_scope_for_flux(flux),
            required_resource_type=flux.resource_type,
            required_action="allocate",
            reference_time=reference_time,
            dry_run=True,
        )
        if not checked.accepted:
            reasons.extend(checked.reasons)
            accepted = False
    return accepted


def _consent_valid(
    flux: CandidateFlux,
    policy: AFSTProfilePolicy,
    channels: Sequence[ConsentChannel],
    reference_time: datetime | None,
    reasons: list[str],
) -> bool:
    if not flux.consent_refs and not policy.require_consent_channel:
        return True
    if not flux.consent_refs:
        reasons.append("missing_consent_channel")
        return False
    by_id = {item.consent_id: item for item in channels}
    accepted = True
    for ref in flux.consent_refs:
        channel = by_id.get(ref)
        if channel is None:
            reasons.append("missing_consent_channel")
            accepted = False
            continue
        checked = check_consent_channel(channel, flux=flux, reference_time=reference_time)
        if not checked.accepted:
            reasons.extend(checked.reasons)
            accepted = False
    return accepted


def _refusal_preserved(
    flux: CandidateFlux,
    policy: AFSTProfilePolicy,
    channels: Sequence[RefusalChannel],
    reasons: list[str],
) -> bool:
    if not flux.refusal_refs:
        if policy.require_refusal_channel:
            reasons.append("refusal_channel_missing")
        return not policy.require_refusal_channel
    by_id = {item.channel_id: item for item in channels}
    accepted = True
    for ref in flux.refusal_refs:
        channel = by_id.get(ref)
        if channel is None:
            reasons.append("refusal_channel_missing")
            accepted = False
            continue
        checked = check_refusal_channel(channel)
        if not checked.accepted:
            reasons.extend(checked.reasons)
            accepted = False
    return accepted


def _balance_for_flux(
    flux: CandidateFlux,
    witnesses: Sequence[ResourceBalanceWitness],
) -> ResourceBalanceWitness | None:
    for witness in sorted(witnesses, key=lambda item: item.witness_id):
        if witness.flux_id == flux.flux_id:
            return witness
    return None


def _effect_for_flux(
    flux: CandidateFlux,
    witnesses: Sequence[SatisfactionEffectWitness],
) -> SatisfactionEffectWitness | None:
    for witness in sorted(witnesses, key=lambda item: item.witness_id):
        if witness.flux_id == flux.flux_id:
            return witness
    return None


def _bind_abundance(
    flux: CandidateFlux,
    abundances: Sequence[CertifiedAbundanceCoordinate],
) -> CertifiedAbundanceCoordinate | None:
    candidates = [
        item
        for item in abundances
        if item.cell_id == flux.source_cell_id and item.resource_type == flux.resource_type
    ]
    if not candidates:
        return None
    exact = [
        item
        for item in candidates
        if item.unit == flux.unit
        and (not item.unit_family or not flux.unit_family or item.unit_family == flux.unit_family)
    ]
    return sorted(exact or candidates, key=lambda item: item.abundance_id)[0]


def _bind_deficit(
    flux: CandidateFlux,
    deficits: Sequence[SatisfactionDeficit],
) -> SatisfactionDeficit | None:
    candidates = [
        item
        for item in deficits
        if item.cell_id == flux.target_cell_id and item.resource_type == flux.resource_type
    ]
    if not candidates:
        return None
    exact = [
        item
        for item in candidates
        if item.unit == flux.unit
        and (not item.unit_family or not flux.unit_family or item.unit_family == flux.unit_family)
    ]
    return sorted(exact or candidates, key=lambda item: item.deficit_id)[0]


def _diagnostic_certificate(flux: CandidateFlux, reason: str) -> NonMarketLiquidityCertificate:
    certificate_id = f"afst-liquidity:{_short_hash([flux.flux_id, reason])}"
    return NonMarketLiquidityCertificate(
        certificate_id=certificate_id,
        flux_id=flux.flux_id,
        residual_ledger=_ledger_from_reasons([reason], flux.flux_id or certificate_id),
        missing_obligations=[reason],
        accepted=False,
        finite_checks_passed=False,
        operationally_usable=False,
        settled=False,
        status=ClaimStatus.DIAGNOSTIC,
        reasons=[reason],
    )


def _model_reason_residuals(models: Sequence[Any], prefix: str) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    for model in models:
        model_id = str(
            getattr(model, "buffer_id", "")
            or getattr(model, "handover_id", "")
            or getattr(model, "witness_id", "")
            or prefix
        )
        for reason in getattr(model, "reasons", []):
            residuals.append(
                _residual(str(reason), _reason_blocking(str(reason)), object_id=model_id)
            )
    return residuals


def _reason_blocking(reason: str) -> bool:
    nonblocking = {
        "unknown_top_level_paths_preserved",
        "legacy_flat_buffer_input",
        "renamed_frictionless_to_bounded_friction",
    }
    return reason not in nonblocking


def _blocking_reasons(reasons: Sequence[str]) -> list[str]:
    return [reason for reason in reasons if _reason_blocking(reason)]


def _liquidity_status(accepted: bool, reasons: Sequence[str]) -> ClaimStatus:
    if accepted:
        return ClaimStatus.PROVISIONAL
    if any(reason in {"refusal_active", "legal_hold_present"} for reason in reasons):
        return ClaimStatus.REJECTED
    if any("expired" in reason for reason in reasons):
        return ClaimStatus.EXPIRED
    return ClaimStatus.DIAGNOSTIC


def _report_status(
    certificates: Sequence[NonMarketLiquidityCertificate],
    blockers: Sequence[str],
) -> ClaimStatus:
    if any(item.status == ClaimStatus.REJECTED for item in certificates) or any(
        item in {"refusal_active", "legal_hold_present"} for item in blockers
    ):
        return ClaimStatus.REJECTED
    if any(item.status == ClaimStatus.EXPIRED for item in certificates):
        return ClaimStatus.EXPIRED
    return ClaimStatus.DIAGNOSTIC


def _sorted_residuals(residuals: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(item) for item in residuals),
        key=lambda item: (
            str(item.get("kind") or ""),
            str(item.get("object_id") or ""),
            str(item.get("residual_id") or ""),
        ),
    )


def _next_safe_actions(blockers: Sequence[str]) -> list[str]:
    if not blockers:
        return [
            "review AFST report as diagnostic evidence; do not dispatch providers or mark settled"
        ]
    return [
        "repair AFST residuals through evidence, authority, consent, refusal, buffer, "
        "balance, or handover routes",
        "emit CCR repair tasks with pic afst emit-ccr-tasks",
    ]
