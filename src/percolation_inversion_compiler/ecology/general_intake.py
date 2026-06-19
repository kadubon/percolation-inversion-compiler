"""Bounded general intake for web, feed, JSON, NDJSON, and agent messages."""

from __future__ import annotations

import importlib
import ipaddress
import json
import re
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.ecology.algorithms import packet_from_text, sha256_text
from percolation_inversion_compiler.ecology.connectors import ingest_live_source
from percolation_inversion_compiler.ecology.records import (
    AgentInboxRecord,
    AgentMessageContractReport,
    AgentMessageDeliveryReport,
    AgentMessageEnvelope,
    AgentMessageNonceLedger,
    AgentMessageVerificationContext,
    AgentPacketExchangeReport,
    AgentRelayReadinessReport,
    CapabilityPacketCandidate,
    ExternalCandidateClassification,
    GeneralIntakePolicy,
    GeneralIntakePolicyDecision,
    GeneralIntakeProfile,
    GeneralIntakeReport,
    GeneralIntakeRuntimeBridgeReport,
    GeneralIntakeSource,
    IntakeProvenanceRecord,
    PacketIngestionReport,
    PacketSourceKind,
    RobotsDecision,
    WebDiscoveryReport,
    WebFetchPolicy,
    WebFetchReport,
)


def ingest_general_source(
    source: str | GeneralIntakeSource,
    policy: GeneralIntakePolicy | None = None,
    identity_context: AgentMessageVerificationContext | None = None,
) -> GeneralIntakeReport:
    """Ingest one bounded source into packet candidates or diagnostic residuals."""

    active_policy = policy or GeneralIntakePolicy()
    descriptor = (
        source if isinstance(source, GeneralIntakeSource) else GeneralIntakeSource(source=source)
    )
    descriptor_policy = _policy_for_descriptor(active_policy, descriptor)
    kind = _infer_general_kind(descriptor.source, descriptor.kind)
    if kind not in set(active_policy.allowed_source_kinds):
        return _with_intake_metadata(
            _diagnostic_general_report(kind, descriptor.source, "source kind not allowed"),
            active_policy,
        )
    if kind in {PacketSourceKind.GITHUB, PacketSourceKind.ZENODO, PacketSourceKind.ARXIV}:
        report = (
            ingest_live_source(descriptor.source, kind=kind)
            if descriptor_policy.allow_live_connectors
            else _diagnostic_packet_report(
                kind,
                descriptor.source,
                "live connector source requires allow_live_connectors=true in source "
                "descriptor and policy/runtime config",
            )
        )
        return _general_from_reports(descriptor.source, kind, [report], descriptor_policy)
    if kind in {PacketSourceKind.HTTP, PacketSourceKind.WEB_PAGE}:
        report = _ingest_text_or_web(descriptor.source, kind, descriptor_policy)
        return _general_from_reports(descriptor.source, kind, [report], descriptor_policy)
    if kind in {
        PacketSourceKind.RSS,
        PacketSourceKind.ATOM,
        PacketSourceKind.JSON_FEED,
        PacketSourceKind.NDJSON,
    }:
        return ingest_feed(descriptor.source, descriptor_policy, kind=kind)
    if kind == PacketSourceKind.AGENT_MESSAGE:
        try:
            message = _message_from_source(descriptor.source, active_policy)
        except ValueError as exc:
            return _with_intake_metadata(
                _diagnostic_general_report(kind, descriptor.source, str(exc)), active_policy
            )
        return _general_from_exchange(
            descriptor.source,
            verify_agent_message(message, active_policy, identity_context),
            active_policy,
        )
    if kind == PacketSourceKind.AGENT_INBOX:
        return ingest_agent_inbox(descriptor.source, active_policy, identity_context)
    if kind == PacketSourceKind.WEB_CRAWL:
        discovery = discover_web_packets(descriptor.source, descriptor_policy.web_policy)
        return _with_intake_metadata(
            GeneralIntakeReport(
                report_id=f"general-intake:web-crawl:{sha256_text(descriptor.source)[:12]}",
                source=sanitize_intake_source_ref(descriptor.source),
                source_kind=kind,
                accepted=discovery.accepted,
                packets=discovery.packets,
                discovered_links=discovery.discovered_links,
                rejected_sources=discovery.rejected_sources,
                residual_ledger=discovery.residual_ledger,
                provenance=discovery.provenance,
                web_fetch_reports=discovery.web_fetch_reports,
                reasons=discovery.reasons,
                settled=False,
            ),
            descriptor_policy,
        )
    return _with_intake_metadata(
        _diagnostic_general_report(
            kind, descriptor.source, f"unsupported source kind {kind.value}"
        ),
        active_policy,
    )


def fetch_http_resource(source: str, policy: WebFetchPolicy | None = None) -> PacketIngestionReport:
    """Fetch one HTTP(S) text resource under a bounded fail-closed policy."""

    text, report = _fetch_http_text(source, policy or WebFetchPolicy())
    if text is None:
        return report
    return _packet_report_from_text(
        source,
        text,
        PacketSourceKind.WEB_PAGE,
        tags=["web", "http"],
        provenance=report.provenance,
        web_fetch_reports=report.web_fetch_reports,
    )


def general_intake_to_packet_ingestion(
    report: GeneralIntakeReport,
) -> PacketIngestionReport:
    """Convert a general intake report to the runtime packet-ingestion shape."""

    return PacketIngestionReport(
        report_id=f"packet-ingestion:general:{sha256_text(report.report_id)[:12]}",
        accepted=report.accepted,
        source_kind=report.source_kind,
        packets=report.packets,
        rejected_sources=report.rejected_sources,
        reasons=report.reasons,
        residual_ledger=report.residual_ledger,
        provenance=report.provenance,
        web_fetch_reports=report.web_fetch_reports,
    )


def general_intake_policy_for_profile(profile: str) -> GeneralIntakePolicy:
    """Return a deterministic policy preset for a general-intake profile."""

    normalized = profile.replace("-", "_").lower()
    if normalized == GeneralIntakeProfile.LOCAL_ONLY.value:
        return GeneralIntakePolicy(
            profile=GeneralIntakeProfile.LOCAL_ONLY.value,
            allow_live_connectors=False,
            allowed_source_kinds=[
                PacketSourceKind.LOCAL,
                PacketSourceKind.AGENT_OUTPUT,
                PacketSourceKind.RSS,
                PacketSourceKind.ATOM,
                PacketSourceKind.JSON_FEED,
                PacketSourceKind.NDJSON,
                PacketSourceKind.WEB_PAGE,
                PacketSourceKind.AGENT_MESSAGE,
                PacketSourceKind.AGENT_INBOX,
            ],
            web_policy=WebFetchPolicy(
                allow_live_connectors=False,
                max_pages=4,
                max_total_packets_per_run=64,
            ),
        )
    if normalized == GeneralIntakeProfile.CONTROLLED_WEB.value:
        return GeneralIntakePolicy(
            profile=GeneralIntakeProfile.CONTROLLED_WEB.value,
            allow_live_connectors=True,
            web_policy=WebFetchPolicy(
                allow_live_connectors=True,
                max_depth=1,
                max_pages=8,
                max_total_bytes_per_run=4_000_000,
                max_total_packets_per_run=128,
                robots_uncertainty_is_diagnostic=False,
            ),
        )
    if normalized == GeneralIntakeProfile.FEDERATED_AGENTS.value:
        return GeneralIntakePolicy(
            profile=GeneralIntakeProfile.FEDERATED_AGENTS.value,
            allow_live_connectors=True,
            allowed_source_kinds=[
                PacketSourceKind.AGENT_MESSAGE,
                PacketSourceKind.AGENT_INBOX,
                PacketSourceKind.JSON_FEED,
                PacketSourceKind.NDJSON,
            ],
            require_signed_agent_messages=True,
            require_message_identity_context=True,
            web_policy=WebFetchPolicy(allow_live_connectors=True, max_total_packets_per_run=128),
        )
    if normalized == GeneralIntakeProfile.PRODUCTION_NETWORK.value:
        return GeneralIntakePolicy(
            profile=GeneralIntakeProfile.PRODUCTION_NETWORK.value,
            allow_live_connectors=True,
            require_signed_agent_messages=True,
            require_message_identity_context=True,
            web_policy=WebFetchPolicy(
                allow_live_connectors=True,
                max_depth=1,
                max_pages=8,
                max_total_bytes_per_run=4_000_000,
                max_total_packets_per_run=128,
                require_https_for_live=True,
                require_robots_decision=True,
                robots_uncertainty_is_diagnostic=True,
            ),
        )
    if normalized == GeneralIntakeProfile.ADVERSARIAL_NETWORK.value:
        return GeneralIntakePolicy(
            profile=GeneralIntakeProfile.ADVERSARIAL_NETWORK.value,
            allow_live_connectors=True,
            require_signed_agent_messages=True,
            require_message_identity_context=True,
            max_feed_entries=64,
            max_agent_messages_per_inbox=64,
            web_policy=WebFetchPolicy(
                allow_live_connectors=True,
                max_redirects=1,
                max_depth=0,
                max_pages=4,
                max_bytes_per_resource=500_000,
                max_total_bytes_per_run=1_000_000,
                max_total_packets_per_run=32,
                require_https_for_live=True,
                require_robots_decision=True,
                robots_uncertainty_is_diagnostic=True,
            ),
        )
    return GeneralIntakePolicy(profile=profile)


