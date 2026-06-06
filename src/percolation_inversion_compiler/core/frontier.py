"""Pareto, antichain, and archive truncation utilities."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.status import ClaimStatus, no_worse_status


class FrontierRecord(BaseModel):
    """One typed frontier/archive record."""

    record_id: str
    benefits: dict[str, float] = Field(default_factory=dict)
    burdens: dict[str, float] = Field(default_factory=dict)
    status: ClaimStatus = ClaimStatus.PROVISIONAL
    stratum: str = "main"
    domain_key: str = "global"
    trace_id: str | None = None
    residual_ledger: Ledger = Field(default_factory=Ledger)
    metadata: dict[str, object] = Field(default_factory=dict)

    def ledger(self) -> Ledger:
        ledger = Ledger()
        for name, value in self.benefits.items():
            ledger = ledger.add_coordinate(name, value, kind=CoordinateKind.BENEFIT)
        for name, value in self.burdens.items():
            ledger = ledger.add_coordinate(name, value, kind=CoordinateKind.BURDEN)
        return ledger.combine(self.residual_ledger)


def dominates(
    left: FrontierRecord,
    right: FrontierRecord,
    *,
    require_same_stratum: bool = True,
    epsilon: float = 0.0,
) -> bool:
    """Return true when ``left`` epsilon-dominates ``right``."""

    if require_same_stratum and left.stratum != right.stratum:
        return False
    if left.domain_key != right.domain_key:
        return False
    if not no_worse_status(left.status, right.status):
        return False
    benefit_names = set(left.benefits) & set(right.benefits)
    burden_names = set(left.burdens) & set(right.burdens)
    if not benefit_names and not burden_names:
        return False
    strict_improvement = False
    for name in benefit_names:
        if left.benefits.get(name, 0.0) + epsilon < right.benefits.get(name, 0.0):
            return False
        if left.benefits.get(name, 0.0) > right.benefits.get(name, 0.0) + epsilon:
            strict_improvement = True
    for name in burden_names:
        if left.burdens.get(name, 0.0) > right.burdens.get(name, 0.0) + epsilon:
            return False
        if left.burdens.get(name, 0.0) + epsilon < right.burdens.get(name, 0.0):
            strict_improvement = True
    return left.record_id != right.record_id and strict_improvement


def pareto_frontier(records: list[FrontierRecord], *, epsilon: float = 0.0) -> list[FrontierRecord]:
    """Return records not dominated by any other compatible record."""

    frontier: list[FrontierRecord] = []
    for candidate in records:
        if any(dominates(other, candidate, epsilon=epsilon) for other in records):
            continue
        frontier.append(candidate)
    return sorted(frontier, key=lambda item: item.record_id)


class ArchiveResult(BaseModel):
    retained: list[FrontierRecord]
    truncated: list[FrontierRecord] = Field(default_factory=list)
    truncation_residual: Ledger = Field(default_factory=Ledger)


def archive_with_truncation(
    records: list[FrontierRecord],
    *,
    cap: int,
    epsilon: float = 0.0,
) -> ArchiveResult:
    """Build an epsilon Pareto archive and charge cap deletions as residuals."""

    if cap < 1:
        raise ValueError("archive cap must be positive")
    frontier = pareto_frontier(records, epsilon=epsilon)
    retained = frontier[:cap]
    truncated = frontier[cap:]
    residual = Ledger()
    for record in truncated:
        residual = residual.add_coordinate(
            f"truncated:{record.record_id}",
            max(record.burdens.values(), default=0.0) + max(record.benefits.values(), default=0.0),
            kind=CoordinateKind.RESIDUAL,
        )
    return ArchiveResult(retained=retained, truncated=truncated, truncation_residual=residual)
