"""Portable certificate-family records and non-promotion checkers."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.checker import CheckerContext, ObligationRule
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult, ExternalProofObligation
from percolation_inversion_compiler.core.status import ClaimStatus


class CertificateRoute(BaseModel):
    """Finite construction, verification, or settlement route."""

    route_id: str
    obligation_id: str
    accepted: bool = False
    cost: Ledger = Field(default_factory=Ledger)
    residual: Ledger = Field(default_factory=Ledger)
    failure_mode: str = "route-not-accepted"


class RefreshRule(BaseModel):
    """Finite expiry/refresh rule for certificate routes."""

    live_obligations: set[str] = Field(default_factory=set)
    expired_obligations: set[str] = Field(default_factory=set)
    refresh_obligations: set[str] = Field(default_factory=set)

    def accepted(self) -> bool:
        return not self.expired_obligations


class CertificateFamily(BaseModel):
    """A finite certificate family with construction/verifier/settlement routes."""

    family_id: str
    construction_routes: list[CertificateRoute] = Field(default_factory=list)
    verifier_routes: list[CertificateRoute] = Field(default_factory=list)
    settlement_routes: list[CertificateRoute] = Field(default_factory=list)
    refresh_rule: RefreshRule = Field(default_factory=RefreshRule)
    status_rule: ObligationRule | None = None
    external_obligations: list[ExternalProofObligation] = Field(default_factory=list)

    def present_obligations(self) -> set[str]:
        present: set[str] = set(self.refresh_rule.live_obligations)
        for route in self.construction_routes + self.verifier_routes + self.settlement_routes:
            if route.accepted:
                present.add(route.obligation_id)
        return present

    def residual_ledger(self) -> Ledger:
        ledger = Ledger()
        for route in self.construction_routes + self.verifier_routes + self.settlement_routes:
            ledger = ledger.combine(route.cost).combine(route.residual)
            if not route.accepted:
                ledger = ledger.add_coordinate(
                    f"{route.route_id}:{route.failure_mode}",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
        return ledger

    def check(self) -> CheckResult:
        present = self.present_obligations()
        context = CheckerContext(
            context_id=self.family_id,
            present_obligations=present,
            expired_obligations=self.refresh_rule.expired_obligations,
            external_obligations=self.external_obligations,
            residual_ledger=self.residual_ledger(),
        )
        if self.status_rule is None:
            rule = ObligationRule(
                rule_id=f"{self.family_id}:default",
                required_for_settled={
                    route.obligation_id
                    for route in self.construction_routes
                    + self.verifier_routes
                    + self.settlement_routes
                },
                required_for_provisional={
                    route.obligation_id for route in self.construction_routes + self.verifier_routes
                },
                required_for_speculative={
                    route.obligation_id for route in self.construction_routes
                },
                hard_domain_obligations=self.refresh_rule.live_obligations,
                external_obligation_ids={
                    obligation.obligation_id for obligation in self.external_obligations
                },
            )
        else:
            rule = self.status_rule
        result = rule.decide(context)
        if not self.refresh_rule.accepted():
            return result.model_copy(
                update={
                    "accepted": False,
                    "status": ClaimStatus.EXPIRED,
                    "reasons": [
                        *result.reasons,
                        "certificate family has expired obligations",
                    ],
                    "missing_obligations": sorted(
                        set(result.missing_obligations) | self.refresh_rule.expired_obligations
                    ),
                }
            )
        return result


class NonPromotionPolicy(BaseModel):
    """Declarative status policy for agent-facing integrations."""

    settled_requires: set[str] = Field(default_factory=set)
    provisional_requires: set[str] = Field(default_factory=set)
    speculative_requires: set[str] = Field(default_factory=set)
    hard_domain_requires: set[str] = Field(default_factory=set)

    def as_rule(self, rule_id: str) -> ObligationRule:
        return ObligationRule(
            rule_id=rule_id,
            required_for_settled=self.settled_requires,
            required_for_provisional=self.provisional_requires,
            required_for_speculative=self.speculative_requires,
            hard_domain_obligations=self.hard_domain_requires,
        )
