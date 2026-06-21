"""Data-only packet-exchange sidecar algorithms."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from percolation_inversion_compiler.packet_exchange.records import (
    PacketExchangeEnvelope,
    PacketImportInspectionReport,
    PacketLineageDigest,
    PacketMergeReport,
    ResidualCarryForwardReport,
)
from percolation_inversion_compiler.runtime.records import RuntimeStepReport

_COMMAND_MARKERS = (
    "cmd.exe",
    "powershell",
    "bash ",
    "sh ",
    "wsl ",
    "git ",
    "pip install",
    "python -m pip",
    "uv run",
    "rm -rf",
    "curl ",
    "wget ",
)


def stable_json_digest(data: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 digest for JSON-like data."""

    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def residual_summary_from_report(report: RuntimeStepReport) -> dict[str, float]:
    """Summarize residual ledger coordinates by kind."""

    summary: dict[str, float] = {}
    for coordinate in report.residual_ledger.coordinates.values():
        kind = getattr(coordinate.kind, "value", str(coordinate.kind))
        summary[kind] = summary.get(kind, 0.0) + float(coordinate.value)
    return dict(sorted(summary.items()))


def packet_exchange_envelope_from_runtime_report(
    report: RuntimeStepReport,
) -> PacketExchangeEnvelope:
    """Export a RuntimeStepReport as a data-only exchange envelope."""

    content = report.model_dump(mode="json")
    content_digest = stable_json_digest(content)
    residual_summary = residual_summary_from_report(report)
    candidate_only_reasons = [
        "runtime report is exported as diagnostic packet-exchange data",
        "packet exchange does not route promotion checks",
    ]
    settled_blockers = [
        "packet exchange is sidecar-only and cannot settle claims",
        *([] if report.settled else ["source runtime report settled=false"]),
        *report.missing_obligations,
    ]
    carry_forward = ResidualCarryForwardReport(
        report_id=f"residual-carry-forward:{report.report_id}",
        residual_summary=residual_summary,
        missing_obligations=report.missing_obligations,
        candidate_only_reasons=candidate_only_reasons,
        settled_blockers=settled_blockers,
        accepted=report.accepted,
        settled=False,
        reasons=["residuals and blockers are preserved during packet export"],
    )
    issuer_agent_id = None
    issuer_public_key_id = None
    if report.registry.packets:
        issuer_agent_id = report.registry.packets[0].issuer_agent_id
        issuer_public_key_id = report.registry.packets[0].issuer_public_key_id
    return PacketExchangeEnvelope(
        packet_id=f"packet-exchange:{report.report_id}:{content_digest[:12]}",
        source_kind="runtime-report",
        content_digest=content_digest,
        provenance_summary={
            "source_report_id": report.report_id,
            "state_id": report.state_id,
            "input_id": report.input_id,
        },
        issuer_agent_id=issuer_agent_id,
        issuer_public_key_id=issuer_public_key_id,
        identity_context_summary={
            "accepted_agent_context_present": bool(issuer_agent_id),
            "accepted_public_key_context_present": bool(issuer_public_key_id),
        },
        accepted=report.accepted,
        workflow_usable=bool(
            report.accepted or report.agent_tasks or report.route_execution_requests
        ),
        settled=False,
        residual_ledger_summary=residual_summary,
        missing_obligations=report.missing_obligations,
        candidate_only_reasons=candidate_only_reasons,
        settled_blockers=settled_blockers,
        lineage_parents=[report.report_id],
        content=content,
        residual_carry_forward=carry_forward,
        reasons=["exported packet is diagnostic data and is not promoted"],
    )


def inspect_packet_exchange_envelope(
    envelope: PacketExchangeEnvelope,
) -> PacketImportInspectionReport:
    """Inspect a packet envelope without executing its content."""

    command_like_values = sorted(set(_command_like_strings(envelope.model_dump(mode="json"))))
    return PacketImportInspectionReport(
        report_id=f"packet-inspection:{envelope.packet_id}",
        packet_id=envelope.packet_id,
        content_digest=envelope.content_digest,
        content_treated_as_data=True,
        executed_command_count=0,
        embedded_command_like_values=command_like_values,
        accepted=envelope.accepted,
        workflow_usable=envelope.workflow_usable,
        candidate_only=True,
        settled=False,
        reasons=[
            "packet content was inspected as inert data",
            "embedded command-like strings are not execution authority",
        ],
    )


