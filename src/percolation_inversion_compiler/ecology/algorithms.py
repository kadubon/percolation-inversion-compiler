"""Capability packet ecology algorithms for ECPT active runtimes."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.ecology.records import (
    BottleneckIntervention,
    BottleneckInversionPlan,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    ClosedLoopAgentIteration,
    EdgeWitness,
    PacketIngestionReport,
    PacketSourceKind,
    PsiDashboard,
    VerificationThroughputReport,
)

_PSI_COMPONENTS = ("G", "DE", "AC", "VT", "LX", "SD", "CV", "FR", "BR")


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
    components = {
        "G": len(reachable) / total,
        "DE": min(1.0, len(accepted_edges) / max(1, total)),
        "AC": _cycle_proxy(accepted_edges),
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
        "BR": 0.0 if not tag_targets else target_hits / total,
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
        residual_ledger=registry.residual_ledger,
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
    }.get(component, "inspect-proxy-component")


def registry_to_json(registry: CapabilityPacketRegistry) -> dict[str, object]:
    """Return sorted registry JSON for deterministic CLI output."""

    return cast(dict[str, object], json.loads(registry.model_dump_json()))
