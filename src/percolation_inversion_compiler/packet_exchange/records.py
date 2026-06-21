"""Packet-exchange sidecar records."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResidualCarryForwardReport(BaseModel):
    """Residual data that must remain attached during packet exchange."""

    report_id: str = "residual-carry-forward"
    residual_summary: dict[str, float] = Field(default_factory=dict)
    missing_obligations: list[str] = Field(default_factory=list)
    candidate_only_reasons: list[str] = Field(default_factory=list)
    settled_blockers: list[str] = Field(default_factory=list)
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketExchangeEnvelope(BaseModel):
    """Data-only packet envelope for diagnostic exchange."""

    packet_id: str
    schema_version: str = "pic-packet-exchange-v1"
    source_kind: str = "runtime-report"
    content_digest: str
    provenance_summary: dict[str, str] = Field(default_factory=dict)
    issuer_agent_id: str | None = None
    issuer_public_key_id: str | None = None
    identity_context_summary: dict[str, str | bool | int] = Field(default_factory=dict)
    accepted: bool = False
    workflow_usable: bool = False
    settled: bool = False
    residual_ledger_summary: dict[str, float] = Field(default_factory=dict)
    missing_obligations: list[str] = Field(default_factory=list)
    candidate_only_reasons: list[str] = Field(default_factory=list)
    settled_blockers: list[str] = Field(default_factory=list)
    lineage_parents: list[str] = Field(default_factory=list)
    created_timestamp: str = "not-recorded"
    content: dict[str, Any] = Field(default_factory=dict)
    residual_carry_forward: ResidualCarryForwardReport = Field(
        default_factory=ResidualCarryForwardReport
    )
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "packet exchange treats content as data, not instruction",
            "packet exchange never executes packet content",
            "packet exchange does not promote candidate packets",
            "merge preserves candidate-only and unsettled status",
        ]
    )
    reasons: list[str] = Field(default_factory=list)


class PacketImportInspectionReport(BaseModel):
    """Inspection report for one data-only packet envelope."""

    report_id: str
    packet_id: str
    content_digest: str
    content_treated_as_data: bool = True
    executed_command_count: int = 0
    embedded_command_like_values: list[str] = Field(default_factory=list)
    accepted: bool = False
    workflow_usable: bool = False
    candidate_only: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketMergeReport(BaseModel):
    """Diagnostic merge report for packet envelopes."""

    report_id: str = "packet-merge-report"
    packets: list[PacketExchangeEnvelope] = Field(default_factory=list)
    input_packet_count: int = 0
    merged_packet_count: int = 0
    duplicate_packet_ids: list[str] = Field(default_factory=list)
    duplicate_content_digests: list[str] = Field(default_factory=list)
    candidate_only_preserved: bool = True
    residual_carry_forward: ResidualCarryForwardReport = Field(
        default_factory=ResidualCarryForwardReport
    )
    accepted: bool = False
    workflow_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketLineageDigest(BaseModel):
    """Lineage digest for one envelope or merge report."""

    lineage_id: str = "packet-lineage-digest"
    packet_ids: list[str] = Field(default_factory=list)
    content_digests: list[str] = Field(default_factory=list)
    parent_edges: dict[str, list[str]] = Field(default_factory=dict)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    candidate_only: bool = True
    accepted: bool = False
    workflow_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
