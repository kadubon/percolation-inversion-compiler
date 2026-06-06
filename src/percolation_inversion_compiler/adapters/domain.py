"""Deterministic finite domain-adapter checks for v0.2.1 evidence routes."""

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
