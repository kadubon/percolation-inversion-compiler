"""Deterministic BIT bottleneck inversion diagnostics."""

from __future__ import annotations

from collections import Counter

from percolation_inversion_compiler.bit_engine.records import (
    ActivationGainEstimate,
    BottleneckClassDiagnosis,
    BottleneckInversionCandidate,
    BottleneckInversionReport,
    CapabilityExpressionPath,
    InversionCertificate,
    MinimalEnablingCondition,
    PostInversionAuditPlan,
    RollbackOrDeactivationPlan,
)
from percolation_inversion_compiler.phase_lab.records import (
    EffectivePacketGraph,
    PhaseWindowObservation,
)

BLOCKER_CLASS_MAP = {
    "candidate-only": "missing evidence",
    "raw-external-volume": "external-domain obligation",
    "verification-blocked": "missing verifier route",
    "missing-edge-evidence": "missing semantic edge",
    "authority-invalid": "missing authority",
    "rollback-missing": "missing rollback support",
    "salience-obstruction": "salience obstruction",
    "stale": "stale packet",
    "hash-invalid": "missing evidence",
    "validity-domain-missing": "external-domain obligation",
}


def diagnose_bottlenecks(graph: EffectivePacketGraph) -> BottleneckInversionReport:
    """Diagnose bottlenecks in an effective graph without mutating anything."""

    bottlenecks: list[BottleneckClassDiagnosis] = []
    paths: list[CapabilityExpressionPath] = []
    for node in graph.nodes:
        blockers = list(node.eligibility.blockers)
        if not blockers and not node.contribution.positive_contribution:
            blockers.append("missing evidence")
        for blocker in blockers:
            bottleneck_class = _class_for_blocker(blocker)
            bottleneck_id = f"bit-bottleneck:{node.node_id}:{_slug(bottleneck_class)}"
            mecs = _mecs_for_class(bottleneck_id, bottleneck_class)
            bottlenecks.append(
                BottleneckClassDiagnosis(
                    bottleneck_id=bottleneck_id,
                    bottleneck_class=bottleneck_class,
                    object_id=node.node_id,
                    severity=1.0,
                    blockers=[blocker],
                    minimal_enabling_conditions=mecs,
                    accepted=False,
                    settled=False,
                    reasons=[
                        "bottleneck diagnosis is recommendation-only",
                        "residual obligations remain visible",
                    ],
                )
            )
    for edge in graph.edges:
        path_id = f"capability-path:{edge.edge_id}"
        blocked_by = [] if edge.contribution.positive_contribution else ["missing semantic edge"]
        paths.append(
            CapabilityExpressionPath(
                path_id=path_id,
                packet_ids=sorted(set([*edge.source_node_ids, edge.target_node_id])),
                edge_ids=[edge.edge_id],
                blocked_by=blocked_by,
                execution_available=False,
                settled=False,
            )
        )
        if not edge.evidence.evidence_supported:
            bottleneck_class = "missing semantic edge"
            bottleneck_id = f"bit-bottleneck:{edge.edge_id}:{_slug(bottleneck_class)}"
            bottlenecks.append(
                BottleneckClassDiagnosis(
                    bottleneck_id=bottleneck_id,
                    bottleneck_class=bottleneck_class,
                    object_id=edge.edge_id,
                    severity=1.0,
                    blockers=["missing-edge-evidence"],
                    minimal_enabling_conditions=_mecs_for_class(bottleneck_id, bottleneck_class),
                    reasons=["edge lacks finite evidence support"],
                )
            )
    return BottleneckInversionReport(
        graph_id=graph.graph_id,
        capability_expression_paths=paths,
        bottlenecks=_dedupe_bottlenecks(bottlenecks),
        accepted=bool(bottlenecks),
        workflow_usable=True,
        settled=False,
        reasons=[
            "BIT diagnostics do not grant execution authority",
            "activation gain is protocol-relative only",
        ],
    )