def merge_packet_exchange_envelopes(
    envelopes: Iterable[PacketExchangeEnvelope],
) -> PacketMergeReport:
    """Merge packet envelopes by digest while preserving non-promotion status."""

    items = list(envelopes)
    by_digest: dict[str, PacketExchangeEnvelope] = {}
    duplicate_packet_ids: list[str] = []
    duplicate_digests: list[str] = []
    residual_summary: dict[str, float] = {}
    missing: set[str] = set()
    candidate_only: set[str] = set()
    blockers: set[str] = set()
    for envelope in items:
        if envelope.content_digest in by_digest:
            duplicate_packet_ids.append(envelope.packet_id)
            duplicate_digests.append(envelope.content_digest)
        else:
            by_digest[envelope.content_digest] = envelope
        for key, value in envelope.residual_ledger_summary.items():
            residual_summary[key] = residual_summary.get(key, 0.0) + float(value)
        missing.update(envelope.missing_obligations)
        candidate_only.update(envelope.candidate_only_reasons)
        blockers.update(envelope.settled_blockers)
    merged = list(by_digest.values())
    carry_forward = ResidualCarryForwardReport(
        report_id="residual-carry-forward:packet-merge",
        residual_summary=dict(sorted(residual_summary.items())),
        missing_obligations=sorted(missing),
        candidate_only_reasons=sorted(candidate_only),
        settled_blockers=sorted(blockers),
        accepted=bool(merged) and all(item.accepted for item in merged),
        settled=False,
        reasons=["merge preserves residuals and candidate-only blockers"],
    )
    return PacketMergeReport(
        packets=merged,
        input_packet_count=len(items),
        merged_packet_count=len(merged),
        duplicate_packet_ids=sorted(duplicate_packet_ids),
        duplicate_content_digests=sorted(set(duplicate_digests)),
        candidate_only_preserved=all(not packet.settled for packet in merged),
        residual_carry_forward=carry_forward,
        accepted=bool(merged) and all(item.accepted for item in merged),
        workflow_usable=bool(merged) and any(item.workflow_usable for item in merged),
        settled=False,
        reasons=["packet merge is diagnostic-only and does not promote packets"],
    )


def packet_lineage_digest(
    packet_or_merge: PacketExchangeEnvelope | PacketMergeReport,
) -> PacketLineageDigest:
    """Build a lineage digest from one envelope or merge report."""

    packets = (
        [packet_or_merge]
        if isinstance(packet_or_merge, PacketExchangeEnvelope)
        else packet_or_merge.packets
    )
    residual_summary: dict[str, float] = {}
    for packet in packets:
        for key, value in packet.residual_ledger_summary.items():
            residual_summary[key] = residual_summary.get(key, 0.0) + float(value)
    return PacketLineageDigest(
        packet_ids=[packet.packet_id for packet in packets],
        content_digests=[packet.content_digest for packet in packets],
        parent_edges={packet.packet_id: packet.lineage_parents for packet in packets},
        residual_summary=dict(sorted(residual_summary.items())),
        candidate_only=True,
        accepted=bool(packets) and all(packet.accepted for packet in packets),
        workflow_usable=bool(packets) and any(packet.workflow_usable for packet in packets),
        settled=False,
        reasons=["lineage digest is diagnostic-only and preserves candidate status"],
    )


def _command_like_strings(data: Any) -> list[str]:
    if isinstance(data, str):
        lowered = data.lower()
        return [data] if any(marker in lowered for marker in _COMMAND_MARKERS) else []
    if isinstance(data, dict):
        found: list[str] = []
        for value in data.values():
            found.extend(_command_like_strings(value))
        return found
    if isinstance(data, list):
        found = []
        for value in data:
            found.extend(_command_like_strings(value))
        return found
    return []
