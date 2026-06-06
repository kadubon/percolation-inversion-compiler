"""Finite calibration and statistical-certificate records."""

from __future__ import annotations

from math import log, sqrt

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.algorithms import dkw_radius, good_turing_unseen
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus


class ConfidenceLedger(BaseModel):
    """Finite confidence ledger for a statistical certificate."""

    alpha: float
    sample_size: int
    residual_coordinates: dict[str, float] = Field(default_factory=dict)

    def ledger(self) -> Ledger:
        ledger = Ledger()
        for coordinate, value in self.residual_coordinates.items():
            ledger = ledger.add_coordinate(
                coordinate,
                value,
                kind=CoordinateKind.RESIDUAL,
            )
        return ledger


class SplitCertificate(BaseModel):
    """Training/holdout split certificate."""

    certificate_id: str
    train_size: int
    holdout_size: int
    selected_on_train: bool = False
    checked_on_holdout: bool = False
    selection_residual: float = 0.0

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if self.train_size <= 0 or self.holdout_size <= 0:
            reasons.append("split certificate requires positive train and holdout sizes")
        if not self.selected_on_train:
            reasons.append("model or quotient was not selected on training split")
        if not self.checked_on_holdout:
            reasons.append("certificate was not checked on holdout split")
        if self.selection_residual < 0:
            reasons.append("selection residual must be nonnegative")
        residual = Ledger()
        if self.selection_residual:
            residual = residual.add_coordinate(
                f"split:{self.certificate_id}:selection",
                self.selection_residual,
                kind=CoordinateKind.RESIDUAL,
            )
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=reasons,
            missing_obligations=[] if not reasons else [f"split:{self.certificate_id}"],
            residual_ledger=residual,
        )


class DKWCertificate(BaseModel):
    """Finite DKW calibration certificate."""

    sample_size: int
    alpha: float
    observed_radius: float | None = None

    def radius(self) -> float:
        return dkw_radius(self.sample_size, self.alpha)

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if self.sample_size <= 0:
            reasons.append("DKW sample size must be positive")
        if not 0.0 < self.alpha < 1.0:
            reasons.append("DKW alpha must be in (0, 1)")
        if self.observed_radius is not None and self.observed_radius < 0:
            reasons.append("observed radius must be nonnegative")
        radius = self.radius() if not reasons else 0.0
        residual = Ledger().add_coordinate("dkw:radius", radius, kind=CoordinateKind.RESIDUAL)
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=reasons,
            missing_obligations=[] if not reasons else ["dkw:finite-calibration"],
            residual_ledger=residual,
        )


class GoodTuringCertificate(BaseModel):
    """Good-Turing unseen-mass certificate with explicit charges."""

    species_counts: list[int]
    duplicate_rate: float = 0.0
    false_entry_rate: float = 0.0

    def unseen_mass(self) -> float:
        return good_turing_unseen(self.species_counts)

    def release(self) -> float:
        return max(0.0, self.unseen_mass() - self.duplicate_rate - self.false_entry_rate)

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if any(count < 0 for count in self.species_counts):
            reasons.append("species counts must be nonnegative")
        if self.duplicate_rate < 0 or self.false_entry_rate < 0:
            reasons.append("Good-Turing charges must be nonnegative")
        residual = Ledger()
        if not reasons:
            residual = residual.add_coordinate(
                "good-turing:unseen-mass",
                self.unseen_mass(),
                kind=CoordinateKind.RESIDUAL,
            )
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=reasons,
            missing_obligations=[] if not reasons else ["good-turing:counts"],
            residual_ledger=residual,
        )


class EProcessCertificate(BaseModel):
    """Finite e-process hook for time-uniform evidence."""

    e_values: list[float]
    alpha: float

    def lower_boundary(self) -> float:
        return 1.0 / self.alpha

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if not self.e_values:
            reasons.append("e-process requires at least one e-value")
        if any(value < 0 for value in self.e_values):
            reasons.append("e-values must be nonnegative")
        if not 0.0 < self.alpha < 1.0:
            reasons.append("e-process alpha must be in (0, 1)")
        accepted = not reasons and max(self.e_values, default=0.0) >= self.lower_boundary()
        if not accepted and not reasons:
            reasons.append("e-process boundary not crossed")
        residual = Ledger()
        if self.e_values and 0.0 < self.alpha < 1.0:
            residual = residual.add_coordinate(
                "e-process:boundary-gap",
                max(0.0, self.lower_boundary() - max(self.e_values)),
                kind=CoordinateKind.RESIDUAL,
            )
        return CheckResult(
            accepted=accepted,
            status=ClaimStatus.SETTLED if accepted else ClaimStatus.PROVISIONAL,
            reasons=reasons,
            missing_obligations=[] if accepted else ["e-process:boundary"],
            residual_ledger=residual,
        )


class MartingaleBlockResidual(BaseModel):
    """Self-normalized martingale block residual certificate."""

    block_bounds: list[float]
    quadratic_variation: float
    alpha: float
    drift_charge: float = 0.0

    def residual(self) -> float:
        if self.quadratic_variation < 0 or not 0.0 < self.alpha < 1.0:
            return 0.0
        return sqrt(2.0 * self.quadratic_variation * log(2.0 / self.alpha)) + abs(self.drift_charge)

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if not self.block_bounds:
            reasons.append("martingale certificate requires finite block bounds")
        if self.quadratic_variation < 0:
            reasons.append("quadratic variation must be nonnegative")
        if not 0.0 < self.alpha < 1.0:
            reasons.append("martingale alpha must be in (0, 1)")
        residual = Ledger().add_coordinate(
            "martingale:block-residual",
            self.residual(),
            kind=CoordinateKind.RESIDUAL,
        )
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=reasons,
            missing_obligations=[] if not reasons else ["martingale:block-certificate"],
            residual_ledger=residual,
        )


class CalibrationCertificate(BaseModel):
    """Aggregate finite calibration certificate."""

    split: SplitCertificate | None = None
    dkw: DKWCertificate | None = None
    good_turing: GoodTuringCertificate | None = None
    e_process: EProcessCertificate | None = None
    martingale: MartingaleBlockResidual | None = None
    confidence: ConfidenceLedger | None = None

    def check(self) -> CheckResult:
        results = [
            certificate.check()
            for certificate in [
                self.split,
                self.dkw,
                self.good_turing,
                self.e_process,
                self.martingale,
            ]
            if certificate is not None
        ]
        reasons: list[str] = []
        missing: list[str] = []
        ledger = self.confidence.ledger() if self.confidence is not None else Ledger()
        for result in results:
            reasons.extend(result.reasons)
            missing.extend(result.missing_obligations)
            ledger = ledger.combine(result.residual_ledger)
        accepted = bool(results) and all(result.accepted for result in results)
        if not results:
            reasons.append("calibration certificate has no finite components")
            missing.append("calibration:component")
        return CheckResult(
            accepted=accepted,
            status=ClaimStatus.SETTLED if accepted else ClaimStatus.PROVISIONAL,
            reasons=sorted(set(reasons)),
            missing_obligations=sorted(set(missing)),
            residual_ledger=ledger,
        )
