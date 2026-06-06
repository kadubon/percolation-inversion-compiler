"""Deterministic finite domain-adapter checks for production evidence routes."""

from __future__ import annotations

from percolation_inversion_compiler.core.checker import residual_from_reasons
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus


def _domain_result(name: str, reasons: list[str], residual: Ledger | None = None) -> CheckResult:
    residual_ledger = residual or Ledger()
    residual_ledger = residual_ledger.combine(residual_from_reasons(name, reasons))
    accepted = not reasons
    return CheckResult(
        accepted=accepted,
        status=ClaimStatus.SETTLED if accepted else ClaimStatus.DIAGNOSTIC,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=accepted,
        reasons=sorted(set(reasons)),
        missing_obligations=[] if accepted else [f"{name}:accepted"],
        residual_ledger=residual_ledger,
    )


def verify_ecpt_numerical_envelope(
    *,
    residual: float,
    residual_bound: float,
    finite_horizon: int,
) -> CheckResult:
    """Check a finite ECPT numerical envelope without asserting limit behavior."""

    reasons: list[str] = []
    ledger = Ledger()
    if finite_horizon < 0:
        reasons.append("finite horizon is negative")
    if residual < 0 or residual_bound < 0:
        reasons.append("numerical envelope residuals must be nonnegative")
    if residual > residual_bound:
        reasons.append("numerical envelope residual exceeds certified bound")
        ledger = ledger.add_coordinate(
            "ecpt:numerical-envelope:gap",
            residual - residual_bound,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-numerical-envelope", reasons, ledger)


def verify_ecpt_generator_limit(
    *,
    observed_generation: float,
    certified_limit: float,
    residual_allowance: float = 0.0,
) -> CheckResult:
    """Check a finite generator-limit certificate."""

    reasons: list[str] = []
    ledger = Ledger()
    if certified_limit < 0 or observed_generation < 0 or residual_allowance < 0:
        reasons.append("generator limit inputs must be nonnegative")
    gap = observed_generation - certified_limit - residual_allowance
    if gap > 0:
        reasons.append("observed generation exceeds certified limit plus residual allowance")
        ledger = ledger.add_coordinate(
            "ecpt:generator-limit:excess",
            gap,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-generator-limit", reasons, ledger)


def verify_ecpt_bridge_reserve(
    bridge_relations: dict[str, str],
    required_relations: dict[str, str],
    *,
    reserve: float,
    minimum_reserve: float,
) -> CheckResult:
    """Check finite cross-theory bridge relations and reserve budget."""

    reasons: list[str] = []
    ledger = Ledger()
    if reserve < 0 or minimum_reserve < 0:
        reasons.append("bridge reserve inputs must be nonnegative")
    missing = sorted(
        key for key, target in required_relations.items() if bridge_relations.get(key) != target
    )
    if missing:
        reasons.append("bridge reserve is missing required finite relations")
    if reserve < minimum_reserve:
        reasons.append("bridge reserve is below certified minimum")
        ledger = ledger.add_coordinate(
            "ecpt:bridge-reserve:gap",
            minimum_reserve - reserve,
            kind=CoordinateKind.RESIDUAL,
        )
    for key in missing:
        ledger = ledger.add_coordinate(
            f"ecpt:bridge-reserve:missing:{key}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-bridge-reserve", reasons, ledger)


def verify_ecpt_trace_diagnostic_projection(
    projected_trace_ids: set[str],
    accepted_trace_ids: set[str],
    *,
    residual: float = 0.0,
) -> CheckResult:
    """Check finite trace-diagnostic projection containment."""

    reasons: list[str] = []
    ledger = Ledger()
    if residual < 0:
        reasons.append("trace diagnostic residual must be nonnegative")
    missing = sorted(projected_trace_ids - accepted_trace_ids)
    if missing:
        reasons.append("trace diagnostic projection contains unaccepted traces")
    if residual:
        ledger = ledger.add_coordinate(
            "ecpt:trace-diagnostic:residual",
            residual,
            kind=CoordinateKind.RESIDUAL,
        )
    for trace_id in missing:
        ledger = ledger.add_coordinate(
            f"ecpt:trace-diagnostic:missing:{trace_id}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-trace-diagnostic", reasons, ledger)


def verify_ecpt_domain_abstraction(
    abstraction_map: dict[str, str],
    required_targets: set[str],
    *,
    refinement_residual: float,
    residual_bound: float,
) -> CheckResult:
    """Check a finite ecology/ontology abstraction envelope."""

    reasons: list[str] = []
    ledger = Ledger()
    if refinement_residual < 0 or residual_bound < 0:
        reasons.append("domain abstraction residuals must be nonnegative")
    if refinement_residual > residual_bound:
        reasons.append("domain abstraction refinement residual exceeds bound")
        ledger = ledger.add_coordinate(
            "ecpt:domain-abstraction:residual-gap",
            refinement_residual - residual_bound,
            kind=CoordinateKind.RESIDUAL,
        )
    missing_targets = sorted(required_targets - set(abstraction_map.values()))
    if missing_targets:
        reasons.append("domain abstraction misses required target concepts")
    for target in missing_targets:
        ledger = ledger.add_coordinate(
            f"ecpt:domain-abstraction:missing:{target}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-domain-abstraction", reasons, ledger)


def verify_ecpt_execution_policy(
    policy_actions: set[str],
    available_actions: set[str],
    *,
    counterfactual_residual: float,
    residual_bound: float,
) -> CheckResult:
    """Check a finite execution-policy/counterfactual envelope."""

    reasons: list[str] = []
    ledger = Ledger()
    if counterfactual_residual < 0 or residual_bound < 0:
        reasons.append("execution-policy residuals must be nonnegative")
    unavailable = sorted(policy_actions - available_actions)
    if unavailable:
        reasons.append("execution policy references unavailable actions")
    if counterfactual_residual > residual_bound:
        reasons.append("execution policy counterfactual residual exceeds bound")
        ledger = ledger.add_coordinate(
            "ecpt:execution-policy:residual-gap",
            counterfactual_residual - residual_bound,
            kind=CoordinateKind.RESIDUAL,
        )
    for action in unavailable:
        ledger = ledger.add_coordinate(
            f"ecpt:execution-policy:unavailable:{action}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-execution-policy", reasons, ledger)


def verify_ecpt_proxy_target_contract(
    proxy_coordinates: dict[str, float],
    required_coordinates: dict[str, float],
    *,
    mismatch_residual: float,
    residual_bound: float,
) -> CheckResult:
    """Check finite proxy-target grounding coordinates."""

    reasons: list[str] = []
    ledger = Ledger()
    if mismatch_residual < 0 or residual_bound < 0:
        reasons.append("proxy-target residuals must be nonnegative")
    for coordinate, floor in required_coordinates.items():
        value = proxy_coordinates.get(coordinate, 0.0)
        if value < floor:
            reasons.append(f"proxy coordinate {coordinate} is below required floor")
            ledger = ledger.add_coordinate(
                f"ecpt:proxy-target:{coordinate}:gap",
                floor - value,
                kind=CoordinateKind.RESIDUAL,
            )
    if mismatch_residual > residual_bound:
        reasons.append("proxy-target mismatch residual exceeds bound")
        ledger = ledger.add_coordinate(
            "ecpt:proxy-target:mismatch-gap",
            mismatch_residual - residual_bound,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-proxy-target", reasons, ledger)


def verify_ecpt_speculative_channel_repair(
    channels: set[str],
    repaired_channels: set[str],
    required_channels: set[str],
    *,
    repair_residual: float,
    residual_bound: float,
) -> CheckResult:
    """Check finite speculative-channel coverage and repair evidence."""

    reasons: list[str] = []
    ledger = Ledger()
    if repair_residual < 0 or residual_bound < 0:
        reasons.append("speculative-channel residuals must be nonnegative")
    missing = sorted(required_channels - (channels | repaired_channels))
    if missing:
        reasons.append("speculative channel repair misses required channels")
    if repair_residual > residual_bound:
        reasons.append("speculative channel repair residual exceeds bound")
        ledger = ledger.add_coordinate(
            "ecpt:speculative-channel:residual-gap",
            repair_residual - residual_bound,
            kind=CoordinateKind.RESIDUAL,
        )
    for channel in missing:
        ledger = ledger.add_coordinate(
            f"ecpt:speculative-channel:missing:{channel}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("ecpt-speculative-channel", reasons, ledger)


def verify_trc_telemetry_calibration(
    samples: list[float],
    references: list[float],
    *,
    tolerance: float,
) -> CheckResult:
    """Check bounded absolute calibration error over finite telemetry samples."""

    reasons: list[str] = []
    ledger = Ledger()
    if len(samples) != len(references):
        reasons.append("telemetry samples and references must have equal length")
    if not samples:
        reasons.append("telemetry calibration requires at least one sample")
    if tolerance < 0:
        reasons.append("telemetry tolerance must be nonnegative")
    if not reasons:
        max_error = max(
            abs(sample - reference) for sample, reference in zip(samples, references, strict=True)
        )
        if max_error > tolerance:
            reasons.append("telemetry calibration error exceeds tolerance")
            ledger = ledger.add_coordinate(
                "trc:telemetry-calibration:error-gap",
                max_error - tolerance,
                kind=CoordinateKind.RESIDUAL,
            )
    return _domain_result("trc-telemetry-calibration", reasons, ledger)


def replay_trc_physical_trace(
    events: list[str],
    expected_events: list[str],
    *,
    allow_prefix: bool = False,
) -> CheckResult:
    """Replay a finite physical trace against an expected transition log."""

    reasons: list[str] = []
    if not expected_events:
        reasons.append("expected physical trace is empty")
    if allow_prefix:
        accepted = expected_events[: len(events)] == events
    else:
        accepted = events == expected_events
    if not accepted:
        reasons.append("physical trace does not match expected transition log")
    return _domain_result("trc-physical-trace", reasons)


def verify_archive_domain_evidence(
    record_domains: dict[str, str],
    allowed_domains: set[str],
) -> CheckResult:
    """Check finite archive records against an explicit allowed-domain set."""

    reasons: list[str] = []
    if not allowed_domains:
        reasons.append("archive-domain evidence has no allowed domains")
    unknown = sorted(
        record_id for record_id, domain in record_domains.items() if domain not in allowed_domains
    )
    if unknown:
        reasons.append("archive records reference domains outside the certified domain set")
    ledger = Ledger()
    for record_id in unknown:
        ledger = ledger.add_coordinate(
            f"trc:archive-domain:{record_id}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _domain_result("trc-archive-domain", reasons, ledger)
