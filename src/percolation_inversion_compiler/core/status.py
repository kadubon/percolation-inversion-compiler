"""Claim status ordering and non-promotion discipline."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ClaimStatus(StrEnum):
    """Protocol-relative status labels used by ECPT, BIT, and TRC."""

    REJECTED = "rejected"
    EXPIRED = "expired"
    DIAGNOSTIC = "diagnostic"
    RELAXED = "relaxed"
    RISK_PROVISIONAL = "risk-provisional"
    SPECULATIVE = "speculative"
    PROVISIONAL = "provisional"
    PARTIAL = "partial"
    SETTLED = "settled"


_STATUS_RANK: dict[ClaimStatus, int] = {
    ClaimStatus.REJECTED: 0,
    ClaimStatus.EXPIRED: 1,
    ClaimStatus.DIAGNOSTIC: 2,
    ClaimStatus.RELAXED: 3,
    ClaimStatus.RISK_PROVISIONAL: 4,
    ClaimStatus.SPECULATIVE: 5,
    ClaimStatus.PROVISIONAL: 6,
    ClaimStatus.PARTIAL: 6,
    ClaimStatus.SETTLED: 7,
}


def status_rank(status: ClaimStatus | str) -> int:
    """Return a conservative rank where higher means no worse status."""

    return _STATUS_RANK[ClaimStatus(status)]


def no_worse_status(left: ClaimStatus | str, right: ClaimStatus | str) -> bool:
    """Return true when ``left`` is no worse than ``right``."""

    return status_rank(left) >= status_rank(right)


class StatusDecision(BaseModel):
    """A checker decision plus the reasons that constrained it."""

    status: ClaimStatus
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)
    missing_obligations: list[str] = Field(default_factory=list)


class StatusRule(BaseModel):
    """Finite non-promotion rule for one claim coordinate."""

    required_for_settled: set[str] = Field(default_factory=set)
    required_for_provisional: set[str] = Field(default_factory=set)
    required_for_speculative: set[str] = Field(default_factory=set)
    hard_domain_obligations: set[str] = Field(default_factory=set)

    def decide(self, present: set[str], expired: set[str] | None = None) -> StatusDecision:
        """Apply ECPT/BIT/TRC non-promotion logic to a finite obligation set."""

        expired = expired or set()
        hard_missing = sorted((self.hard_domain_obligations - present) | (expired & present))
        if hard_missing:
            return StatusDecision(
                status=ClaimStatus.REJECTED,
                accepted=False,
                reasons=["hard-domain obligation absent or expired"],
                missing_obligations=hard_missing,
            )

        settled_missing = sorted((self.required_for_settled - present) | (expired & present))
        if not settled_missing:
            return StatusDecision(status=ClaimStatus.SETTLED, accepted=True)

        provisional_missing = sorted(
            (self.required_for_provisional - present) | (expired & present)
        )
        if not provisional_missing:
            return StatusDecision(
                status=ClaimStatus.PROVISIONAL,
                accepted=True,
                reasons=["settled obligations missing; no status promotion"],
                missing_obligations=settled_missing,
            )

        speculative_missing = sorted(
            (self.required_for_speculative - present) | (expired & present)
        )
        if not speculative_missing:
            return StatusDecision(
                status=ClaimStatus.SPECULATIVE,
                accepted=True,
                reasons=["only speculative transition ledgers are complete"],
                missing_obligations=sorted(set(settled_missing) | set(provisional_missing)),
            )

        return StatusDecision(
            status=ClaimStatus.DIAGNOSTIC,
            accepted=False,
            reasons=["insufficient obligations for settled, provisional, or speculative claim"],
            missing_obligations=sorted(
                set(settled_missing) | set(provisional_missing) | set(speculative_missing)
            ),
        )