def invert_bottlenecks(report: BottleneckInversionReport) -> BottleneckInversionReport:
    """Build recommendation-only inversion candidates for diagnosed bottlenecks."""

    candidates = [
        _candidate_for_bottleneck(bottleneck)
        for bottleneck in report.bottlenecks
    ]
    return report.model_copy(
        update={
            "inversion_candidates": candidates,
            "accepted": bool(candidates),
            "settled": False,
            "reasons": sorted(
                {
                    *report.reasons,
                    "inversion candidates are recommendations, not execution authority",
                }
            ),
        }
    )


def minimal_enabling_conditions_for_bottleneck(
    bottleneck_id: str,
    report: BottleneckInversionReport | None = None,
) -> list[MinimalEnablingCondition]:
    """Return MECs for a bottleneck id, using a report when supplied."""

    if report is not None:
        for bottleneck in report.bottlenecks:
            if bottleneck.bottleneck_id == bottleneck_id:
                return bottleneck.minimal_enabling_conditions
    return _mecs_for_class(bottleneck_id, "missing evidence")


def build_inversion_certificate(candidate: BottleneckInversionCandidate) -> InversionCertificate:
    """Build a fail-closed certificate candidate for one inversion candidate."""

    finite_requirements_passed = all(
        condition.required_evidence for condition in candidate.minimal_enabling_conditions
    )
    status = "candidate" if finite_requirements_passed else "abstain"
    return InversionCertificate(
        certificate_id=f"inversion-certificate:{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        certificate_status=status,
        finite_requirements_passed=finite_requirements_passed,
        residual_preserved=True,
        grants_execution_authority=False,
        settled=False,
        reasons=[
            "certificate remains protocol-relative",
            "candidate does not mutate repositories, shells, networks, or models",
            *(
                []
                if finite_requirements_passed
                else ["finite evidence references are required before certification"]
            ),
        ],
    )


def compare_observation_baseline(
    baseline: PhaseWindowObservation,
    candidate: PhaseWindowObservation,
) -> BottleneckInversionReport:
    """Compare two phase observations for protocol-relative activation gain."""

    delta = {
        "accepted_packet_count": float(
            candidate.accepted_packet_count - baseline.accepted_packet_count
        ),
        "effective_edge_count": float(
            candidate.effective_edge_count - baseline.effective_edge_count
        ),
        "execution_available_path_count": float(
            candidate.execution_available_path_count - baseline.execution_available_path_count
        ),
        "closure_witness_count": float(
            candidate.closure_witness_count - baseline.closure_witness_count
        ),
        "residual_debt": float(candidate.residual_debt - baseline.residual_debt),
    }
    return BottleneckInversionReport(
        report_id="bit-baseline-comparison",
        baseline_comparison=delta,
        accepted=True,
        workflow_usable=True,
        settled=False,
        reasons=["baseline comparison is diagnostic and protocol-relative"],
    )


def _candidate_for_bottleneck(
    bottleneck: BottleneckClassDiagnosis,
) -> BottleneckInversionCandidate:
    gain = _gain_for_class(bottleneck.bottleneck_class)
    candidate_id = f"inversion-candidate:{bottleneck.bottleneck_id}"
    return BottleneckInversionCandidate(
        candidate_id=candidate_id,
        bottleneck_id=bottleneck.bottleneck_id,
        bottleneck_class=bottleneck.bottleneck_class,
        minimal_enabling_conditions=bottleneck.minimal_enabling_conditions,
        expected_activation_gain=ActivationGainEstimate(
            estimate_id=f"activation-gain:{bottleneck.bottleneck_id}",
            lower_bound=gain,
            upper_bound=min(1.0, gain + 0.2),
            assumptions=[
                "all listed minimal enabling conditions are met",
                "no new residual or salience obstruction is introduced",
            ],
        ),
        verification_cost=max(0.1, bottleneck.severity),
        rollback_or_deactivation_plan=RollbackOrDeactivationPlan(
            plan_id=f"rollback:{candidate_id}",
            rollback_required=True,
            rollback_refs_required=["rollback-or-safe-abort-evidence"],
            deactivation_steps=["revert candidate contribution to diagnostic-only status"],
            automatic_rollback=False,
        ),
        post_inversion_audit_plan=PostInversionAuditPlan(
            plan_id=f"audit:{candidate_id}",
            required_checks=[
                "rerun effective graph build",
                "rerun threshold status",
                "inspect residual ledger",
            ],
            evidence_to_record=["verifier route result", "edge evidence", "rollback evidence"],
        ),
        risk_hazard_authority_notes=[
            "explicit scope-bounded authority remains required",
            "candidate is not execution authority",
        ],
        accepted=False,
        settled=False,
        reasons=["candidate remains not settled until finite checker rules pass"],
    )


