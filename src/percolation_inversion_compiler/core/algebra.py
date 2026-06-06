"""Finite algebraic law certificates for portable residual summaries."""

from __future__ import annotations

from itertools import product

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.checker import residual_from_reasons
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus


class MonoidRecord(BaseModel):
    """A finite monoid table."""

    elements: list[str]
    identity: str
    operation_table: dict[str, str]

    @staticmethod
    def key(left: str, right: str) -> str:
        return f"{left}|{right}"

    def op(self, left: str, right: str) -> str | None:
        return self.operation_table.get(self.key(left, right))

    def check(self) -> CheckResult:
        reasons: list[str] = []
        elements = set(self.elements)
        if self.identity not in elements:
            reasons.append("monoid identity is absent from elements")
        for left, right in product(self.elements, repeat=2):
            value = self.op(left, right)
            if value not in elements:
                reasons.append(f"operation is not closed for {left},{right}")
        for element in self.elements:
            if self.op(self.identity, element) != element:
                reasons.append(f"left identity law fails for {element}")
            if self.op(element, self.identity) != element:
                reasons.append(f"right identity law fails for {element}")
        for a, b, c in product(self.elements, repeat=3):
            left_mid = self.op(a, b)
            right_mid = self.op(b, c)
            if left_mid is None or right_mid is None:
                continue
            if self.op(left_mid, c) != self.op(a, right_mid):
                reasons.append(f"associativity fails for {a},{b},{c}")
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=sorted(set(reasons)),
            missing_obligations=[] if not reasons else ["monoid:laws"],
            residual_ledger=residual_from_reasons("monoid", reasons),
        )


class DomainTypedSemiring(BaseModel):
    """Finite semiring table with domain and coordinate metadata."""

    domain_id: str
    elements: list[str]
    zero: str
    one: str
    plus_table: dict[str, str]
    times_table: dict[str, str]
    coordinate_units: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def key(left: str, right: str) -> str:
        return f"{left}|{right}"

    def plus(self, left: str, right: str) -> str | None:
        return self.plus_table.get(self.key(left, right))

    def times(self, left: str, right: str) -> str | None:
        return self.times_table.get(self.key(left, right))

    def plus_monoid(self) -> MonoidRecord:
        return MonoidRecord(
            elements=self.elements,
            identity=self.zero,
            operation_table=self.plus_table,
        )

    def times_monoid(self) -> MonoidRecord:
        return MonoidRecord(
            elements=self.elements,
            identity=self.one,
            operation_table=self.times_table,
        )


class ReconstructionResidual(BaseModel):
    """Residual charged when an algebraic summary is decoded to a source ledger."""

    coordinate: str
    value: float
    unit: str = "dimensionless"

    def ledger(self) -> Ledger:
        return Ledger().add_coordinate(
            self.coordinate,
            self.value,
            unit=self.unit,
            kind=CoordinateKind.RESIDUAL,
        )


class AlgebraLawCertificate(BaseModel):
    """Finite semiring-law checker with reconstruction residual accounting."""

    semiring: DomainTypedSemiring
    reconstruction_residuals: list[ReconstructionResidual] = Field(default_factory=list)

    def check(self) -> CheckResult:
        reasons: list[str] = []
        elements = set(self.semiring.elements)
        if self.semiring.zero not in elements:
            reasons.append("semiring zero is absent from elements")
        if self.semiring.one not in elements:
            reasons.append("semiring one is absent from elements")
        plus_result = self.semiring.plus_monoid().check()
        times_result = self.semiring.times_monoid().check()
        reasons.extend(f"plus:{reason}" for reason in plus_result.reasons)
        reasons.extend(f"times:{reason}" for reason in times_result.reasons)
        for a, b, c in product(self.semiring.elements, repeat=3):
            bc_plus = self.semiring.plus(b, c)
            ab_plus = self.semiring.plus(a, b)
            if bc_plus is not None and self.semiring.times(a, bc_plus) != self.semiring.plus(
                self.semiring.times(a, b) or "",
                self.semiring.times(a, c) or "",
            ):
                reasons.append(f"left distributivity fails for {a},{b},{c}")
            if ab_plus is not None and self.semiring.times(ab_plus, c) != self.semiring.plus(
                self.semiring.times(a, c) or "",
                self.semiring.times(b, c) or "",
            ):
                reasons.append(f"right distributivity fails for {a},{b},{c}")
        for element in self.semiring.elements:
            if self.semiring.times(self.semiring.zero, element) != self.semiring.zero:
                reasons.append(f"left zero absorption fails for {element}")
            if self.semiring.times(element, self.semiring.zero) != self.semiring.zero:
                reasons.append(f"right zero absorption fails for {element}")
        residual = residual_from_reasons("semiring", reasons)
        for residual_record in self.reconstruction_residuals:
            residual = residual.combine(residual_record.ledger())
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=sorted(set(reasons)),
            missing_obligations=[] if not reasons else ["semiring:laws"],
            residual_ledger=residual,
        )


class FunctorLawCertificate(BaseModel):
    """Finite semiring homomorphism/functor law certificate."""

    source: DomainTypedSemiring
    target: DomainTypedSemiring
    mapping: dict[str, str]

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if set(self.mapping) != set(self.source.elements):
            reasons.append("functor mapping does not cover source elements")
        if any(value not in self.target.elements for value in self.mapping.values()):
            reasons.append("functor mapping targets unknown elements")
        if self.mapping.get(self.source.zero) != self.target.zero:
            reasons.append("functor does not preserve zero")
        if self.mapping.get(self.source.one) != self.target.one:
            reasons.append("functor does not preserve one")
        for left, right in product(self.source.elements, repeat=2):
            src_plus = self.source.plus(left, right)
            src_times = self.source.times(left, right)
            mapped_left = self.mapping.get(left)
            mapped_right = self.mapping.get(right)
            if (
                src_plus is not None
                and mapped_left is not None
                and mapped_right is not None
                and self.mapping.get(src_plus) != self.target.plus(mapped_left, mapped_right)
            ):
                reasons.append(f"functor does not preserve plus for {left},{right}")
            if (
                src_times is not None
                and mapped_left is not None
                and mapped_right is not None
                and self.mapping.get(src_times) != self.target.times(mapped_left, mapped_right)
            ):
                reasons.append(f"functor does not preserve times for {left},{right}")
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=sorted(set(reasons)),
            missing_obligations=[] if not reasons else ["functor:laws"],
            residual_ledger=residual_from_reasons("functor", reasons),
        )
