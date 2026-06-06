"""Typed finite ledgers and monotone burden accounting."""

from __future__ import annotations

from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, Field, field_validator


class CoordinateKind(StrEnum):
    BENEFIT = "benefit"
    BURDEN = "burden"
    RESIDUAL = "residual"
    TOLERANCE = "tolerance"
    RESOURCE = "resource"
    METADATA = "metadata"


class EvidenceStatus(StrEnum):
    VERIFIED = "verified"
    DECLARED = "declared"
    UNKNOWN = "unknown"


class LedgerCoordinate(BaseModel):
    """One typed coordinate in a finite certificate ledger."""

    name: str
    value: float
    unit: str = "dimensionless"
    kind: CoordinateKind = CoordinateKind.BURDEN
    description: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.DECLARED
    evidence_refs: list[str] = Field(default_factory=list)
    known: bool = True

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("ledger values must be finite")
        return value


class Ledger(BaseModel):
    """A finite typed ledger with explicit coordinate kinds."""

    coordinates: dict[str, LedgerCoordinate] = Field(default_factory=dict)

    @classmethod
    def from_values(
        cls,
        values: dict[str, float],
        *,
        kind: CoordinateKind | str = CoordinateKind.BURDEN,
        unit: str = "dimensionless",
    ) -> Ledger:
        coordinate_kind = CoordinateKind(kind)
        return cls(
            coordinates={
                name: LedgerCoordinate(name=name, value=value, unit=unit, kind=coordinate_kind)
                for name, value in values.items()
            }
        )

    def value(self, name: str, default: float = 0.0) -> float:
        coord = self.coordinates.get(name)
        return default if coord is None else coord.value

    def names(self) -> set[str]:
        return set(self.coordinates)

    def add_coordinate(
        self,
        name: str,
        value: float,
        *,
        unit: str = "dimensionless",
        kind: CoordinateKind | str = CoordinateKind.BURDEN,
        description: str | None = None,
    ) -> Ledger:
        data = self.model_copy(deep=True)
        coordinate_kind = CoordinateKind(kind)
        if name in data.coordinates:
            existing = data.coordinates[name]
            if existing.unit != unit or existing.kind != coordinate_kind:
                raise ValueError(f"coordinate {name!r} has incompatible unit or kind")
            value = existing.value + value
        data.coordinates[name] = LedgerCoordinate(
            name=name,
            value=value,
            unit=unit,
            kind=coordinate_kind,
            description=description,
        )
        return data

    def combine(self, other: Ledger) -> Ledger:
        result = self.model_copy(deep=True)
        for coord in other.coordinates.values():
            result = result.add_coordinate(
                coord.name,
                coord.value,
                unit=coord.unit,
                kind=coord.kind,
                description=coord.description,
            )
        return result

    def burden_sum(self) -> float:
        return sum(
            coord.value
            for coord in self.coordinates.values()
            if coord.kind
            in {CoordinateKind.BURDEN, CoordinateKind.RESIDUAL, CoordinateKind.TOLERANCE}
        )

    def benefit_sum(self) -> float:
        return sum(
            coord.value
            for coord in self.coordinates.values()
            if coord.kind == CoordinateKind.BENEFIT
        )

    def compatible_units(self, other: Ledger) -> bool:
        for name, coord in self.coordinates.items():
            other_coord = other.coordinates.get(name)
            if other_coord is not None and (
                coord.unit != other_coord.unit or coord.kind != other_coord.kind
            ):
                return False
        return True

    def dominates(self, other: Ledger, *, missing_as_zero: bool = False) -> bool:
        """Return true if this ledger is no worse coordinatewise.

        Benefits must be greater or equal. Burdens, residuals, tolerance charges,
        and resources must be less or equal. Metadata is ignored.
        """

        all_names = set(self.coordinates) | set(other.coordinates)
        comparable = False
        for name in all_names:
            left = self.coordinates.get(name)
            right = other.coordinates.get(name)
            if left is None:
                if not missing_as_zero:
                    return False
                if right is None:
                    return False
                left = LedgerCoordinate(
                    name=name,
                    value=0.0,
                    kind=right.kind,
                    unit=right.unit,
                    evidence_status=EvidenceStatus.UNKNOWN,
                    known=True,
                )
            if right is None:
                if not missing_as_zero:
                    return False
                if left is None:
                    return False
                right = LedgerCoordinate(
                    name=name,
                    value=0.0,
                    kind=left.kind,
                    unit=left.unit,
                    evidence_status=EvidenceStatus.UNKNOWN,
                    known=True,
                )
            if not left.known or not right.known:
                return False
            if left.unit != right.unit or left.kind != right.kind:
                return False
            if left.kind != CoordinateKind.METADATA:
                comparable = True
            if left.kind == CoordinateKind.BENEFIT:
                if left.value < right.value:
                    return False
            elif left.kind != CoordinateKind.METADATA and left.value > right.value:
                return False
        return comparable