def audit_general_intake_report(
    report: GeneralIntakeReport,
    policy: GeneralIntakePolicy | None = None,
) -> GeneralIntakeRuntimeBridgeReport:
    """Audit one general intake report against candidate-only runtime rules."""

    return bridge_general_intake_to_runtime(report, policy)


def bridge_general_intake_to_runtime(
    report: GeneralIntakeReport,
    policy: GeneralIntakePolicy | None = None,
) -> GeneralIntakeRuntimeBridgeReport:
    """Classify external candidates for SQOT/runtime scheduling."""

    active_policy = policy or GeneralIntakePolicy(profile=report.intake_profile)
    ingestion = general_intake_to_packet_ingestion(report)
    classifications: dict[str, ExternalCandidateClassification] = {}
    verifier_work: list[str] = []
    diagnostic_work: list[str] = []
    quarantine: list[str] = []
    queue_records: list[str] = []
    for packet in sorted(report.packets, key=lambda item: item.packet_id):
        classification = classify_external_candidate_for_sqot(
            packet, report.provenance, active_policy
        )
        classifications[packet.packet_id] = classification
        queue_records.append(f"queue:{classification.value}:{packet.packet_id}")
        if classification == ExternalCandidateClassification.VERIFIER_WORK:
            verifier_work.append(packet.packet_id)
        elif classification == ExternalCandidateClassification.QUARANTINE_WORK:
            quarantine.append(packet.packet_id)
        else:
            diagnostic_work.append(packet.packet_id)
    reasons = list(report.reasons)
    if report.total_candidate_packets > active_policy.web_policy.max_total_packets_per_run:
        reasons.append("candidate packet count exceeds max_total_packets_per_run")
    if report.total_bytes_read > active_policy.web_policy.max_total_bytes_per_run:
        reasons.append("intake byte count exceeds max_total_bytes_per_run")
    accepted = report.accepted and not quarantine and not reasons
    return GeneralIntakeRuntimeBridgeReport(
        report_id=f"general-intake-bridge:{sha256_text(report.report_id)[:12]}",
        source_report_id=report.report_id,
        accepted=accepted,
        packet_ingestion=ingestion,
        classifications={key: value for key, value in sorted(classifications.items())},
        sqot_queue_records=sorted(queue_records),
        verifier_work_packet_ids=sorted(verifier_work),
        diagnostic_work_packet_ids=sorted(diagnostic_work),
        quarantine_packet_ids=sorted(quarantine),
        ecpt_phase_contribution_allowed=False,
        residual_ledger=report.residual_ledger,
        reasons=sorted(set(reasons)),
    )


def classify_external_candidate_for_sqot(
    packet: CapabilityPacketCandidate,
    provenance: list[IntakeProvenanceRecord] | None = None,
    policy: GeneralIntakePolicy | None = None,
) -> ExternalCandidateClassification:
    """Classify one external packet candidate for SQOT queue routing."""

    _ = provenance, policy
    if not packet.evidence_hash_valid or not packet.route_safe or packet.hazard_charge > 0.0:
        return ExternalCandidateClassification.QUARANTINE_WORK
    if packet.verifier_routes:
        return ExternalCandidateClassification.VERIFIER_WORK
    if "external-candidate" in set(packet.tags) or packet.residual_charge > 0.0:
        return ExternalCandidateClassification.DIAGNOSTIC_WORK
    return ExternalCandidateClassification.CANDIDATE_ONLY