def _mecs_for_class(bottleneck_id: str, bottleneck_class: str) -> list[MinimalEnablingCondition]:
    templates = {
        "missing evidence": ("evidence", ["content-addressed-evidence-ref"], ["route:evidence"]),
        "missing verifier route": ("verifier-route", ["verifier-resolution"], ["route:verifier"]),
        "missing semantic edge": ("semantic-edge", ["edge-evidence-ref"], ["route:edge"]),
        "missing rollback support": ("rollback", ["rollback-ref"], ["route:rollback"]),
        "missing authority": ("authority", ["authority-envelope-ref"], ["route:authority"]),
        "missing receiver context": (
            "receiver-context",
            ["receiver-context-ref"],
            ["route:receiver"],
        ),
        "identity/Sybil blocker": ("identity", ["identity-context-ref"], ["route:identity"]),
        "stale packet": ("freshness", ["freshness-refresh-ref"], ["route:freshness"]),
        "false-liquidity blocker": ("liquidity", ["liquidity-certificate-ref"], ["route:alt"]),
        "salience obstruction": ("salience", ["salience-rebalance-ref"], ["route:sqot"]),
        "queue occupation": ("queue", ["queue-reserve-ref"], ["route:sqot"]),
        "missing ALT lift": ("alt-lift", ["alt-ecpt-lift-ref"], ["route:alt-lift"]),
        "trace boundary mismatch": ("trace-boundary", ["typed-trace-ref"], ["route:trc"]),
        "external-domain obligation": (
            "external-obligation",
            ["external-obligation-resolution"],
            ["route:external"],
        ),
    }
    condition_type, evidence, routes = templates.get(
        bottleneck_class,
        ("evidence", ["content-addressed-evidence-ref"], ["route:evidence"]),
    )
    return [
        MinimalEnablingCondition(
            condition_id=f"mec:{bottleneck_id}:{condition_type}",
            bottleneck_id=bottleneck_id,
            condition_type=condition_type,
            required_evidence=evidence,
            verifier_routes=routes,
            settled=False,
        )
    ]


def _class_for_blocker(blocker: str) -> str:
    normalized = blocker.lower()
    if normalized in BLOCKER_CLASS_MAP:
        return BLOCKER_CLASS_MAP[normalized]
    for key, value in BLOCKER_CLASS_MAP.items():
        if key in normalized:
            return value
    return "missing evidence"


def _gain_for_class(bottleneck_class: str) -> float:
    priority = {
        "missing semantic edge": 0.4,
        "missing verifier route": 0.35,
        "missing evidence": 0.3,
        "missing ALT lift": 0.3,
        "salience obstruction": 0.25,
        "queue occupation": 0.2,
        "missing rollback support": 0.2,
        "missing authority": 0.15,
        "trace boundary mismatch": 0.15,
        "external-domain obligation": 0.1,
    }
    return priority.get(bottleneck_class, 0.1)


def _dedupe_bottlenecks(
    bottlenecks: list[BottleneckClassDiagnosis],
) -> list[BottleneckClassDiagnosis]:
    seen: set[str] = set()
    result: list[BottleneckClassDiagnosis] = []
    for item in bottlenecks:
        key = f"{item.object_id}:{item.bottleneck_class}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    counts = Counter(item.bottleneck_class for item in result)
    return [
        item.model_copy(update={"severity": float(counts[item.bottleneck_class])})
        for item in sorted(result, key=lambda value: (value.bottleneck_class, value.object_id))
    ]


def _slug(value: str) -> str:
    return value.lower().replace("/", "-").replace(" ", "-")
