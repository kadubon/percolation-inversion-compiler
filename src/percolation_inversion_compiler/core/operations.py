"""Operational readiness records for production and agent runners."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OperationalCheck(BaseModel):
    """One deterministic operational readiness check."""

    check_id: str
    status: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class OperationalReadinessReport(BaseModel):
    """Machine-readable environment report for CI and autonomous agents."""

    report_id: str = "pic-operational-readiness"
    package_version: str
    python_version: str
    overall_status: str
    checks: list[OperationalCheck] = Field(default_factory=list)
    summary: dict[str, object] = Field(default_factory=dict)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "registry entries are metadata, not evidence",
            "derived_status is checker-derived",
            "unresolved external obligations do not promote to settled",
            "snapshots are derived metadata and do not vendor TeX/PDF sources",
        ]
    )