def check_agent_message_contract(message: AgentMessageEnvelope) -> AgentMessageContractReport:
    """Check portable agent-message envelope contract without trusting the content."""

    residual = Ledger()
    reasons: list[str] = []
    if message.protocol_version != "pic-agent-message-v1":
        reasons.append("unsupported agent message protocol_version")
    if not message.message_id:
        reasons.append("message_id is required")
    if not message.sender_agent_id:
        reasons.append("sender_agent_id is required")
    if sha256_text(message.content) != message.content_sha256:
        reasons.append("message content digest mismatch")
    if message.declared_packet_kind != "capability-packet-candidate":
        reasons.append("declared_packet_kind must remain capability-packet-candidate")
    if not message.declared_validity_domain:
        reasons.append("declared_validity_domain is required")
    if not message.declared_receiver_family:
        reasons.append("declared_receiver_family must be nonempty")
    for index, _reason in enumerate(reasons):
        residual = residual.add_coordinate(
            f"agent-message-contract:{message.message_id or 'missing'}:{index}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons
    return AgentMessageContractReport(
        report_id=f"agent-message-contract:{sha256_text(message.message_id)[:12]}",
        message_id=message.message_id,
        accepted=accepted,
        protocol_version=message.protocol_version,
        message_contract_valid=accepted,
        sender_agent_id=message.sender_agent_id,
        receiver_agent_id=message.receiver_agent_id,
        declared_packet_kind=message.declared_packet_kind,
        declared_validity_domain=message.declared_validity_domain,
        declared_receiver_family=message.declared_receiver_family,
        route_request_refs=message.route_request_refs,
        evidence_refs=message.evidence_refs,
        reasons=sorted(set(reasons)),
        residual_ledger=residual,
    )


def sanitize_intake_source_ref(source: str) -> str:
    """Return a public, deterministic source reference without secrets or local paths."""

    stripped = source.strip()
    parsed = urlparse(stripped)
    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or parsed.netloc
        netloc = host
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        url_path = parsed.path or "/"
        return urlunparse((parsed.scheme, netloc, url_path, "", "", ""))
    local_path = _safe_path(stripped)
    if (
        local_path is not None and (_path_exists(local_path) or local_path.is_absolute())
    ) or re.match(r"^[A-Za-z]:[\\/]", stripped):
        return (local_path.name if local_path is not None else "") or "local-source"
    if stripped.startswith(("{", "[")):
        return f"inline-json:{sha256_text(stripped)[:12]}"
    if "\n" in stripped or len(stripped) > 160:
        return f"literal:{sha256_text(stripped)[:12]}"
    return stripped


def discover_web_packets(
    seed: str,
    policy: WebFetchPolicy | None = None,
) -> WebDiscoveryReport:
    """Boundedly discover web packet candidates without executing page code."""

    active_policy = policy or WebFetchPolicy()
    visited: list[str] = []
    visited_raw: set[str] = set()
    discovered: list[str] = []
    packets: list[CapabilityPacketCandidate] = []
    rejected: list[str] = []
    provenance: list[IntakeProvenanceRecord] = []
    web_fetch_reports: list[WebFetchReport] = []
    reasons: list[str] = []
    residual = Ledger()
    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    seed_is_live = seed.startswith(("http://", "https://"))
    while queue and len(visited) < active_policy.max_pages:
        source, depth = queue.popleft()
        if source in visited_raw:
            continue
        visited_raw.add(source)
        report, text = _ingest_text_or_web_with_text(
            source,
            PacketSourceKind.WEB_PAGE,
            GeneralIntakePolicy(
                allow_live_connectors=active_policy.allow_live_connectors, web_policy=active_policy
            ),
        )
        visited.append(sanitize_intake_source_ref(source))
        provenance.extend(report.provenance)
        web_fetch_reports.extend(report.web_fetch_reports)
        if not report.accepted:
            rejected.extend(report.rejected_sources or [sanitize_intake_source_ref(source)])
            reasons.extend(report.reasons)
            residual = residual.combine(report.residual_ledger)
            continue
        packets.extend(report.packets)
        if text is None:
            reasons.append("link extraction source unavailable: source text was not retained")
            residual = residual.add_coordinate(
                f"general-intake:web-crawl:{sha256_text(source)[:8]}:link-extraction",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            continue
        links = _extract_links(text, source)[: active_policy.max_pages]
        for link in links:
            if link not in discovered:
                discovered.append(sanitize_intake_source_ref(link))
            if link.startswith(("http://", "https://")) and (
                not active_policy.allow_live_connectors or not seed_is_live
            ):
                continue
            if (
                depth + 1 <= active_policy.max_depth
                and len(visited) + len(queue) < active_policy.max_pages
            ):
                queue.append((link, depth + 1))
    accepted = bool(packets) and not reasons
    return WebDiscoveryReport(
        report_id=f"web-discovery:{sha256_text(seed)[:12]}",
        seed=sanitize_intake_source_ref(seed),
        accepted=accepted,
        visited=sorted(set(visited)),
        discovered_links=sorted(set(discovered)),
        packets=sorted(packets, key=lambda packet: packet.packet_id),
        rejected_sources=sorted({sanitize_intake_source_ref(source) for source in rejected}),
        residual_ledger=residual,
        provenance=sorted(provenance, key=lambda item: item.provenance_id),
        web_fetch_reports=sorted(web_fetch_reports, key=lambda item: item.report_id),
        reasons=sorted(set(reasons)),
        settled=False,
    )


def ingest_feed(
    source: str,
    policy: GeneralIntakePolicy | None = None,
    *,
    kind: PacketSourceKind | None = None,
) -> GeneralIntakeReport:
    """Ingest RSS, Atom, JSON feed, or NDJSON content from file or explicit live source."""

    active_policy = policy or GeneralIntakePolicy()
    active_kind = kind or _infer_general_kind(source, PacketSourceKind.AUTO)
    try:
        text, provenance = _read_source_text_with_provenance(
            source, active_policy.web_policy, active_kind
        )
    except ValueError as exc:
        return _with_intake_metadata(
            _diagnostic_general_report(active_kind, source, str(exc)),
            active_policy,
        )
    packets: list[CapabilityPacketCandidate] = []
    reasons: list[str] = []
    if active_kind in {PacketSourceKind.RSS, PacketSourceKind.ATOM}:
        entries = _feed_entries(text)
    elif active_kind == PacketSourceKind.JSON_FEED:
        entries = _json_entries(text)
    elif active_kind == PacketSourceKind.NDJSON:
        entries = _ndjson_entries(text)
    else:
        entries = []
        reasons.append(f"unsupported feed kind {active_kind.value}")
    for index, entry in enumerate(entries):
        if index >= active_policy.max_feed_entries:
            reasons.append("feed entry count exceeds max_feed_entries")
            packets = []
            break
        packet = packet_from_text(
            entry,
            packet_id=f"packet:{active_kind.value}:{sha256_text(source)[:8]}:{index}",
            source_kind=active_kind,
            source_ref=sanitize_intake_source_ref(source),
            tags=sorted({active_kind.value, "feed", "external-candidate"}),
        )
        packet = packet.model_copy(
            update={
                "evidence_refs": sorted(
                    {
                        *packet.evidence_refs,
                        *[
                            ref
                            for item in provenance
                            for ref in [f"provenance:{item.provenance_id}", *item.evidence_refs]
                        ],
                    }
                )
            }
        )
        packets.append(packet)
    accepted = bool(packets) and not reasons
    residual = Ledger()
    if not accepted:
        residual = residual.add_coordinate(
            f"general-intake:{active_kind.value}:empty-or-malformed",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return _with_intake_metadata(
        GeneralIntakeReport(
            report_id=f"general-intake:{active_kind.value}:{sha256_text(source)[:12]}",
            source=sanitize_intake_source_ref(source),
            source_kind=active_kind,
            accepted=accepted,
            packets=sorted(packets, key=lambda packet: packet.packet_id),
            rejected_sources=[] if accepted else [sanitize_intake_source_ref(source)],
            residual_ledger=residual,
            provenance=sorted(provenance, key=lambda item: item.provenance_id),
            reasons=sorted(
                set(reasons or ([] if accepted else ["feed returned no packet entries"]))
            ),
            settled=False,
        ),
        active_policy,
    )


def create_agent_message(
    content: str,
    *,
    sender_agent_id: str,
    receiver_agent_id: str | None = None,
    message_id: str | None = None,
    nonce: str | None = None,
) -> AgentMessageEnvelope:
    """Create an unsigned local agent message envelope."""

    digest = sha256_text(content)
    return AgentMessageEnvelope(
        message_id=message_id or f"agent-message:{digest[:12]}",
        sender_agent_id=sender_agent_id,
        receiver_agent_id=receiver_agent_id,
        content=content,
        content_sha256=digest,
        nonce=nonce,
        tags=["agent-message"],
    )


def verify_agent_message(
    message: AgentMessageEnvelope,
    policy: GeneralIntakePolicy | None = None,
    identity_context: AgentMessageVerificationContext | None = None,
) -> AgentPacketExchangeReport:
    """Verify one message envelope shape and convert it to packet candidates."""

    active_policy = policy or GeneralIntakePolicy()
    contract = check_agent_message_contract(message)
    residual = contract.residual_ledger
    reasons: list[str] = []
    identity_reasons: list[str] = []
    if not contract.accepted:
        reasons.extend(contract.reasons)
    digest_valid = sha256_text(message.content) == message.content_sha256
    replay_detected = bool(
        active_policy.reject_replay_nonce
        and message.nonce
        and message.nonce in set(active_policy.seen_message_nonces)
    )
    signature_present = bool(
        message.signature_ref and message.issuer_public_key_id and message.issuer_attestation_id
    )
    signature_required = (
        active_policy.require_signed_agent_messages
        or active_policy.profile.lower()
        in {
            "production",
            "adversarial",
        }
    )
    identity_context_required = (
        active_policy.require_message_identity_context
        or active_policy.profile.lower() in {"production", "adversarial"}
    )
    if not digest_valid:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:digest-mismatch",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("message content digest mismatch")
    if replay_detected:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:replay-nonce",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("message replay nonce was already seen")
    time_reasons, residual = _message_time_reasons(message, active_policy, residual)
    reasons.extend(time_reasons)
    if signature_required and not signature_present:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:missing-signature",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("signed agent message required by profile")
    identity_verified = False
    if identity_context_required:
        if identity_context is None:
            residual = residual.add_coordinate(
                f"agent-message:{message.message_id}:missing-identity-context",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            identity_reasons.append("accepted identity context required by profile")
        elif not identity_context.accepted:
            residual = residual.add_coordinate(
                f"agent-message:{message.message_id}:unaccepted-identity-context",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            identity_reasons.append("identity context is not accepted")
        else:
            membership_reasons = _identity_membership_reasons(message, identity_context)
            identity_reasons.extend(membership_reasons)
            for index, _reason in enumerate(membership_reasons):
                residual = residual.add_coordinate(
                    f"agent-message:{message.message_id}:identity-context:{index}",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
            identity_verified = not membership_reasons
    elif identity_context is not None and identity_context.accepted:
        membership_reasons = _identity_membership_reasons(message, identity_context)
        identity_reasons.extend(membership_reasons)
        identity_verified = not membership_reasons
    reasons.extend(identity_reasons)
    accepted = digest_valid and not replay_detected and not reasons
    nonce_consumed = bool(message.nonce and accepted)
    packets = []
    if digest_valid:
        packet = packet_from_text(
            message.content,
            packet_id=f"packet:agent-message:{message.message_id}",
            source_kind=PacketSourceKind.AGENT_MESSAGE,
            source_ref=message.message_id,
            tags=sorted(set([*message.tags, "agent-message", "external-candidate"])),
        ).model_copy(
            update={
                "evidence_refs": sorted(
                    set(
                        [
                            *message.evidence_refs,
                            *message.route_request_refs,
                            f"sha256:{message.content_sha256}",
                            f"agent-message:{message.message_id}",
                        ]
                    )
                ),
                "verifier_routes": sorted(set(message.declared_routes)),
                "receiver_family": sorted(set(message.declared_receiver_family)),
                "issuer_agent_id": message.sender_agent_id,
                "issuer_public_key_id": message.issuer_public_key_id,
                "issuer_attestation_id": message.issuer_attestation_id,
                "issuer_signature_ref": message.signature_ref,
            }
        )
        packets.append(packet)
    nonce_ledger = AgentMessageNonceLedger(
        consumed_nonces=sorted({message.nonce} if nonce_consumed and message.nonce else set()),
        replayed_nonces=sorted({message.nonce} if replay_detected and message.nonce else set()),
        rejected_message_ids=[] if accepted else [message.message_id],
        accepted=accepted,
        reasons=sorted(set(reasons)),
    )
    return AgentPacketExchangeReport(
        report_id=f"agent-message-check:{message.message_id}",
        accepted=accepted,
        message_id=message.message_id,
        sender_agent_id=message.sender_agent_id,
        packets=packets,
        replay_detected=replay_detected,
        signature_required=signature_required,
        signature_present=signature_present,
        consumed_nonces=nonce_ledger.consumed_nonces,
        nonce_ledger=nonce_ledger,
        identity_verified=identity_verified,
        identity_reasons=sorted(set(identity_reasons)),
        message_contract_valid=contract.accepted,
        nonce_status=("replayed" if replay_detected else _nonce_status(message, nonce_consumed)),
        identity_status=(
            "verified"
            if identity_verified
            else ("required" if identity_context_required else "not-required")
        ),
        candidate_packet_ids=sorted(packet.packet_id for packet in packets),
        quarantine_recommended=bool(reasons),
        next_safe_commands=[
            "uv run pic agent message contract --message <message.json>",
            "uv run pic ecology bridge-runtime --report <general-intake-report.json>",
        ],
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
        settled=False,
    )


def ingest_agent_inbox(
    source: str,
    policy: GeneralIntakePolicy | None = None,
    identity_context: AgentMessageVerificationContext | None = None,
) -> GeneralIntakeReport:
    """Ingest one local JSON or JSONL agent inbox."""

    active_policy = policy or GeneralIntakePolicy()
    try:
        inbox = _inbox_from_source(source, active_policy)
    except ValueError as exc:
        return _with_intake_metadata(
            _diagnostic_general_report(PacketSourceKind.AGENT_INBOX, source, str(exc)),
            active_policy,
        )
    reports = [
        verify_agent_message(
            message,
            active_policy.model_copy(
                update={
                    "seen_message_nonces": inbox.seen_nonces + active_policy.seen_message_nonces
                }
            ),
            identity_context,
        )
        for message in inbox.messages
    ]
    packets = [packet for report in reports for packet in report.packets]
    residual = Ledger()
    reasons: list[str] = []
    for report in reports:
        residual = residual.combine(report.residual_ledger)
        reasons.extend(report.reasons)
    return _with_intake_metadata(
        GeneralIntakeReport(
            report_id=f"general-intake:agent-inbox:{inbox.inbox_id}",
            source=sanitize_intake_source_ref(source),
            source_kind=PacketSourceKind.AGENT_INBOX,
            accepted=bool(packets) and not reasons,
            packets=sorted(packets, key=lambda packet: packet.packet_id),
            rejected_sources=[] if not reasons else [sanitize_intake_source_ref(source)],
            residual_ledger=residual,
            reasons=sorted(set(reasons)),
            settled=False,
        ),
        active_policy,
    )


def read_agent_inbox(path: str | Path) -> AgentInboxRecord:
    """Read an agent inbox from JSON or JSONL."""

    return _inbox_from_source(str(path), GeneralIntakePolicy())


def write_agent_inbox(path: str | Path, inbox: AgentInboxRecord) -> None:
    """Write a deterministic JSON inbox file."""

    Path(path).write_text(
        json.dumps(inbox.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_agent_message(path: str | Path, message: AgentMessageEnvelope) -> AgentInboxRecord:
    """Append one message to a deterministic JSON inbox file."""

    target = Path(path)
    inbox = (
        read_agent_inbox(target) if _path_exists(target) else AgentInboxRecord(inbox_id=target.stem)
    )
    updated = inbox.model_copy(update={"messages": [*inbox.messages, message]})
    write_agent_inbox(target, updated)
    return updated


def deliver_agent_message(
    path: str | Path,
    message: AgentMessageEnvelope,
    policy: GeneralIntakePolicy | None = None,
    identity_context: AgentMessageVerificationContext | None = None,
) -> AgentMessageDeliveryReport:
    """Verify and append one agent message to a local inbox/outbox file."""

    active_policy = policy or GeneralIntakePolicy()
    target = Path(path)
    report = verify_agent_message(message, active_policy, identity_context)
    inbox = (
        read_agent_inbox(target) if _path_exists(target) else AgentInboxRecord(inbox_id=target.stem)
    )
    delivered: list[str] = []
    rejected: list[str] = []
    reasons = list(report.reasons)
    if report.accepted:
        inbox = inbox.model_copy(update={"messages": [*inbox.messages, message]})
        write_agent_inbox(target, inbox)
        delivered.append(message.message_id)
    else:
        rejected.append(message.message_id)
        reasons.append("message was not appended because verification failed")
    return _delivery_report(
        action="send",
        inbox_ref=str(path),
        inbox=inbox,
        profile=active_policy.profile,
        reports=[report],
        delivered_message_ids=delivered,
        rejected_message_ids=rejected,
        identity_context=identity_context,
        reasons=reasons,
    )


def receive_agent_inbox(
    path: str | Path,
    policy: GeneralIntakePolicy | None = None,
    identity_context: AgentMessageVerificationContext | None = None,
) -> AgentMessageDeliveryReport:
    """Read and verify all messages in a local agent inbox."""

    active_policy = policy or GeneralIntakePolicy()
    try:
        inbox = read_agent_inbox(path)
    except ValueError as exc:
        return _delivery_report(
            action="receive",
            inbox_ref=str(path),
            inbox=AgentInboxRecord(inbox_id=Path(path).stem),
            profile=active_policy.profile,
            reports=[],
            delivered_message_ids=[],
            rejected_message_ids=[],
            identity_context=identity_context,
            reasons=[str(exc)],
        )
    seen_nonces = list(inbox.seen_nonces) + list(active_policy.seen_message_nonces)
    reports: list[AgentPacketExchangeReport] = []
    consumed: list[str] = []
    for message in inbox.messages:
        active_report = verify_agent_message(
            message,
            active_policy.model_copy(update={"seen_message_nonces": [*seen_nonces, *consumed]}),
            identity_context,
        )
        reports.append(active_report)
        consumed.extend(active_report.consumed_nonces)
    delivered = [report.message_id or "" for report in reports if report.accepted]
    rejected = [report.message_id or "" for report in reports if not report.accepted]
    reasons = [reason for report in reports for reason in report.reasons]
    if not inbox.messages:
        reasons.append("inbox contains no messages")
    return _delivery_report(
        action="receive",
        inbox_ref=str(path),
        inbox=inbox,
        profile=active_policy.profile,
        reports=reports,
        delivered_message_ids=[item for item in delivered if item],
        rejected_message_ids=[item for item in rejected if item],
        identity_context=identity_context,
        reasons=reasons,
    )


def agent_relay_readiness_report(
    path: str | Path | None = None,
    policy: GeneralIntakePolicy | None = None,
    identity_context: AgentMessageVerificationContext | None = None,
) -> AgentRelayReadinessReport:
    """Summarize local agent-message relay readiness without network calls."""

    active_policy = policy or GeneralIntakePolicy()
    inbox: AgentInboxRecord | None = None
    inbox_exists = False
    reasons: list[str] = []
    if path is not None:
        inbox_path = Path(path)
        inbox_exists = _path_exists(inbox_path)
        if inbox_exists:
            try:
                inbox = read_agent_inbox(inbox_path)
            except ValueError as exc:
                reasons.append(str(exc))
        else:
            reasons.append("inbox path does not exist yet; send will create a local JSON inbox")
    signature_required = (
        active_policy.require_signed_agent_messages
        or active_policy.profile.lower() in {"production", "adversarial"}
    )
    identity_required = (
        active_policy.require_message_identity_context
        or active_policy.profile.lower() in {"production", "adversarial"}
    )
    identity_accepted = bool(identity_context and identity_context.accepted)
    if identity_required and not identity_accepted:
        reasons.append("accepted identity context required before production relay promotion")
    loopback_ready = not reasons or all("does not exist yet" in reason for reason in reasons)
    return AgentRelayReadinessReport(
        report_id=f"agent-relay-readiness:{active_policy.profile}",
        profile=active_policy.profile,
        allow_live_connectors=active_policy.allow_live_connectors,
        inbox_ref=None if path is None else sanitize_intake_source_ref(str(path)),
        inbox_exists=inbox_exists,
        message_count=0 if inbox is None else len(inbox.messages),
        seen_nonce_count=0 if inbox is None else len(inbox.seen_nonces),
        signature_required=signature_required,
        identity_context_required=identity_required,
        identity_context_accepted=identity_accepted,
        loopback_ready=loopback_ready,
        operationally_usable=loopback_ready and (not identity_required or identity_accepted),
        readiness={
            "local_inbox": "ready" if inbox_exists else "create-on-send",
            "contract_check": "ready",
            "nonce_replay_check": "ready",
            "signature_policy": "required" if signature_required else "diagnostic",
            "identity_context": (
                "ready"
                if identity_accepted
                else "required"
                if identity_required
                else "not-required"
            ),
            "live_default_mode": "bounded-explicit-source",
        },
        recommended_next_commands=[
            "pic agent message send --inbox inbox.json --sender agent:alice --text <text>",
            "pic agent message receive --inbox inbox.json",
            "pic agent inbox verify --inbox inbox.json",
            "pic ecology bridge-runtime --report <general-intake-report.json>",
        ],
        safety_invariants=[
            "agent-message relay is local-file based unless an explicit live source is supplied",
            "agent messages remain packet candidates until verifier and identity policies pass",
            "nonce, signature, identity, and residual checks fail closed",
            "relay readiness does not prove external-world truth or real ASI",
        ],
        reasons=sorted(set(reasons)),
    )


def _delivery_report(
    *,
    action: str,
    inbox_ref: str,
    inbox: AgentInboxRecord,
    profile: str,
    reports: list[AgentPacketExchangeReport],
    delivered_message_ids: list[str],
    rejected_message_ids: list[str],
    identity_context: AgentMessageVerificationContext | None,
    reasons: list[str],
) -> AgentMessageDeliveryReport:
    aggregate_nonce_ledger = AgentMessageNonceLedger(
        consumed_nonces=sorted(
            {nonce for report in reports for nonce in report.nonce_ledger.consumed_nonces}
        ),
        replayed_nonces=sorted(
            {nonce for report in reports for nonce in report.nonce_ledger.replayed_nonces}
        ),
        rejected_message_ids=sorted(
            {
                message_id
                for report in reports
                for message_id in report.nonce_ledger.rejected_message_ids
            }
        ),
        accepted=bool(reports) and all(report.nonce_ledger.accepted for report in reports),
        reasons=sorted({reason for report in reports for reason in report.nonce_ledger.reasons}),
    )
    message_ids = sorted({report.message_id or "" for report in reports if report.message_id})
    candidate_packet_ids = sorted(
        {packet_id for report in reports for packet_id in report.candidate_packet_ids}
    )
    accepted = bool(reports) and all(report.accepted for report in reports) and not reasons
    if delivered_message_ids:
        accepted = accepted and not rejected_message_ids
    return AgentMessageDeliveryReport(
        report_id=f"agent-message-delivery:{action}:{sha256_text(inbox_ref)[:12]}",
        action=action,
        inbox_ref=sanitize_intake_source_ref(inbox_ref),
        inbox_id=inbox.inbox_id,
        profile=profile,
        message_ids=message_ids,
        delivered_message_ids=sorted(set(delivered_message_ids)),
        rejected_message_ids=sorted(set(rejected_message_ids)),
        exchange_reports=sorted(reports, key=lambda report: report.report_id),
        nonce_ledger=aggregate_nonce_ledger,
        candidate_packet_ids=candidate_packet_ids,
        identity_context_accepted=bool(identity_context and identity_context.accepted),
        accepted=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
        next_safe_commands=[
            "pic agent message contract --message <message.json>",
            "pic agent inbox verify --inbox <inbox.json>",
            "pic ecology bridge-runtime --report <general-intake-report.json>",
        ],
    )


def _policy_for_descriptor(
    policy: GeneralIntakePolicy, descriptor: GeneralIntakeSource
) -> GeneralIntakePolicy:
    live_allowed = bool(policy.allow_live_connectors and descriptor.allow_live_connectors)
    return policy.model_copy(
        update={
            "allow_live_connectors": live_allowed,
            "web_policy": policy.web_policy.model_copy(
                update={"allow_live_connectors": live_allowed}
            ),
        }
    )


def _ingest_text_or_web(
    source: str,
    kind: PacketSourceKind,
    policy: GeneralIntakePolicy,
) -> PacketIngestionReport:
    report, _text = _ingest_text_or_web_with_text(source, kind, policy)
    return report


def _ingest_text_or_web_with_text(
    source: str,
    kind: PacketSourceKind,
    policy: GeneralIntakePolicy,
) -> tuple[PacketIngestionReport, str | None]:
    path = _safe_path(source)
    if path is not None and _path_is_file(path):
        try:
            text = _read_bounded_local_text(path, policy.web_policy.max_bytes_per_resource)
        except UnicodeDecodeError:
            return (
                _diagnostic_packet_report(kind, source, "local source is not valid UTF-8 text"),
                None,
            )
        except OSError as exc:
            return _diagnostic_packet_report(
                kind, source, f"could not read local source: {exc}"
            ), None
        except ValueError as exc:
            return _diagnostic_packet_report(kind, source, str(exc)), None
        provenance = [_provenance_for_text(source, text, kind, accepted=True)]
        return (
            _packet_report_from_text(source, text, kind, tags=[kind.value], provenance=provenance),
            text,
        )
    if kind == PacketSourceKind.HTTP or source.startswith(("http://", "https://")):
        fetched_text, report = _fetch_http_text(
            source,
            policy.web_policy.model_copy(
                update={"allow_live_connectors": policy.allow_live_connectors}
            ),
        )
        if fetched_text is None:
            return report, None
        return (
            _packet_report_from_text(
                source,
                fetched_text,
                PacketSourceKind.WEB_PAGE,
                tags=["web", "http"],
                provenance=report.provenance,
                web_fetch_reports=report.web_fetch_reports,
            ),
            fetched_text,
        )
    return (
        _diagnostic_packet_report(
            kind, source, "source is neither a local text file nor an allowed live URL"
        ),
        None,
    )


def _fetch_http_text(
    source: str, policy: WebFetchPolicy
) -> tuple[str | None, PacketIngestionReport]:
    if not policy.allow_live_connectors:
        return None, _http_diagnostic_report(
            source,
            "HTTP intake requires allow_live_connectors=true in both source/request "
            "and policy/runtime",
        )
    validation_failure = _validate_url(source, policy)
    if validation_failure is not None:
        return None, _http_diagnostic_report(source, validation_failure)
    robots_decision = _robots_decision(source, policy)
    if policy.require_robots_decision and robots_decision.mode in {
        "not-checked",
        "conservative-assumed",
    }:
        return None, _http_diagnostic_report(
            source,
            "robots decision is required by WebFetchPolicy",
            robots_decision=robots_decision,
        )
    if not robots_decision.allowed:
        return None, _http_diagnostic_report(
            source,
            robots_decision.reason,
            robots_decision=robots_decision,
        )
    try:
        httpx = importlib.import_module("httpx")
    except ModuleNotFoundError:
        return None, _http_diagnostic_report(
            source,
            "optional connector dependency 'httpx' is not installed",
            robots_decision=robots_decision,
        )
    try:
        if hasattr(httpx, "Client"):
            with httpx.Client(
                follow_redirects=True,
                max_redirects=policy.max_redirects,
                timeout=policy.timeout_seconds,
                headers={"User-Agent": policy.user_agent},
            ) as client:
                response = client.get(source)
        else:
            response = httpx.get(
                source,
                follow_redirects=True,
                timeout=policy.timeout_seconds,
                headers={"User-Agent": policy.user_agent},
            )
    except httpx.HTTPError as exc:
        return None, _http_diagnostic_report(
            source,
            f"connector request failed: {exc}",
            robots_decision=robots_decision,
        )
    redirect_chain = _redirect_chain(response, source)
    redirect_reasons = _redirect_validation_reasons(redirect_chain, policy)
    if redirect_reasons:
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        fetch_report = WebFetchReport(
            report_id=f"web-fetch:{sha256_text(source)[:12]}",
            requested_url=sanitize_intake_source_ref(source),
            final_url=sanitize_intake_source_ref(redirect_chain[-1] if redirect_chain else source),
            redirect_chain=[sanitize_intake_source_ref(item) for item in redirect_chain],
            status_code=response.status_code,
            content_type=content_type or None,
            byte_count=0,
            robots_decision=robots_decision,
            accepted=False,
            reasons=sorted(set(redirect_reasons)),
        )
        report = _diagnostic_packet_report(
            PacketSourceKind.HTTP, source, "; ".join(redirect_reasons)
        )
        diagnostic_coordinates = sorted(report.residual_ledger.coordinates)
        report.provenance = [
            _provenance_for_fetch(
                source,
                "",
                PacketSourceKind.WEB_PAGE,
                final_url=redirect_chain[-1] if redirect_chain else source,
                redirect_chain=redirect_chain,
                status_code=response.status_code,
                content_type=content_type or None,
                robots_decision=robots_decision,
                accepted=False,
                reasons=redirect_reasons,
                residual_coordinates=diagnostic_coordinates,
            )
        ]
        report.web_fetch_reports = [fetch_report]
        return None, report
    final_url = redirect_chain[-1] if redirect_chain else str(getattr(response, "url", source))
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    raw = response.content[: policy.max_bytes_per_resource + 1]
    text = raw.decode(response.encoding or "utf-8", errors="replace")
    reasons: list[str] = []
    if response.status_code >= 400:
        status_reason = f"http status {response.status_code}"
        if policy.diagnose_rate_limits and response.status_code == 429:
            status_reason = "rate limited by remote source"
        reasons.append(status_reason)
    if content_type and content_type not in set(policy.allowed_content_types):
        reasons.append(f"unsupported content type {content_type!r}")
    if len(raw) > policy.max_bytes_per_resource:
        reasons.append("response exceeds max_bytes_per_resource")
    accepted = not reasons
    fetch_report = WebFetchReport(
        report_id=f"web-fetch:{sha256_text(source)[:12]}",
        requested_url=sanitize_intake_source_ref(source),
        final_url=sanitize_intake_source_ref(final_url),
        redirect_chain=[sanitize_intake_source_ref(item) for item in redirect_chain],
        status_code=response.status_code,
        content_type=content_type or None,
        content_sha256=sha256_text(text) if accepted else None,
        byte_count=min(len(raw), policy.max_bytes_per_resource),
        robots_decision=robots_decision,
        accepted=accepted,
        reasons=sorted(set(reasons)),
    )
    if not accepted:
        report = _diagnostic_packet_report(PacketSourceKind.HTTP, source, "; ".join(reasons))
        provenance = _provenance_for_fetch(
            source,
            "",
            PacketSourceKind.WEB_PAGE,
            final_url=final_url,
            redirect_chain=redirect_chain,
            status_code=response.status_code,
            content_type=content_type or None,
            byte_count=min(len(raw), policy.max_bytes_per_resource),
            robots_decision=robots_decision,
            accepted=False,
            reasons=reasons,
            residual_coordinates=sorted(report.residual_ledger.coordinates),
        )
        report.provenance = [provenance]
        report.web_fetch_reports = [fetch_report]
        return None, report
    provenance = _provenance_for_fetch(
        source,
        text,
        PacketSourceKind.WEB_PAGE,
        final_url=final_url,
        redirect_chain=redirect_chain,
        status_code=response.status_code,
        content_type=content_type or None,
        byte_count=min(len(raw), policy.max_bytes_per_resource),
        robots_decision=robots_decision,
        accepted=True,
        reasons=reasons,
    )
    report = PacketIngestionReport(
        report_id=f"packet-ingestion:http-fetch:{sha256_text(source)[:12]}",
        accepted=True,
        source_kind=PacketSourceKind.HTTP,
        provenance=[provenance],
        web_fetch_reports=[fetch_report],
    )
    # Preserve the structured fetch report as a reason-free provenance evidence ref.
    report.provenance[0].evidence_refs.append(f"web-fetch:{fetch_report.report_id}")
    return text, report


def _packet_report_from_text(
    source: str,
    text: str,
    kind: PacketSourceKind,
    *,
    tags: list[str],
    provenance: list[IntakeProvenanceRecord] | None = None,
    web_fetch_reports: list[WebFetchReport] | None = None,
) -> PacketIngestionReport:
    provenance_items = provenance or [_provenance_for_text(source, text, kind, accepted=True)]
    provenance_refs = [
        ref
        for item in provenance_items
        for ref in [f"provenance:{item.provenance_id}", *item.evidence_refs]
    ]
    packet = packet_from_text(
        _text_summary(source, text),
        packet_id=f"packet:{kind.value}:{sha256_text(source + text)[:12]}",
        source_kind=kind,
        source_ref=sanitize_intake_source_ref(source),
        tags=sorted(set([*tags, "external-candidate"])),
    ).model_copy(
        update={
            "evidence_refs": sorted(set(provenance_refs)),
            "residual_charge": 1.0 if kind != PacketSourceKind.LOCAL else 0.0,
        }
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:{kind.value}:{sha256_text(source)[:12]}",
        accepted=True,
        source_kind=kind,
        packets=[packet],
        provenance=sorted(provenance_items, key=lambda item: item.provenance_id),
        web_fetch_reports=sorted(web_fetch_reports or [], key=lambda item: item.report_id),
    )


def _general_from_reports(
    source: str,
    kind: PacketSourceKind,
    reports: list[PacketIngestionReport],
    policy: GeneralIntakePolicy | None = None,
) -> GeneralIntakeReport:
    residual = Ledger()
    reasons: list[str] = []
    packets = []
    rejected: list[str] = []
    provenance: list[IntakeProvenanceRecord] = []
    web_fetch_reports: list[WebFetchReport] = []
    for report in reports:
        residual = residual.combine(report.residual_ledger)
        reasons.extend(report.reasons)
        packets.extend(report.packets)
        rejected.extend(report.rejected_sources)
        provenance.extend(report.provenance)
        web_fetch_reports.extend(report.web_fetch_reports)
    return _with_intake_metadata(
        GeneralIntakeReport(
            report_id=f"general-intake:{kind.value}:{sha256_text(source)[:12]}",
            source=sanitize_intake_source_ref(source),
            source_kind=kind,
            accepted=bool(packets) and not reasons,
            packets=sorted(packets, key=lambda packet: packet.packet_id),
            ingestion_reports=reports,
            rejected_sources=sorted(set(rejected)),
            residual_ledger=residual,
            provenance=sorted(provenance, key=lambda item: item.provenance_id),
            web_fetch_reports=sorted(web_fetch_reports, key=lambda item: item.report_id),
            reasons=sorted(set(reasons)),
            settled=False,
        ),
        policy or GeneralIntakePolicy(),
    )


def _general_from_exchange(
    source: str,
    exchange: AgentPacketExchangeReport,
    policy: GeneralIntakePolicy | None = None,
) -> GeneralIntakeReport:
    provenance = [
        IntakeProvenanceRecord(
            provenance_id=f"agent-message:{exchange.message_id or sha256_text(source)[:12]}",
            source_kind=PacketSourceKind.AGENT_MESSAGE,
            source_ref=sanitize_intake_source_ref(source),
            public_source_ref=sanitize_intake_source_ref(source),
            accepted=exchange.accepted,
            reasons=exchange.reasons,
            residual_coordinates=[
                f"agent-message:{exchange.message_id}:diagnostic"
                if exchange.message_id
                else "agent-message:diagnostic"
            ],
        )
    ]
    return _with_intake_metadata(
        GeneralIntakeReport(
            report_id=f"general-intake:agent-message:{sha256_text(source)[:12]}",
            source=sanitize_intake_source_ref(source),
            source_kind=PacketSourceKind.AGENT_MESSAGE,
            accepted=exchange.accepted,
            packets=exchange.packets,
            rejected_sources=[] if exchange.accepted else [sanitize_intake_source_ref(source)],
            residual_ledger=exchange.residual_ledger,
            provenance=provenance,
            reasons=exchange.reasons,
            settled=False,
        ),
        policy or GeneralIntakePolicy(),
    )


def _with_intake_metadata(
    report: GeneralIntakeReport,
    policy: GeneralIntakePolicy,
) -> GeneralIntakeReport:
    """Attach candidate-only public metadata to a general intake report."""

    total_candidate_packets = len(report.packets)
    candidate_coordinates = sorted(
        {
            coordinate
            for item in report.provenance
            for coordinate in item.residual_coordinates
            if "external-candidate" in coordinate or coordinate.startswith("agent-message:")
        }
    )
    total_bytes = sum(item.byte_count for item in report.provenance) + sum(
        fetch.byte_count for fetch in report.web_fetch_reports
    )
    reasons = list(report.reasons)
    residual = report.residual_ledger
    if total_candidate_packets > policy.web_policy.max_total_packets_per_run:
        reason = "candidate packet count exceeds max_total_packets_per_run"
        reasons.append(reason)
        residual = residual.add_coordinate(
            f"general-intake:{report.source_kind.value}:{sha256_text(report.report_id)[:8]}:packet-budget",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    if total_bytes > policy.web_policy.max_total_bytes_per_run:
        reason = "intake byte count exceeds max_total_bytes_per_run"
        reasons.append(reason)
        residual = residual.add_coordinate(
            f"general-intake:{report.source_kind.value}:{sha256_text(report.report_id)[:8]}:byte-budget",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = report.accepted and not reasons
    decisions = [
        _policy_decision_for_report(
            report,
            policy,
            candidate_coordinates,
            total_bytes=total_bytes,
            total_candidate_packets=total_candidate_packets,
            reasons=reasons,
        ),
    ]
    queue_class = _report_queue_class(report, reasons)
    return report.model_copy(
        update={
            "accepted": accepted,
            "candidate_only": True,
            "intake_profile": policy.profile,
            "policy_digest": _policy_digest(policy),
            "source_policy_decisions": decisions,
            "total_bytes_read": total_bytes,
            "total_candidate_packets": total_candidate_packets,
            "sqot_queue_class": queue_class,
            "ecpt_phase_contribution_allowed": False,
            "candidate_residual_coordinates": candidate_coordinates,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
            "settled": False,
        }
    )


def _policy_decision_for_report(
    report: GeneralIntakeReport,
    policy: GeneralIntakePolicy,
    candidate_coordinates: list[str],
    *,
    total_bytes: int,
    total_candidate_packets: int,
    reasons: list[str],
) -> GeneralIntakePolicyDecision:
    _ = total_bytes, total_candidate_packets
    return GeneralIntakePolicyDecision(
        decision_id=(
            f"intake-policy-decision:{sha256_text(report.report_id + _policy_digest(policy))[:12]}"
        ),
        profile=policy.profile,
        source_ref=report.source,
        source_kind=report.source_kind,
        accepted=report.accepted and not reasons,
        allow_live_connectors=policy.allow_live_connectors,
        candidate_only=True,
        ecpt_phase_contribution_allowed=False,
        reasons=sorted(set(reasons)),
        residual_coordinates=sorted(
            set(candidate_coordinates) | set(report.residual_ledger.coordinates)
        ),
    )


def _policy_digest(policy: GeneralIntakePolicy) -> str:
    payload = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return sha256_text(payload)


def _report_queue_class(
    report: GeneralIntakeReport, reasons: list[str] | None = None
) -> ExternalCandidateClassification:
    if reasons or report.rejected_sources:
        return ExternalCandidateClassification.QUARANTINE_WORK
    if any(packet.verifier_routes for packet in report.packets):
        return ExternalCandidateClassification.VERIFIER_WORK
    if report.packets:
        return ExternalCandidateClassification.DIAGNOSTIC_WORK
    return ExternalCandidateClassification.CANDIDATE_ONLY


def _diagnostic_packet_report(
    kind: PacketSourceKind,
    source: str,
    reason: str,
) -> PacketIngestionReport:
    coordinate = (
        f"general-intake:{kind.value}:{sha256_text(source)[:8]}:"
        f"diagnostic:{sha256_text(reason)[:8]}"
    )
    provenance = IntakeProvenanceRecord(
        provenance_id=f"provenance:{kind.value}:diagnostic:{sha256_text(source + reason)[:12]}",
        source_kind=kind,
        source_ref=sanitize_intake_source_ref(source),
        public_source_ref=sanitize_intake_source_ref(source),
        residual_coordinates=[coordinate],
        accepted=False,
        reasons=[reason],
    )
    return PacketIngestionReport(
        report_id=(
            f"packet-ingestion:{kind.value}:diagnostic:"
            f"{sha256_text(source)[:8]}:{sha256_text(reason)[:8]}"
        ),
        accepted=False,
        source_kind=kind,
        rejected_sources=[sanitize_intake_source_ref(source)],
        reasons=[reason],
        residual_ledger=Ledger().add_coordinate(
            coordinate,
            1.0,
            kind=CoordinateKind.RESIDUAL,
        ),
        provenance=[provenance],
    )


def _diagnostic_general_report(
    kind: PacketSourceKind,
    source: str,
    reason: str,
) -> GeneralIntakeReport:
    report = _diagnostic_packet_report(kind, source, reason)
    return _general_from_reports(source, kind, [report])


def _http_diagnostic_report(
    source: str,
    reason: str,
    *,
    robots_decision: RobotsDecision | None = None,
    final_url: str | None = None,
    redirect_chain: list[str] | None = None,
    status_code: int | None = None,
    content_type: str | None = None,
    byte_count: int = 0,
) -> PacketIngestionReport:
    report = _diagnostic_packet_report(PacketSourceKind.HTTP, source, reason)
    diagnostic_coordinates = sorted(report.residual_ledger.coordinates)
    active_robots = robots_decision or RobotsDecision(
        decision_id=f"robots:not-checked:{sha256_text(source)[:12]}",
        source_ref=sanitize_intake_source_ref(source),
    )
    report.provenance = [
        _provenance_for_fetch(
            source,
            "",
            PacketSourceKind.HTTP,
            final_url=final_url or source,
            redirect_chain=redirect_chain or [],
            status_code=status_code,
            content_type=content_type,
            byte_count=byte_count,
            robots_decision=active_robots,
            accepted=False,
            reasons=[reason],
            residual_coordinates=diagnostic_coordinates,
        )
    ]
    report.web_fetch_reports = [
        WebFetchReport(
            report_id=f"web-fetch:{sha256_text(source)[:12]}",
            requested_url=sanitize_intake_source_ref(source),
            final_url=sanitize_intake_source_ref(final_url or source),
            redirect_chain=[sanitize_intake_source_ref(item) for item in redirect_chain or []],
            status_code=status_code,
            content_type=content_type,
            byte_count=byte_count,
            robots_decision=active_robots,
            accepted=False,
            reasons=[reason],
        )
    ]
    return report


def _provenance_for_text(
    source: str,
    text: str,
    kind: PacketSourceKind,
    *,
    accepted: bool,
    reasons: list[str] | None = None,
) -> IntakeProvenanceRecord:
    digest = sha256_text(text)
    coordinate = f"general-intake:{kind.value}:{sha256_text(source)[:8]}:external-candidate"
    return IntakeProvenanceRecord(
        provenance_id=f"provenance:{kind.value}:{digest[:12]}",
        source_kind=kind,
        source_ref=sanitize_intake_source_ref(source),
        public_source_ref=sanitize_intake_source_ref(source),
        content_sha256=digest,
        byte_count=len(text.encode("utf-8")),
        evidence_refs=[f"sha256:{digest}", coordinate],
        residual_coordinates=[coordinate],
        accepted=accepted,
        reasons=sorted(set(reasons or [])),
    )


def _provenance_for_fetch(
    source: str,
    text: str,
    kind: PacketSourceKind,
    *,
    final_url: str | None = None,
    redirect_chain: list[str] | None = None,
    status_code: int | None = None,
    content_type: str | None = None,
    byte_count: int = 0,
    robots_decision: RobotsDecision | None = None,
    accepted: bool,
    reasons: list[str] | None = None,
    residual_coordinates: list[str] | None = None,
) -> IntakeProvenanceRecord:
    digest = sha256_text(text) if text else None
    coordinates = residual_coordinates or [
        f"general-intake:{kind.value}:{sha256_text(source)[:8]}:external-candidate"
    ]
    evidence_refs = [*coordinates]
    if digest is not None:
        evidence_refs.append(f"sha256:{digest}")
    return IntakeProvenanceRecord(
        provenance_id=f"provenance:{kind.value}:{sha256_text(source + (digest or ''))[:12]}",
        source_kind=kind,
        source_ref=sanitize_intake_source_ref(source),
        public_source_ref=sanitize_intake_source_ref(final_url or source),
        content_sha256=digest,
        media_type=content_type,
        byte_count=byte_count,
        final_url=sanitize_intake_source_ref(final_url) if final_url else None,
        redirect_chain=[sanitize_intake_source_ref(item) for item in redirect_chain or []],
        status_code=status_code,
        robots_decision=robots_decision,
        evidence_refs=sorted(set(evidence_refs)),
        residual_coordinates=sorted(set(coordinates)),
        accepted=accepted,
        reasons=sorted(set(reasons or [])),
    )


def _robots_decision(source: str, policy: WebFetchPolicy) -> RobotsDecision:
    if not policy.respect_robots:
        return RobotsDecision(
            decision_id=f"robots:ignored:{sha256_text(source)[:12]}",
            source_ref=sanitize_intake_source_ref(source),
            allowed=True,
            mode="not-enforced",
            reason="robots policy explicitly disabled by WebFetchPolicy",
        )
    if policy.robots_uncertainty_is_diagnostic:
        coordinate = f"general-intake:web:{sha256_text(source)[:8]}:robots-uncertain"
        return RobotsDecision(
            decision_id=f"robots:uncertain:{sha256_text(source)[:12]}",
            source_ref=sanitize_intake_source_ref(source),
            allowed=False,
            mode="uncertain",
            reason="robots policy uncertainty is diagnostic under current WebFetchPolicy",
            residual_coordinate=coordinate,
        )
    return RobotsDecision(
        decision_id=f"robots:assumed:{sha256_text(source)[:12]}",
        source_ref=sanitize_intake_source_ref(source),
        allowed=True,
        mode="conservative-assumed",
        reason=(
            "robots policy recorded; no active crawler automation or script execution is performed"
        ),
    )


def _redirect_chain(response: Any, fallback: str) -> list[str]:
    history = list(getattr(response, "history", []) or [])
    chain = [str(getattr(item, "url", fallback)) for item in history]
    chain.append(str(getattr(response, "url", fallback)))
    return chain


def _redirect_validation_reasons(chain: list[str], policy: WebFetchPolicy) -> list[str]:
    reasons: list[str] = []
    for url in chain:
        failure = _validate_url(url, policy)
        if failure is not None:
            reasons.append(
                f"redirect chain URL rejected ({sanitize_intake_source_ref(url)}): {failure}"
            )
    return sorted(set(reasons))


def _infer_general_kind(source: str, kind: PacketSourceKind) -> PacketSourceKind:
    if kind != PacketSourceKind.AUTO:
        return kind
    path = _safe_path(source)
    suffix = path.suffix.lower() if path is not None else ""
    if path is not None and _path_exists(path):
        if suffix in {".jsonl", ".ndjson"}:
            return PacketSourceKind.NDJSON
        if suffix == ".json":
            try:
                data = json.loads(
                    _read_bounded_local_text(path, WebFetchPolicy().max_bytes_per_resource)
                )
            except (OSError, ValueError, json.JSONDecodeError):
                return PacketSourceKind.JSON_FEED
            if isinstance(data, dict) and ("messages" in data or "inbox_id" in data):
                return PacketSourceKind.AGENT_INBOX
            if isinstance(data, dict) and {"message_id", "sender_agent_id", "content"} <= set(data):
                return PacketSourceKind.AGENT_MESSAGE
            return PacketSourceKind.JSON_FEED
        if suffix in {".rss", ".xml"}:
            return PacketSourceKind.RSS
        if suffix in {".html", ".htm"}:
            return PacketSourceKind.WEB_PAGE
        return PacketSourceKind.LOCAL
    host = urlparse(source).netloc.lower()
    lowered = source.lower()
    if "github.com" in host or (source.count("/") == 1 and not source.startswith("http")):
        return PacketSourceKind.GITHUB
    if "zenodo.org" in host or "zenodo" in lowered:
        return PacketSourceKind.ZENODO
    if "arxiv.org" in host or lowered.startswith("arxiv:"):
        return PacketSourceKind.ARXIV
    if lowered.startswith(("http://", "https://")):
        return PacketSourceKind.WEB_PAGE
    return PacketSourceKind.LOCAL


def _read_source_text(source: str, policy: WebFetchPolicy) -> str:
    text, _ = _read_source_text_with_provenance(source, policy, PacketSourceKind.WEB_PAGE)
    return text


def _safe_path(source: str) -> Path | None:
    try:
        return Path(source)
    except (OSError, ValueError):
        return None


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except (OSError, ValueError):
        return False


def _path_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except (OSError, ValueError):
        return False


def _read_bounded_local_text(path: Path, max_bytes: int) -> str:
    try:
        if path.stat().st_size > max_bytes:
            raise ValueError("local source exceeds max_bytes_per_resource")
    except OSError:
        raise
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ValueError("local source exceeds max_bytes_per_resource")
    return raw.decode("utf-8")


def _read_inline_or_local_text(source: str, policy: GeneralIntakePolicy, *, label: str) -> str:
    max_bytes = policy.web_policy.max_bytes_per_resource
    path = _safe_path(source)
    if path is not None and _path_exists(path):
        try:
            return _read_bounded_local_text(path, max_bytes)
        except UnicodeDecodeError as exc:
            raise ValueError(f"{label} source is not valid UTF-8 text") from exc
    if len(source.encode("utf-8")) > max_bytes:
        raise ValueError(f"inline {label} exceeds max_bytes_per_resource")
    return source


def _check_inbox_message_count(messages: Any, policy: GeneralIntakePolicy) -> None:
    if isinstance(messages, list) and len(messages) > policy.max_agent_messages_per_inbox:
        raise ValueError("agent inbox message count exceeds max_agent_messages_per_inbox")


def _read_source_text_with_provenance(
    source: str, policy: WebFetchPolicy, kind: PacketSourceKind
) -> tuple[str, list[IntakeProvenanceRecord]]:
    path = _safe_path(source)
    if path is not None and _path_is_file(path):
        try:
            text = _read_bounded_local_text(path, policy.max_bytes_per_resource)
        except OSError as exc:
            raise ValueError(f"could not read local source: {exc}") from exc
        return text, [_provenance_for_text(source, text, kind, accepted=True)]
    fetched_text, report = _fetch_http_text(source, policy)
    if fetched_text is None or not report.accepted:
        reason = "; ".join(report.reasons) or "source unavailable"
        raise ValueError(reason)
    return fetched_text, report.provenance


def _validate_url(source: str, policy: WebFetchPolicy) -> str | None:
    parsed = urlparse(source)
    if parsed.scheme not in set(policy.allowed_schemes):
        return f"unsupported URL scheme {parsed.scheme!r}"
    if policy.require_https_for_live and parsed.scheme != "https":
        return "live intake requires HTTPS under current WebFetchPolicy"
    if policy.prefer_https and parsed.scheme != "https" and not policy.allow_http:
        return "HTTP URLs require allow_http=true"
    if not parsed.hostname:
        return "URL host is required"
    host = parsed.hostname.lower()
    if policy.allowed_hosts and not _host_matches(host, policy.allowed_hosts):
        return "URL host is outside allowed_hosts"
    if _host_matches(host, policy.blocked_hosts):
        return "URL host is blocked by blocked_hosts"
    if policy.allowed_path_prefixes and not any(
        parsed.path.startswith(prefix) for prefix in policy.allowed_path_prefixes
    ):
        return "URL path is outside allowed_path_prefixes"
    if policy.reject_private_networks and _is_private_host(host):
        return "private, loopback, or link-local host rejected"
    return None


def _host_matches(host: str, patterns: list[str]) -> bool:
    lowered = host.lower().strip("[]")
    for pattern in patterns:
        active = pattern.lower().strip()
        if not active:
            continue
        if active.startswith("*.") and lowered.endswith(active[1:]):
            return True
        if active == lowered:
            return True
    return False


def _is_private_host(host: str) -> bool:
    lowered = host.lower().strip("[]")
    if lowered in {"localhost", "127.0.0.1", "::1"} or lowered.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
    )


def _text_summary(source: str, text: str) -> str:
    if "<html" in text[:500].lower():
        title = _first_match(text, r"<title[^>]*>(.*?)</title>") or _safe_source_ref(source)
        description = _first_match(
            text, r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)'
        )
        return "\n".join(part for part in [title, description, _safe_source_ref(source)] if part)
    return text


def _extract_links(text: str, base_url: str) -> list[str]:
    links = []
    base_path = _safe_path(base_url)
    for match in re.finditer(r'href=["\']([^"\']+)["\']', text, flags=re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith(("#", "mailto:", "javascript:")):
            continue
        if (
            base_path is not None
            and _path_exists(base_path)
            and not href.startswith(("http://", "https://"))
        ):
            local_link = _safe_local_discovery_link(base_path, href)
            if local_link is not None:
                links.append(local_link)
            continue
        links.append(urljoin(base_url, href))
    return sorted(set(links))


def _safe_local_discovery_link(base_path: Path, href: str) -> str | None:
    try:
        root = base_path.parent.resolve()
        resolved = (base_path.parent / href).resolve()
    except (OSError, ValueError):
        return None
    if resolved == root or root in resolved.parents:
        return str(resolved)
    return None


def _feed_entries(text: str) -> list[str]:
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, DefusedXmlException):
        return []
    entries: list[str] = []
    for item in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = _element_text(item, "title")
        summary = _element_text(item, "description") or _element_text(item, "summary")
        link = _element_text(item, "link")
        entries.append("\n".join(part for part in [title, summary, link] if part))
    return [entry for entry in entries if entry.strip()]


def _json_entries(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    raw_items: Any = (
        data.get("items", data.get("entries", data if isinstance(data, list) else []))
        if isinstance(data, dict)
        else data
    )
    if not isinstance(raw_items, list):
        return []
    entries: list[str] = []
    for item in raw_items:
        if isinstance(item, dict):
            entries.append(
                "\n".join(
                    str(item.get(key, ""))
                    for key in ["title", "summary", "content_text", "url"]
                    if item.get(key)
                )
            )
        else:
            entries.append(str(item))
    return [entry for entry in entries if entry.strip()]


def _ndjson_entries(text: str) -> list[str]:
    entries: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        entries.append(json.dumps(data, sort_keys=True, separators=(",", ":")))
    return entries


def _message_time_reasons(
    message: AgentMessageEnvelope, policy: GeneralIntakePolicy, residual: Ledger
) -> tuple[list[str], Ledger]:
    reasons: list[str] = []
    now = datetime.now(UTC)
    skew = policy.max_message_clock_skew_seconds
    issued_at = _parse_message_time(message.issued_at)
    expires_at = _parse_message_time(message.expires_at)
    if message.issued_at and issued_at is None:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:invalid-issued-at",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("message issued_at is not valid ISO-8601")
    if message.expires_at and expires_at is None:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:invalid-expires-at",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("message expires_at is not valid ISO-8601")
    if issued_at is not None and issued_at.timestamp() - now.timestamp() > skew:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:future-issued-at",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("message issued_at is beyond allowed future clock skew")
    if expires_at is not None and now > expires_at:
        residual = residual.add_coordinate(
            f"agent-message:{message.message_id}:expired",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("message is expired")
    return reasons, residual


def _nonce_status(message: AgentMessageEnvelope, nonce_consumed: bool) -> str:
    if nonce_consumed:
        return "consumed"
    if message.nonce:
        return "provided"
    return "not-provided"


def _parse_message_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _identity_membership_reasons(
    message: AgentMessageEnvelope, context: AgentMessageVerificationContext
) -> list[str]:
    reasons: list[str] = []
    if context.require_agent_membership and message.sender_agent_id not in set(
        context.accepted_agent_ids
    ):
        reasons.append("message sender_agent_id is outside accepted identity context")
    if context.require_public_key_membership:
        if not message.issuer_public_key_id:
            reasons.append("message issuer_public_key_id is required by identity context")
        elif message.issuer_public_key_id not in set(context.accepted_public_key_ids):
            reasons.append("message issuer_public_key_id is outside accepted identity context")
    if context.accepted_attestation_ids and (
        message.issuer_attestation_id not in set(context.accepted_attestation_ids)
    ):
        reasons.append("message issuer_attestation_id is outside accepted identity context")
    return reasons


def _message_from_source(source: str, policy: GeneralIntakePolicy) -> AgentMessageEnvelope:
    try:
        raw = _read_inline_or_local_text(source, policy, label="agent message")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid agent message JSON: {exc}") from exc
    return AgentMessageEnvelope.model_validate(data)


def _inbox_from_source(source: str, policy: GeneralIntakePolicy) -> AgentInboxRecord:
    path = _safe_path(source)
    try:
        text = _read_inline_or_local_text(source, policy, label="agent inbox")
    except OSError as exc:
        raise ValueError(f"could not read agent inbox: {exc}") from exc
    try:
        if path is not None and path.suffix.lower() == ".jsonl":
            messages = [
                AgentMessageEnvelope.model_validate_json(line)
                for line in text.splitlines()
                if line.strip()
            ]
            _check_inbox_message_count(messages, policy)
            return AgentInboxRecord(inbox_id=path.stem, messages=messages)
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid agent inbox JSON: {exc}") from exc
    if isinstance(data, list):
        _check_inbox_message_count(data, policy)
        return AgentInboxRecord(
            messages=[AgentMessageEnvelope.model_validate(item) for item in data]
        )
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        _check_inbox_message_count(data["messages"], policy)
    return AgentInboxRecord.model_validate(data)


def _element_text(parent: Any, local_name: str) -> str:
    for element in parent.iter():
        if element.tag.split("}")[-1] == local_name and element.text:
            return re.sub(r"\s+", " ", element.text).strip()
    return ""


def _first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _safe_source_ref(source: str) -> str:
    return sanitize_intake_source_ref(source)
