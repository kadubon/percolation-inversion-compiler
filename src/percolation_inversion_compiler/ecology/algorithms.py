"""Capability packet ecology algorithms for ECPT active runtimes."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology.records import (
    AcceptedPacketPath,
    AutocatalyticClosureWitness,
    BasinReachabilityReport,
    BottleneckIntervention,
    BottleneckInversionPlan,
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    ClosedLoopAgentIteration,
    EdgeRelationVerificationReport,
    EdgeRelationVerifierSpec,
    EdgeWitness,
    EdgeWitnessCertificate,
    ExecutionAvailablePathCertificate,
    HiddenCapabilityInjectionReport,
    PacketCapitalLineage,
    PacketIngestionReport,
    PacketSourceKind,
    ProtocolFrameDigest,
    PsiDashboard,
    VerificationThroughputReport,
    VerifiedCapabilityPacket,
)

_PSI_COMPONENTS = ("G", "DE", "AC", "VT", "LX", "SD", "CV", "FR", "BR", "QS", "HZ")


_DEFAULT_EDGE_RELATION_SPECS: dict[str, EdgeRelationVerifierSpec] = {
    "semantic-dependency": EdgeRelationVerifierSpec(
        relation_type="semantic-dependency",
        required_evidence_markers=["sha256:"],
        minimum_confidence_lower_bound=0.2,
    ),
    "theorem-to-code": EdgeRelationVerifierSpec(
        relation_type="theorem-to-code",
        required_evidence_markers=["claim:", "code:"],
        required_relation_evidence_keys=["theorem_id", "code_symbol", "support_digest"],
        required_source_tags=["theorem"],
        required_target_tags=["code"],
        minimum_confidence_lower_bound=0.5,
    ),
    "code-to-test": EdgeRelationVerifierSpec(
        relation_type="code-to-test",
        required_evidence_markers=["code:", "test:"],
        required_relation_evidence_keys=["code_symbol", "test_id", "test_digest"],
        required_source_tags=["code"],
        required_target_tags=["test"],
        minimum_confidence_lower_bound=0.5,
    ),
    "obligation-to-verifier": EdgeRelationVerifierSpec(
        relation_type="obligation-to-verifier",
        required_evidence_markers=["obligation:", "verifier:"],
        required_relation_evidence_keys=["obligation_id", "verifier_route"],
        require_verifier_resolution=True,
        minimum_confidence_lower_bound=0.5,
    ),
    "packet-to-receiver-compatibility": EdgeRelationVerifierSpec(
        relation_type="packet-to-receiver-compatibility",
        required_evidence_markers=["sha256:"],
        require_receiver_overlap=True,
        minimum_confidence_lower_bound=0.2,
    ),
    "receiver-compatibility": EdgeRelationVerifierSpec(
        relation_type="receiver-compatibility",
        required_evidence_markers=["receiver:"],
        required_relation_evidence_keys=["receiver_family"],
        require_receiver_overlap=True,
        minimum_confidence_lower_bound=0.4,
    ),
    "execution-path": EdgeRelationVerifierSpec(
        relation_type="execution-path",
        required_evidence_markers=["execution:", "rollback:"],
        required_relation_evidence_keys=["execution_gate", "rollback_receipt", "not_executed"],
        minimum_confidence_lower_bound=0.5,
    ),
    "rollback-support": EdgeRelationVerifierSpec(
        relation_type="rollback-support",
        required_evidence_markers=["rollback:"],
        required_relation_evidence_keys=["rollback_receipt"],
        minimum_confidence_lower_bound=0.5,
    ),
    "liquidity-transfer": EdgeRelationVerifierSpec(
        relation_type="liquidity-transfer",
        required_evidence_markers=["liquidity:"],
        required_relation_evidence_keys=["source_liquidity", "target_liquidity"],
        minimum_confidence_lower_bound=0.4,
    ),
    "autocatalytic-regeneration": EdgeRelationVerifierSpec(
        relation_type="autocatalytic-regeneration",
        required_evidence_markers=["closure:", "regeneration:"],
        required_relation_evidence_keys=["closure_id", "regeneration_rule"],
        minimum_confidence_lower_bound=0.5,
    ),
}


def sha256_text(text: str) -> str:
    """Return the SHA-256 digest of a text artifact."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def packet_from_text(
    text: str,
    *,
    packet_id: str,
    source_kind: PacketSourceKind = PacketSourceKind.LOCAL,
    source_ref: str,
    tags: Sequence[str] | None = None,
) -> CapabilityPacketCandidate:
    """Construct a finite packet candidate from text without leaking local paths."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    claim = lines[0][:240] if lines else "empty packet candidate"
    token_count = len(text.split())
    inferred_tags = sorted(set(tags or []) | _infer_tags(text))
    return CapabilityPacketCandidate(
        packet_id=packet_id,
        source_kind=source_kind,
        source_ref=source_ref,
        content_sha256=sha256_text(text),
        claim=claim,
        receiver_family=["agent", "verifier"],
        evidence_refs=[f"sha256:{sha256_text(text)}"],
        expected_downstream_gain=min(1.0, token_count / 800.0),
        verification_cost=max(0.01, min(1.0, token_count / 2000.0)),
        salience_class="diagnostic" if "diagnostic" in text.lower() else "packet",
        verifier_routes=_infer_routes(text),
        dependencies=_infer_dependencies(text),
        tags=inferred_tags,
    )


def ingest_local_file(source: Path) -> PacketIngestionReport:
    """Ingest one local file as a capability packet candidate."""

    try:
        text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return PacketIngestionReport(
            report_id="packet-ingestion:local",
            accepted=False,
            source_kind=PacketSourceKind.LOCAL,
            rejected_sources=[source.name],
            reasons=["local source is not valid UTF-8 text"],
        )
    packet = packet_from_text(
        text,
        packet_id=f"packet:{source.stem}:{sha256_text(text)[:12]}",
        source_kind=PacketSourceKind.LOCAL,
        source_ref=source.name,
    )
    return PacketIngestionReport(
        report_id="packet-ingestion:local",
        accepted=True,
        source_kind=PacketSourceKind.LOCAL,
        packets=[packet],
    )


def ingest_agent_output(text: str, *, output_id: str = "agent-output") -> PacketIngestionReport:
    """Ingest an agent output as a packet candidate."""

    packet = packet_from_text(
        text,
        packet_id=f"packet:{output_id}:{sha256_text(text)[:12]}",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref=output_id,
        tags=["agent-output"],
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:{output_id}",
        accepted=True,
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        packets=[packet],
    )


def build_packet_registry(
    packets: Sequence[CapabilityPacketCandidate],
    edges: Sequence[EdgeWitness] | None = None,
    *,
    registry_id: str = "capability-packet-registry",
) -> CapabilityPacketRegistry:
    """Build a deterministic packet registry."""

    sorted_packets = sorted(packets, key=lambda packet: packet.packet_id)
    sorted_edges = sorted(edges or [], key=lambda edge: edge.edge_id)
    residual = Ledger()
    for packet in sorted_packets:
        if packet.residual_charge:
            residual = residual.add_coordinate(
                f"packet:{packet.packet_id}:residual",
                packet.residual_charge,
                kind=CoordinateKind.RESIDUAL,
            )
        if packet.expires_at == "expired":
            residual = residual.add_coordinate(
                f"packet:{packet.packet_id}:stale",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        if not packet.evidence_hash_valid:
            residual = residual.add_coordinate(
                f"packet:{packet.packet_id}:hash-invalid",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        if not packet.route_safe:
            residual = residual.add_coordinate(
                f"packet:{packet.packet_id}:unsafe-route",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        if packet.authority_required and not packet.authority_granted:
            residual = residual.add_coordinate(
                f"packet:{packet.packet_id}:authority-missing",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        if packet.hazard_charge:
            residual = residual.add_coordinate(
                f"packet:{packet.packet_id}:hazard",
                packet.hazard_charge,
                kind=CoordinateKind.RESIDUAL,
            )
    for edge in sorted_edges:
        if edge.residual:
            residual = residual.add_coordinate(
                f"edge:{edge.edge_id}:residual",
                edge.residual,
                kind=CoordinateKind.RESIDUAL,
            )
    return CapabilityPacketRegistry(
        registry_id=registry_id,
        packets=sorted_packets,
        edges=sorted_edges,
        residual_ledger=residual,
    )


def build_edge_witnesses(
    packets: Sequence[CapabilityPacketCandidate],
    *,
    minimum_confidence: float = 0.2,
) -> list[EdgeWitness]:
    """Build finite dependency, semantic, and receiver-compatibility edge witnesses."""

    by_id = {packet.packet_id: packet for packet in packets}
    witnesses: list[EdgeWitness] = []
    for packet in sorted(packets, key=lambda item: item.packet_id):
        for dependency in sorted(packet.dependencies):
            if dependency not in by_id:
                witnesses.append(
                    EdgeWitness(
                        edge_id=f"edge:missing:{dependency}:{packet.packet_id}",
                        source_packet_ids=[dependency],
                        target_packet_id=packet.packet_id,
                        edge_type="missing-dependency",
                        residual=1.0,
                        reasons=["declared dependency is absent from registry"],
                        accepted=False,
                    )
                )
                continue
            witnesses.append(
                EdgeWitness(
                    edge_id=f"edge:dependency:{dependency}:{packet.packet_id}",
                    source_packet_ids=[dependency],
                    target_packet_id=packet.packet_id,
                    edge_type="semantic-dependency",
                    confidence=1.0,
                    evidence_refs=sorted(
                        set(packet.evidence_refs + by_id[dependency].evidence_refs)
                    ),
                    accepted=True,
                )
            )
        for source in sorted(packets, key=lambda item: item.packet_id):
            if source.packet_id >= packet.packet_id:
                continue
            common_tags = sorted(set(source.tags) & set(packet.tags))
            common_receivers = sorted(set(source.receiver_family) & set(packet.receiver_family))
            if not common_tags and not common_receivers:
                continue
            confidence = min(1.0, 0.2 * len(common_tags) + 0.1 * len(common_receivers))
            if confidence < minimum_confidence:
                continue
            witnesses.append(
                EdgeWitness(
                    edge_id=f"edge:compat:{source.packet_id}:{packet.packet_id}",
                    source_packet_ids=[source.packet_id],
                    target_packet_id=packet.packet_id,
                    edge_type="packet-to-receiver-compatibility",
                    confidence=confidence,
                    residual=max(0.0, minimum_confidence - confidence),
                    evidence_refs=sorted(set(source.evidence_refs + packet.evidence_refs)),
                    reasons=[f"common_tags:{','.join(common_tags)}"] if common_tags else [],
                    accepted=confidence >= minimum_confidence,
                )
            )
    return sorted(witnesses, key=lambda edge: edge.edge_id)


def edge_certificate_from_witness(edge: EdgeWitness) -> EdgeWitnessCertificate:
    """Convert a lightweight edge witness into an auditable certificate."""

    residual = Ledger()
    if edge.residual:
        residual = residual.add_coordinate(
            f"edge-certificate:{edge.edge_id}:false-edge-residual",
            edge.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return EdgeWitnessCertificate(
        certificate_id=f"edge-certificate:{edge.edge_id}",
        edge_id=edge.edge_id,
        relation_type=edge.edge_type,
        source_packet_ids=edge.source_packet_ids,
        target_packet_id=edge.target_packet_id,
        evidence_refs=edge.evidence_refs,
        confidence_lower_bound=edge.confidence,
        false_edge_residual=edge.residual,
        expires_at=edge.expires_at,
        accepted=edge.accepted,
        reasons=edge.reasons,
        residual_ledger=residual,
        relation_evidence=_relation_evidence_from_edge(edge),
    )


def verify_edge_witness_certificate(
    registry: CapabilityPacketRegistry,
    certificate: EdgeWitnessCertificate,
) -> CheckResult:
    """Check an edge certificate against packet identities and finite evidence."""

    packet_ids = {packet.packet_id for packet in registry.packets}
    reasons: list[str] = []
    if certificate.target_packet_id not in packet_ids:
        reasons.append("target packet is absent from registry")
    missing_sources = sorted(set(certificate.source_packet_ids) - packet_ids)
    if missing_sources:
        reasons.append("source packet is absent from registry")
    if not certificate.source_packet_ids:
        reasons.append("edge certificate has no source packets")
    if certificate.confidence_lower_bound < 0.0:
        reasons.append("confidence lower bound is negative")
    if certificate.false_edge_residual < 0.0:
        reasons.append("false-edge residual is negative")
    if certificate.expires_at == "expired":
        reasons.append("edge certificate is expired")
    if not certificate.evidence_refs:
        reasons.append("edge certificate has no evidence references")
    accepted = certificate.accepted and not reasons
    residual = certificate.residual_ledger
    if not accepted:
        residual = residual.add_coordinate(
            f"edge-certificate:{certificate.certificate_id}:diagnostic",
            max(1.0, certificate.false_edge_residual),
            kind=CoordinateKind.RESIDUAL,
        )
    return CheckResult(
        accepted=accepted,
        status=ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
        finite_checks_passed=not reasons,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
        missing_obligations=missing_sources,
        residual_ledger=residual,
    )


def edge_relation_verifier_spec(relation_type: str) -> EdgeRelationVerifierSpec:
    """Return the built-in semantic verifier spec for a relation type."""

    return _DEFAULT_EDGE_RELATION_SPECS.get(
        relation_type,
        EdgeRelationVerifierSpec(
            relation_type=relation_type,
            required_evidence_markers=["sha256:"],
        ),
    )


def verify_edge_relation(
    registry: CapabilityPacketRegistry,
    certificate: EdgeWitnessCertificate,
    verifier_spec: EdgeRelationVerifierSpec | None = None,
) -> EdgeRelationVerificationReport:
    """Check semantic relation evidence for an edge certificate."""

    spec = verifier_spec or edge_relation_verifier_spec(certificate.relation_type)
    structural = verify_edge_witness_certificate(registry, certificate)
    packet_by_id = {packet.packet_id: packet for packet in registry.packets}
    source_packets = [
        packet_by_id[packet_id]
        for packet_id in certificate.source_packet_ids
        if packet_id in packet_by_id
    ]
    target_packet = packet_by_id.get(certificate.target_packet_id)
    refs = sorted(set(certificate.evidence_refs))
    reasons = list(structural.reasons)
    residual = structural.residual_ledger
    if certificate.relation_type != spec.relation_type:
        reasons.append("edge relation type does not match verifier spec")
    if certificate.confidence_lower_bound < spec.minimum_confidence_lower_bound:
        reasons.append("edge relation confidence is below verifier threshold")
    missing_markers = [
        marker
        for marker in spec.required_evidence_markers
        if not any(marker in ref for ref in refs)
    ]
    if missing_markers:
        reasons.append("edge relation evidence markers are missing")
    missing_relation_keys = sorted(
        key
        for key in spec.required_relation_evidence_keys
        if key not in certificate.relation_evidence
    )
    if missing_relation_keys:
        reasons.append("edge relation structured evidence is missing")
    if spec.required_source_tags and not any(
        set(packet.tags) & set(spec.required_source_tags) for packet in source_packets
    ):
        reasons.append("edge source packet tags do not satisfy relation verifier")
    if target_packet is None:
        reasons.append("edge target packet is absent from registry")
    elif spec.required_target_tags and not (
        set(target_packet.tags) & set(spec.required_target_tags)
    ):
        reasons.append("edge target packet tags do not satisfy relation verifier")
    if spec.require_receiver_overlap and target_packet is not None:
        receiver_overlap = any(
            set(packet.receiver_family) & set(target_packet.receiver_family)
            for packet in source_packets
        )
        if not receiver_overlap:
            reasons.append("edge relation has no receiver-family overlap")
    if spec.require_verifier_resolution and certificate.verifier_resolution_id is None:
        reasons.append("edge relation requires a verifier resolution id")
    if reasons:
        residual = residual.add_coordinate(
            f"edge-relation:{certificate.certificate_id}:semantic-diagnostic",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons and structural.accepted
    return EdgeRelationVerificationReport(
        report_id=f"edge-relation:{certificate.certificate_id}:{spec.relation_type}",
        certificate_id=certificate.certificate_id,
        relation_type=spec.relation_type,
        accepted=accepted,
        finite_checks_passed=not reasons,
        operationally_usable=accepted,
        settled=False,
        matched_evidence_refs=refs,
        missing_evidence_markers=missing_markers,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
    )


def verification_throughput(
    registry: CapabilityPacketRegistry,
) -> VerificationThroughputReport:
    """Compute finite packet ecology throughput metrics."""

    packets = registry.packets
    edges = registry.edges
    total = len(packets)
    accepted_edges = [edge for edge in edges if edge.accepted]
    rejected_edges = [edge for edge in edges if not edge.accepted]
    stale = [packet for packet in packets if packet.expires_at == "expired"]
    unresolved = sum(len(packet.verifier_routes) for packet in packets) + len(rejected_edges)
    hash_mismatch = sum(
        1
        for packet in packets
        if not packet.evidence_refs or not packet.evidence_refs[0].endswith(packet.content_sha256)
    )
    false_liquidity = sum(
        1
        for packet in packets
        if (
            packet.expected_downstream_gain <= 0.0
            or packet.verification_cost > packet.expected_downstream_gain
        )
    )
    low_contribution = sum(
        max(0.0, packet.verification_cost)
        for packet in packets
        if packet.expected_downstream_gain <= packet.verification_cost
    )
    return VerificationThroughputReport(
        packet_inflow=total,
        accepted_packets=len(accepted_edges),
        rejected_packets=len(rejected_edges),
        abstained_packets=max(0, total - len(accepted_edges) - len(rejected_edges)),
        unresolved_obligation_backlog=unresolved,
        verifier_latency_proxy=sum(packet.verification_cost for packet in packets) / max(1, total),
        evidence_hash_mismatch_rate=0.0 if total == 0 else hash_mismatch / total,
        stale_packet_ratio=0.0 if total == 0 else len(stale) / total,
        false_liquidity_rate=0.0 if total == 0 else false_liquidity / total,
        residual_debt_growth=registry.residual_ledger.burden_sum(),
        low_contribution_queue_occupation=low_contribution,
    )


def build_psi_dashboard(
    registry: CapabilityPacketRegistry,
    *,
    threshold: Mapping[str, float] | None = None,
    target_tags: Sequence[str] | None = None,
    closure_witnesses: Sequence[AutocatalyticClosureWitness] | None = None,
    execution_paths: Sequence[ExecutionAvailablePathCertificate] | None = None,
    basin: CapabilityBasinContract | None = None,
) -> PsiDashboard:
    """Build a protocol-relative finite ASI-proxy bundle dashboard."""

    active_threshold = {key: 0.5 for key in _PSI_COMPONENTS}
    if threshold is not None:
        active_threshold.update({key: float(value) for key, value in threshold.items()})
    throughput = verification_throughput(registry)
    packet_ids = {packet.packet_id for packet in registry.packets}
    accepted_edges = [edge for edge in registry.edges if edge.accepted]
    reachable = _reachable_packets(packet_ids, accepted_edges)
    total = max(1, len(packet_ids))
    route_count = len({route for packet in registry.packets for route in packet.verifier_routes})
    tag_targets = set(target_tags or [])
    target_hits = sum(1 for packet in registry.packets if tag_targets & set(packet.tags))
    accepted_closures = [witness for witness in closure_witnesses or [] if witness.accepted]
    accepted_execution_paths = [path for path in execution_paths or [] if path.accepted]
    residual = registry.residual_ledger
    if accepted_closures:
        ac_score = min(
            1.0,
            sum(max(0.0, witness.closure_strength) for witness in accepted_closures)
            / max(1, len(accepted_closures)),
        )
    else:
        ac_score = _cycle_proxy(accepted_edges)
        if ac_score > 0.0:
            residual = residual.add_coordinate(
                f"psi:{registry.registry_id}:ac-cycle-proxy-fallback",
                1.0 - ac_score,
                kind=CoordinateKind.RESIDUAL,
            )
    if accepted_execution_paths:
        de_score = min(1.0, len(accepted_execution_paths) / max(1, total))
    else:
        de_score = min(1.0, len(accepted_edges) / max(1, total))
        if de_score > 0.0:
            residual = residual.add_coordinate(
                f"psi:{registry.registry_id}:de-edge-density-fallback",
                1.0 - de_score,
                kind=CoordinateKind.RESIDUAL,
            )
    if basin is not None:
        basin_paths = find_accepted_paths_to_basin(registry, basin)
        br_score = min(1.0, len(basin_paths) / max(1, len(basin.target_basis) or 1))
    else:
        br_score = 0.0 if not tag_targets else target_hits / total
    components = {
        "G": len(reachable) / total,
        "DE": de_score,
        "AC": ac_score,
        "VT": _bounded_ratio(
            throughput.accepted_packets + 1.0,
            throughput.unresolved_obligation_backlog + 1.0,
        ),
        "LX": min(1.0, route_count / max(1, total)),
        "SD": _bounded_ratio(
            sum(packet.expected_downstream_gain for packet in registry.packets),
            sum(packet.verification_cost for packet in registry.packets) + 1.0,
        ),
        "CV": max(0.0, 1.0 - registry.residual_ledger.burden_sum()),
        "FR": max(0.0, 1.0 - throughput.false_liquidity_rate),
        "BR": br_score,
        "QS": _queue_salience_score(throughput),
        "HZ": _hazard_authority_score(registry),
    }
    distance = {
        key: max(0.0, active_threshold[key] - components.get(key, 0.0))
        for key in sorted(active_threshold)
    }
    limiting = sorted(
        [key for key, gap in distance.items() if gap > 0.0],
        key=lambda key: (-distance[key], key),
    )
    return PsiDashboard(
        dashboard_id=f"psi:{registry.registry_id}",
        components=dict(sorted(components.items())),
        threshold=dict(sorted(active_threshold.items())),
        distance_to_threshold=distance,
        limiting_components=limiting,
        throughput=throughput,
        residual_ledger=residual,
    )


def check_basin_reachability(
    registry: CapabilityPacketRegistry,
    basin: CapabilityBasinContract,
) -> BasinReachabilityReport:
    """Check finite basin reachability from packets, edges, routes, and receivers."""

    packets = sorted(registry.packets, key=lambda packet: packet.packet_id)
    edges = sorted(
        [edge for edge in registry.edges if edge.accepted],
        key=lambda edge: edge.edge_id,
    )
    accepted_edge_ids = [edge.edge_id for edge in edges]
    receiver_compatible = not basin.receiver_family or any(
        set(packet.receiver_family) & set(basin.receiver_family) for packet in packets
    )
    packet_type_hits = {
        required: any(
            required in set(packet.tags)
            or required == packet.salience_class
            or required == packet.source_kind.value
            for packet in packets
        )
        for required in basin.required_packet_types
    }
    edge_type_hits = {
        required: any(required == edge.edge_type for edge in edges)
        for required in basin.required_edge_types
    }
    routes = {route for packet in packets for route in packet.verifier_routes}
    missing_routes = sorted(set(basin.required_verifier_routes) - routes)
    accepted_paths = find_accepted_paths_to_basin(registry, basin)
    reachable = sorted({packet_id for path in accepted_paths for packet_id in path.packet_ids})
    path_cost = min((path.cost for path in accepted_paths), default=0.0)
    missing_packet_types = sorted(
        required for required, present in packet_type_hits.items() if not present
    )
    missing_edge_types = sorted(
        required for required, present in edge_type_hits.items() if not present
    )
    reasons: list[str] = []
    if not receiver_compatible:
        reasons.append("no packet is compatible with basin receiver family")
    if basin.target_basis and not accepted_paths:
        reasons.append("target basis is not reached by accepted packet paths")
    if missing_packet_types:
        reasons.append("required packet type is missing")
    if missing_edge_types:
        reasons.append("required edge type is missing")
    if missing_routes:
        reasons.append("required verifier route is missing")
    if path_cost > basin.max_path_cost:
        reasons.append("accepted path cost exceeds basin maximum")
    residual = registry.residual_ledger
    for reason in reasons:
        residual = residual.add_coordinate(
            f"basin:{basin.basin_id}:{reason.replace(' ', '-')}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons
    return BasinReachabilityReport(
        report_id=f"basin-reachability:{basin.basin_id}:{registry.registry_id}",
        basin_id=basin.basin_id,
        accepted=accepted,
        reachable_packet_ids=reachable,
        accepted_edge_ids=accepted_edge_ids,
        accepted_paths=accepted_paths,
        missing_packet_types=missing_packet_types,
        missing_edge_types=missing_edge_types,
        missing_verifier_routes=missing_routes,
        receiver_compatible=receiver_compatible,
        path_cost_lower_bound=path_cost,
        residual_ledger=residual,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
    )


def find_accepted_paths_to_basin(
    registry: CapabilityPacketRegistry,
    basin: CapabilityBasinContract,
) -> list[AcceptedPacketPath]:
    """Return accepted finite packet paths satisfying a basin contract."""

    packet_by_id = {packet.packet_id: packet for packet in registry.packets}
    accepted_edges = [edge for edge in registry.edges if edge.accepted]
    incoming: dict[str, list[EdgeWitness]] = {}
    for edge in accepted_edges:
        incoming.setdefault(edge.target_packet_id, []).append(edge)
    targets = [
        packet
        for packet in registry.packets
        if not basin.target_basis
        or any(
            target in set(packet.tags) or target in packet.claim or target == packet.packet_id
            for target in basin.target_basis
        )
    ]
    paths: list[AcceptedPacketPath] = []
    for target in sorted(targets, key=lambda item: item.packet_id):
        route_ids = sorted(set(target.verifier_routes))
        residual = Ledger()
        reasons: list[str] = []
        edge_ids: list[str] = []
        packet_ids = [target.packet_id]
        cost = max(0.0, target.verification_cost + target.residual_charge + target.hazard_charge)
        queue: deque[tuple[str, int]] = deque([(target.packet_id, 0)])
        seen = {target.packet_id}
        while queue:
            current_id, depth = queue.popleft()
            if depth >= 4:
                continue
            for edge in sorted(incoming.get(current_id, []), key=lambda item: item.edge_id):
                if basin.required_edge_types and edge.edge_type not in basin.required_edge_types:
                    continue
                edge_ids.append(edge.edge_id)
                cost += max(0.0, 1.0 - edge.confidence + edge.residual)
                route_ids.extend(
                    route
                    for source_id in edge.source_packet_ids
                    for route in packet_by_id.get(source_id, target).verifier_routes
                )
                for source_id in edge.source_packet_ids:
                    if source_id in packet_by_id and source_id not in seen:
                        seen.add(source_id)
                        packet_ids.append(source_id)
                        queue.append((source_id, depth + 1))
        if basin.receiver_family and not (set(target.receiver_family) & set(basin.receiver_family)):
            reasons.append("target packet receiver family does not match basin")
        missing_routes = sorted(set(basin.required_verifier_routes) - set(route_ids))
        if missing_routes:
            reasons.append("accepted path lacks required verifier routes")
        if basin.required_packet_types and not all(
            any(
                required in set(packet_by_id[packet_id].tags)
                or required == packet_by_id[packet_id].salience_class
                for packet_id in packet_ids
                if packet_id in packet_by_id
            )
            for required in basin.required_packet_types
        ):
            reasons.append("accepted path lacks required packet types")
        if cost > basin.max_path_cost:
            reasons.append("accepted path cost exceeds basin maximum")
        if reasons:
            for reason in reasons:
                residual = residual.add_coordinate(
                    f"accepted-path:{target.packet_id}:{reason.replace(' ', '-')}",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
        path = AcceptedPacketPath(
            path_id=f"accepted-path:{basin.basin_id}:{target.packet_id}",
            packet_ids=sorted(set(packet_ids)),
            edge_ids=sorted(set(edge_ids)),
            route_ids=sorted(set(route_ids)),
            cost=cost,
            residual_ledger=residual,
            accepted=not reasons,
            reasons=sorted(set(reasons)),
        )
        if path.accepted:
            paths.append(path)
    return sorted(paths, key=lambda item: (item.cost, item.path_id))


def find_autocatalytic_closures(
    registry: CapabilityPacketRegistry,
    basin: CapabilityBasinContract | None = None,
    *,
    minimum_strength: float = 0.5,
) -> list[AutocatalyticClosureWitness]:
    """Find finite productive packet closures in the accepted edge graph.

    ECPT's active collective phase is not raw packet volume.  A closure is only
    accepted when accepted edges regenerate at least one packet in the component
    and productive packet capital offsets verification, hazard, and residual
    charges.
    """

    packet_by_id = {packet.packet_id: packet for packet in registry.packets}
    accepted_edges = sorted(
        [edge for edge in registry.edges if edge.accepted],
        key=lambda item: item.edge_id,
    )
    adjacency: dict[str, set[str]] = {packet_id: set() for packet_id in packet_by_id}
    edge_by_pair: dict[tuple[str, str], list[EdgeWitness]] = {}
    for edge in accepted_edges:
        for source in edge.source_packet_ids:
            if source in packet_by_id and edge.target_packet_id in packet_by_id:
                adjacency.setdefault(source, set()).add(edge.target_packet_id)
                edge_by_pair.setdefault((source, edge.target_packet_id), []).append(edge)
    closures: list[AutocatalyticClosureWitness] = []
    seen_components: set[tuple[str, ...]] = set()
    for packet_id in sorted(packet_by_id):
        reached = _reachable_from(packet_id, adjacency)
        component = sorted(
            node for node in reached if packet_id in _reachable_from(node, adjacency)
        )
        if len(component) < 2:
            self_edges = edge_by_pair.get((packet_id, packet_id), [])
            if not self_edges:
                continue
            component = [packet_id]
        key = tuple(component)
        if key in seen_components:
            continue
        seen_components.add(key)
        internal_edges = [
            edge
            for edge in accepted_edges
            if edge.target_packet_id in component
            and any(source in component for source in edge.source_packet_ids)
        ]
        regeneration_edges = [
            edge
            for edge in internal_edges
            if edge.edge_type in {"autocatalytic-regeneration", "semantic-dependency"}
        ]
        productive_packets = [
            packet_by_id[item]
            for item in component
            if _packet_productivity(packet_by_id[item]) > 0.0
        ]
        seed_packets = sorted(
            {
                source
                for edge in accepted_edges
                if edge.target_packet_id in component
                for source in edge.source_packet_ids
                if source not in component
            }
        )
        receiver_ok = True
        if basin is not None and basin.receiver_family:
            receiver_ok = any(
                set(packet_by_id[item].receiver_family) & set(basin.receiver_family)
                for item in component
            )
        closure_strength = min(
            (edge.confidence for edge in internal_edges),
            default=0.0,
        )
        productivity = sum(_packet_productivity(packet) for packet in productive_packets)
        false_liquidity = (
            0.0
            if not component
            else sum(
                1
                for item in component
                if packet_by_id[item].verification_cost
                > packet_by_id[item].expected_downstream_gain
            )
            / len(component)
        )
        residual = Ledger()
        reasons: list[str] = []
        if closure_strength < minimum_strength:
            reasons.append("closure strength is below threshold")
        if not regeneration_edges:
            reasons.append("closure has no accepted regeneration edge")
        if not productive_packets:
            reasons.append("closure has no productive packet")
        if false_liquidity > 0.25:
            reasons.append("closure false-liquidity rate exceeds bound")
        if not receiver_ok:
            reasons.append("closure is not receiver-compatible with basin")
        if reasons:
            residual = residual.add_coordinate(
                f"closure:{registry.registry_id}:{'-'.join(component)}:diagnostic",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        accepted = not reasons
        closures.append(
            AutocatalyticClosureWitness(
                witness_id=f"closure:{registry.registry_id}:{sha256_text('|'.join(component))[:12]}",
                closure_packet_ids=component,
                internal_edge_ids=sorted({edge.edge_id for edge in internal_edges}),
                regeneration_edge_ids=sorted({edge.edge_id for edge in regeneration_edges}),
                productive_packet_ids=sorted(packet.packet_id for packet in productive_packets),
                external_seed_packet_ids=seed_packets,
                closure_strength=closure_strength,
                productivity_lower_bound=productivity,
                false_liquidity_rate=false_liquidity,
                residual_ledger=residual,
                accepted=accepted,
                finite_checks_passed=accepted,
                operationally_usable=accepted,
                settled=False,
                reasons=sorted(set(reasons)),
            )
        )
    return sorted(closures, key=lambda item: item.witness_id)


def find_execution_available_paths(
    registry: CapabilityPacketRegistry,
    basin: CapabilityBasinContract,
    *,
    constraint_frame: Mapping[str, object] | None = None,
) -> list[ExecutionAvailablePathCertificate]:
    """Build execution-available, not-executed path certificates for a basin."""

    return [
        check_execution_available_path(
            _execution_certificate_from_path(registry, path, constraint_frame=constraint_frame),
            registry,
            constraint_frame=constraint_frame,
        )
        for path in find_accepted_paths_to_basin(registry, basin)
    ]


def check_execution_available_path(
    certificate: ExecutionAvailablePathCertificate,
    registry: CapabilityPacketRegistry,
    *,
    constraint_frame: Mapping[str, object] | None = None,
) -> ExecutionAvailablePathCertificate:
    """Check that a path is available for execution without executing it."""

    packet_by_id = {packet.packet_id: packet for packet in registry.packets}
    edge_ids = {edge.edge_id for edge in registry.edges if edge.accepted}
    residual = certificate.residual_ledger
    reasons = list(certificate.reasons)
    missing_packets = sorted(set(certificate.packet_ids) - set(packet_by_id))
    missing_edges = sorted(set(certificate.edge_ids) - edge_ids)
    if missing_packets:
        reasons.append("execution path references missing packets")
    if missing_edges:
        reasons.append("execution path references missing accepted edges")
    if not certificate.not_executed:
        reasons.append("execution path has already been executed")
    if not certificate.execution_gates:
        reasons.append("execution path lacks explicit execution gates")
    if not certificate.authority_granted:
        reasons.append("execution path lacks authority grant")
    if not certificate.rollback_available:
        reasons.append("execution path lacks rollback support")
    if not certificate.receiver_context:
        reasons.append("execution path lacks receiver context")
    if not certificate.evidence_refs:
        reasons.append("execution path lacks evidence refs")
    if constraint_frame is not None:
        hard_gates = constraint_frame.get("hard_gates")
        if isinstance(hard_gates, Mapping) and not all(
            bool(value) for value in hard_gates.values()
        ):
            reasons.append("constraint frame has a closed hard gate")
    for packet_id in certificate.packet_ids:
        packet = packet_by_id.get(packet_id)
        if packet is None:
            continue
        if packet.authority_required and not packet.authority_granted:
            reasons.append("path packet lacks required authority")
        if not packet.rollback_available:
            reasons.append("path packet lacks rollback support")
        if not packet.route_safe:
            reasons.append("path packet route is unsafe")
    if reasons:
        residual = residual.add_coordinate(
            f"execution-available:{certificate.certificate_id}:diagnostic",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "residual_ledger": residual,
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "reasons": sorted(set(reasons)),
        }
    )


def check_no_hidden_capability_injection(
    registry: CapabilityPacketRegistry,
    protocol: ProtocolFrameDigest,
    *,
    runtime_events: Sequence[Mapping[str, object]] | None = None,
) -> HiddenCapabilityInjectionReport:
    """Reject packet, edge, evidence, or event sources outside the protocol frame."""

    allowed_sources = set(protocol.allowed_source_kinds)
    allowed_routes = set(protocol.allowed_route_ids)
    allowed_packets = set(protocol.allowed_packet_ids)
    allowed_prefixes = protocol.allowed_evidence_prefixes or ["sha256:"]
    residual = Ledger()
    rejected_packets: list[str] = []
    rejected_edges: list[str] = []
    rejected_events: list[str] = []
    rejected_refs: list[str] = []
    reasons: list[str] = []
    for packet in registry.packets:
        if allowed_sources and packet.source_kind.value not in allowed_sources:
            rejected_packets.append(packet.packet_id)
            reasons.append("packet source kind is outside protocol frame")
        if allowed_packets and packet.packet_id not in allowed_packets:
            rejected_packets.append(packet.packet_id)
            reasons.append("packet id is outside declared protocol population")
        unknown_routes = (
            sorted(set(packet.verifier_routes) - allowed_routes) if allowed_routes else []
        )
        if unknown_routes:
            rejected_packets.append(packet.packet_id)
            reasons.append("packet verifier route is outside protocol catalog")
        for ref in packet.evidence_refs:
            if not any(ref.startswith(prefix) for prefix in allowed_prefixes):
                rejected_refs.append(ref)
                reasons.append("packet evidence ref is outside allowed evidence prefixes")
    packet_ids = {packet.packet_id for packet in registry.packets}
    for edge in registry.edges:
        if edge.target_packet_id not in packet_ids or any(
            source not in packet_ids for source in edge.source_packet_ids
        ):
            rejected_edges.append(edge.edge_id)
            reasons.append("edge references packet outside registry")
    for event in runtime_events or []:
        event_type = str(event.get("event_type", ""))
        if event_type and not event_type.startswith(
            ("runtime-", "route-", "packet-", "collective-")
        ):
            rejected_events.append(str(event.get("event_id", event_type)))
            reasons.append("runtime event type is outside protocol runtime vocabulary")
    if reasons:
        rejected_items = set(rejected_packets + rejected_edges + rejected_events + rejected_refs)
        for item in sorted(rejected_items):
            residual = residual.add_coordinate(
                f"hidden-injection:{protocol.protocol_id}:{item}",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
    accepted = not reasons and bool(protocol.accepted or protocol.sha256)
    if not protocol.accepted and not protocol.sha256:
        reasons.append("protocol frame digest is not accepted or content-addressed")
        accepted = False
    return HiddenCapabilityInjectionReport(
        report_id=f"hidden-injection:{protocol.protocol_id}:{registry.registry_id}",
        protocol_id=protocol.protocol_id,
        checked_packet_ids=sorted(packet_ids),
        rejected_packet_ids=sorted(set(rejected_packets)),
        rejected_edge_ids=sorted(set(rejected_edges)),
        rejected_event_ids=sorted(set(rejected_events)),
        rejected_evidence_refs=sorted(set(rejected_refs)),
        allowed_source_kinds=sorted(allowed_sources),
        allowed_route_ids=sorted(allowed_routes),
        allowed_packet_ids=sorted(allowed_packets),
        residual_ledger=residual,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
    )


def build_packet_capital_lineage(
    packet: VerifiedCapabilityPacket | CapabilityPacketCandidate,
    *,
    parent_packet_ids: Sequence[str] | None = None,
    edge_certificate_ids: Sequence[str] | None = None,
    verifier_resolution_ids: Sequence[str] | None = None,
    runtime_event_ids: Sequence[str] | None = None,
    protocol_frame_sha256: str | None = None,
) -> PacketCapitalLineage:
    """Build a deterministic lineage record for finite packet capital."""

    source_candidate_id = getattr(packet, "source_candidate_id", None)
    packet_id = packet.packet_id
    residual_external = getattr(packet, "residual_external_obligations", [])
    accepted = bool(protocol_frame_sha256) and not residual_external
    return PacketCapitalLineage(
        lineage_id=f"lineage:{packet_id}:{sha256_text(protocol_frame_sha256 or packet_id)[:12]}",
        packet_id=packet_id,
        source_candidate_id=source_candidate_id,
        parent_packet_ids=sorted(set(parent_packet_ids or [])),
        edge_certificate_ids=sorted(set(edge_certificate_ids or [])),
        verifier_resolution_ids=sorted(set(verifier_resolution_ids or [])),
        runtime_event_ids=sorted(set(runtime_event_ids or [])),
        protocol_frame_sha256=protocol_frame_sha256,
        residual_external_obligations=sorted(set(residual_external)),
        accepted=accepted,
        reasons=[]
        if accepted
        else ["packet lineage lacks complete protocol digest or residual-free scope"],
    )


def build_bottleneck_plan(
    registry: CapabilityPacketRegistry,
    dashboard: PsiDashboard,
    *,
    profile: str = "development",
) -> BottleneckInversionPlan:
    """Build ranked interventions for limiting finite proxy components."""

    interventions: list[BottleneckIntervention] = []
    for component in dashboard.limiting_components:
        gap = dashboard.distance_to_threshold.get(component, 0.0)
        action_kind = _action_for_component(component)
        cost = 0.1 + dashboard.throughput.verifier_latency_proxy
        risk = 0.05 if component in {"FR", "CV"} else 0.01
        score = gap - cost - risk
        routes = sorted({route for packet in registry.packets for route in packet.verifier_routes})
        interventions.append(
            BottleneckIntervention(
                intervention_id=f"intervention:{component.lower()}:{action_kind}",
                target_component=component,
                action_kind=action_kind,
                expected_gain=gap,
                verification_cost=cost,
                risk_charge=risk,
                required_routes=routes[:4],
                score=score,
            )
        )
    interventions = sorted(interventions, key=lambda item: (-item.score, item.intervention_id))
    after = dict(dashboard.components)
    for intervention in interventions:
        after[intervention.target_component] = min(
            1.0,
            after.get(intervention.target_component, 0.0) + max(0.0, intervention.expected_gain),
        )
    return BottleneckInversionPlan(
        plan_id=f"bottleneck-plan:{dashboard.dashboard_id}:{profile}",
        accepted=bool(interventions),
        interventions=interventions,
        limiting_components=dashboard.limiting_components,
        before_psi=dashboard.components,
        after_psi_lower_bound=dict(sorted(after.items())),
        residual_ledger=dashboard.residual_ledger,
        settled=False,
    )


def closed_loop_iteration(
    *,
    state_id: str,
    agent_output: str,
    threshold: Mapping[str, float] | None = None,
) -> ClosedLoopAgentIteration:
    """Run one deterministic packet-ingest, edge-build, Psi, and bottleneck cycle."""

    ingestion = ingest_agent_output(agent_output, output_id=state_id)
    edges = build_edge_witnesses(ingestion.packets)
    registry = build_packet_registry(ingestion.packets, edges, registry_id=f"registry:{state_id}")
    dashboard = build_psi_dashboard(registry, threshold=threshold, target_tags=["agent-output"])
    plan = build_bottleneck_plan(registry, dashboard)
    tasks = [
        f"{intervention.action_kind}:{intervention.target_component}"
        for intervention in plan.interventions[:3]
    ]
    return ClosedLoopAgentIteration(
        iteration_id=f"closed-loop:{state_id}",
        ingestion=ingestion,
        registry=registry,
        psi=dashboard,
        plan=plan,
        next_agent_tasks=tasks,
        residual_ledger=registry.residual_ledger,
    )


def registry_from_json(data: Mapping[str, object]) -> CapabilityPacketRegistry:
    """Parse a packet registry from portable JSON."""

    raw_packets = data.get("packets", [])
    raw_edges = data.get("edges", [])
    if not isinstance(raw_packets, list):
        raise ValueError("registry packets must be a list")
    if not isinstance(raw_edges, list):
        raise ValueError("registry edges must be a list")
    return CapabilityPacketRegistry(
        registry_id=str(data.get("registry_id", "capability-packet-registry")),
        packets=[CapabilityPacketCandidate.model_validate(packet) for packet in raw_packets],
        edges=[EdgeWitness.model_validate(edge) for edge in raw_edges],
    )


def _infer_tags(text: str) -> set[str]:
    lower = text.lower()
    tags = set()
    for key in [
        "ecpt",
        "bit",
        "trc",
        "sqot",
        "packet",
        "verifier",
        "obligation",
        "residual",
        "queue",
        "salience",
        "phase",
        "frontier",
    ]:
        if key in lower:
            tags.add(key)
    return tags or {"general"}


def _infer_routes(text: str) -> list[str]:
    lower = text.lower()
    routes: list[str] = []
    if "proxy" in lower or "target" in lower:
        routes.append("ecpt.adapters.proxy.verify_target_contract")
    if "bridge" in lower or "sqot" in lower:
        routes.append("ecpt.adapters.bridge.verify_cross_theory_bridge")
    if "telemetry" in lower:
        routes.append("trc.adapters.telemetry.verify_calibration_window")
    if "physical" in lower or "trace" in lower:
        routes.append("trc.adapters.physical_hybrid.verify_envelope")
    return sorted(set(routes))


def _infer_dependencies(text: str) -> list[str]:
    dependencies: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("depends:"):
            dependencies.extend(item.strip() for item in stripped[8:].split(",") if item.strip())
    return sorted(set(dependencies))


def _reachable_packets(packet_ids: set[str], edges: Sequence[EdgeWitness]) -> set[str]:
    if not packet_ids:
        return set()
    outgoing: dict[str, list[str]] = {}
    for edge in edges:
        if not edge.accepted:
            continue
        for source in edge.source_packet_ids:
            outgoing.setdefault(source, []).append(edge.target_packet_id)
    start = sorted(packet_ids)[0]
    reached = {start}
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        for target in outgoing.get(current, []):
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def _reachable_from(start: str, adjacency: Mapping[str, set[str]]) -> set[str]:
    reached = {start}
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        for target in sorted(adjacency.get(current, set())):
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def _cycle_proxy(edges: Sequence[EdgeWitness]) -> float:
    pairs = {
        (source, edge.target_packet_id)
        for edge in edges
        if edge.accepted
        for source in edge.source_packet_ids
    }
    if not pairs:
        return 0.0
    reciprocal = sum(1 for left, right in pairs if (right, left) in pairs)
    return min(1.0, reciprocal / len(pairs))


def _bounded_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 1.0
    return max(0.0, min(1.0, numerator / denominator))


def _queue_salience_score(throughput: VerificationThroughputReport) -> float:
    backlog_charge = min(1.0, throughput.unresolved_obligation_backlog / 10.0)
    latency_charge = min(1.0, throughput.verifier_latency_proxy)
    stale_charge = min(1.0, throughput.stale_packet_ratio)
    obstruction_charge = min(1.0, throughput.low_contribution_queue_occupation)
    return max(
        0.0,
        1.0
        - (
            0.35 * backlog_charge
            + 0.2 * latency_charge
            + 0.25 * stale_charge
            + 0.2 * obstruction_charge
        ),
    )


def _hazard_authority_score(registry: CapabilityPacketRegistry) -> float:
    packets = registry.packets
    total = max(1, len(packets))
    hazard = min(1.0, sum(max(0.0, packet.hazard_charge) for packet in packets) / total)
    authority_violations = sum(
        1 for packet in packets if packet.authority_required and not packet.authority_granted
    )
    unsafe_routes = sum(1 for packet in packets if not packet.route_safe)
    rollback_missing = sum(1 for packet in packets if not packet.rollback_available)
    return max(
        0.0,
        1.0
        - (
            0.4 * hazard
            + 0.2 * authority_violations / total
            + 0.2 * unsafe_routes / total
            + 0.2 * rollback_missing / total
        ),
    )


def _packet_productivity(packet: CapabilityPacketCandidate) -> float:
    return max(
        0.0,
        packet.expected_downstream_gain
        - packet.verification_cost
        - packet.residual_charge
        - packet.hazard_charge,
    )


def _relation_evidence_from_edge(edge: EdgeWitness) -> dict[str, str]:
    if edge.edge_type == "packet-to-receiver-compatibility":
        return {"receiver_family": "overlap"}
    if edge.edge_type == "semantic-dependency":
        return {"dependency": ",".join(edge.source_packet_ids)}
    if edge.edge_type == "execution-path":
        return {
            "execution_gate": "declared",
            "not_executed": "true",
            "rollback_receipt": "declared",
        }
    return {}


def _execution_certificate_from_path(
    registry: CapabilityPacketRegistry,
    path: AcceptedPacketPath,
    *,
    constraint_frame: Mapping[str, object] | None,
) -> ExecutionAvailablePathCertificate:
    packet_by_id = {packet.packet_id: packet for packet in registry.packets}
    edge_by_id = {edge.edge_id: edge for edge in registry.edges}
    packets = [
        packet_by_id[packet_id] for packet_id in path.packet_ids if packet_id in packet_by_id
    ]
    edges = [edge_by_id[edge_id] for edge_id in path.edge_ids if edge_id in edge_by_id]
    receivers = sorted({receiver for packet in packets for receiver in packet.receiver_family})
    refs = sorted(
        {ref for packet in packets for ref in packet.evidence_refs}
        | {ref for edge in edges for ref in edge.evidence_refs}
    )
    hard_gates = constraint_frame.get("hard_gates") if constraint_frame is not None else None
    gates = (
        sorted(str(key) for key in hard_gates) if isinstance(hard_gates, Mapping) else ["ExecGate"]
    )
    return ExecutionAvailablePathCertificate(
        certificate_id=f"execution-available:{path.path_id}",
        path_id=path.path_id,
        packet_ids=path.packet_ids,
        edge_ids=path.edge_ids,
        route_ids=path.route_ids,
        not_executed=True,
        execution_gates=gates,
        authority_granted=all(
            not packet.authority_required or packet.authority_granted for packet in packets
        ),
        rollback_available=all(packet.rollback_available for packet in packets),
        receiver_context=receivers,
        evidence_refs=refs,
        constraint_frame_id=str(
            constraint_frame.get("constraint_frame_id", "default-constraint-frame")
        )
        if constraint_frame is not None
        else "default-constraint-frame",
    )


def _action_for_component(component: str) -> str:
    return {
        "G": "build-edge-witnesses",
        "DE": "increase-execution-available-path-density",
        "AC": "seed-autocatalytic-closure",
        "VT": "run-verifier-queue",
        "LX": "bridge-liquidity",
        "SD": "reduce-downstream-search-cost",
        "CV": "repair-constraint-viability",
        "FR": "quarantine-false-liquidity",
        "BR": "ingest-target-basin-packets",
        "QS": "restore-sqot-diagnostic-reserve",
        "HZ": "reduce-hazard-authority-load",
    }.get(component, "inspect-proxy-component")


def registry_to_json(registry: CapabilityPacketRegistry) -> dict[str, object]:
    """Return sorted registry JSON for deterministic CLI output."""

    return cast(dict[str, object], json.loads(registry.model_dump_json()))
