"""Finite order-theoretic kernels used by ECPT, BIT, and TRC."""

from __future__ import annotations

from itertools import combinations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.checker import residual_from_reasons
from percolation_inversion_compiler.core.ledger import CoordinateKind
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus


class DominanceWitness(BaseModel):
    """Certificate that one finite element is no worse than another."""

    left: str
    right: str
    accepted: bool
    reasons: list[str] = Field(default_factory=list)


class FiniteOrder(BaseModel):
    """A finite preorder/partial order represented by a finite relation."""

    elements: list[str]
    leq_pairs: list[tuple[str, str]] = Field(default_factory=list)

    def relation(self) -> set[tuple[str, str]]:
        pairs = set(self.leq_pairs)
        pairs.update((element, element) for element in self.elements)
        return pairs

    def leq(self, left: str, right: str) -> bool:
        if left not in self.elements or right not in self.elements:
            return False
        closure = self.transitive_closure()
        return (left, right) in closure

    def transitive_closure(self) -> set[tuple[str, str]]:
        closure = self.relation()
        changed = True
        while changed:
            changed = False
            new_pairs = set(closure)
            for a, b in closure:
                for c, d in closure:
                    if b == c and (a, d) not in new_pairs:
                        new_pairs.add((a, d))
                        changed = True
            closure = new_pairs
        return closure

    def is_reflexive(self) -> bool:
        rel = self.relation()
        return all((element, element) in rel for element in self.elements)

    def is_transitive(self) -> bool:
        closure = self.transitive_closure()
        for a, b in closure:
            for c, d in closure:
                if b == c and (a, d) not in closure:
                    return False
        return True

    def is_antisymmetric(self) -> bool:
        closure = self.transitive_closure()
        return all(a == b or (b, a) not in closure for a, b in closure)

    def is_preorder(self) -> bool:
        return self.is_reflexive() and self.is_transitive()

    def is_partial_order(self) -> bool:
        return self.is_reflexive() and self.is_transitive() and self.is_antisymmetric()

    def incomparable(self, left: str, right: str) -> bool:
        return not self.leq(left, right) and not self.leq(right, left)

    def antichain(self, candidates: list[str] | None = None) -> list[str]:
        selected: list[str] = []
        for candidate in sorted(candidates or self.elements):
            if all(self.incomparable(candidate, existing) for existing in selected):
                selected.append(candidate)
        return selected

    def maximal_antichain(self) -> list[str]:
        best: list[str] = []
        for size in range(1, len(self.elements) + 1):
            for subset in combinations(sorted(self.elements), size):
                if all(self.incomparable(a, b) for a, b in combinations(subset, 2)) and len(
                    subset
                ) > len(best):
                    best = list(subset)
        return best

    def dominance_witness(self, left: str, right: str) -> DominanceWitness:
        reasons: list[str] = []
        if left not in self.elements:
            reasons.append("left element absent from order")
        if right not in self.elements:
            reasons.append("right element absent from order")
        if not reasons and not self.leq(right, left):
            reasons.append("right is not below left")
        return DominanceWitness(left=left, right=right, accepted=not reasons, reasons=reasons)

    def check(self, *, partial: bool = True) -> CheckResult:
        reasons: list[str] = []
        if len(set(self.elements)) != len(self.elements):
            reasons.append("finite order has duplicate elements")
        if any(a not in self.elements or b not in self.elements for a, b in self.leq_pairs):
            reasons.append("order relation mentions unknown elements")
        if not self.is_transitive():
            reasons.append("order relation is not transitively closed")
        if partial and not self.is_antisymmetric():
            reasons.append("order relation is not antisymmetric")
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=reasons,
            missing_obligations=[] if not reasons else ["finite-order:laws"],
            residual_ledger=residual_from_reasons("finite-order", reasons),
        )


class ProductOrder(BaseModel):
    """Coordinatewise product order over named finite orders."""

    coordinate_orders: dict[str, FiniteOrder]

    def leq(self, left: dict[str, str], right: dict[str, str]) -> bool:
        return all(
            order.leq(left.get(name, ""), right.get(name, ""))
            for name, order in self.coordinate_orders.items()
        )


class MonotoneMap(BaseModel):
    """Finite monotone map between finite orders."""

    source: FiniteOrder
    target: FiniteOrder
    mapping: dict[str, str]

    def check(self) -> CheckResult:
        reasons: list[str] = []
        if set(self.mapping) != set(self.source.elements):
            reasons.append("monotone map does not cover the source order")
        if any(value not in self.target.elements for value in self.mapping.values()):
            reasons.append("monotone map targets unknown elements")
        for left, right in self.source.transitive_closure():
            mapped_left = self.mapping.get(left)
            mapped_right = self.mapping.get(right)
            if mapped_left is None or mapped_right is None:
                continue
            if not self.target.leq(mapped_left, mapped_right):
                reasons.append(f"monotonicity violation: {left}<={right}")
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=sorted(set(reasons)),
            missing_obligations=[] if not reasons else ["monotone-map:order-preservation"],
            residual_ledger=residual_from_reasons("monotone-map", reasons),
        )


class LatticeWitness(BaseModel):
    """Finite meet/join witness tables for a partial order."""

    order: FiniteOrder
    meet_table: dict[str, str] = Field(default_factory=dict)
    join_table: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def _key(left: str, right: str) -> str:
        return "|".join(sorted([left, right]))

    def check(self) -> CheckResult:
        reasons: list[str] = []
        order_result = self.order.check(partial=True)
        reasons.extend(order_result.reasons)
        for left, right in combinations(self.order.elements, 2):
            key = self._key(left, right)
            meet = self.meet_table.get(key)
            join = self.join_table.get(key)
            if meet is None or meet not in self.order.elements:
                reasons.append(f"missing meet for {key}")
            elif not self.order.leq(meet, left) or not self.order.leq(meet, right):
                reasons.append(f"meet is not a lower bound for {key}")
            if join is None or join not in self.order.elements:
                reasons.append(f"missing join for {key}")
            elif not self.order.leq(left, join) or not self.order.leq(right, join):
                reasons.append(f"join is not an upper bound for {key}")
        residual = residual_from_reasons("lattice", reasons)
        if reasons:
            residual = residual.add_coordinate(
                "lattice:law-failure",
                float(len(reasons)),
                kind=CoordinateKind.RESIDUAL,
            )
        return CheckResult(
            accepted=not reasons,
            status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
            reasons=sorted(set(reasons)),
            missing_obligations=[] if not reasons else ["lattice:meet-join"],
            residual_ledger=residual,
        )
