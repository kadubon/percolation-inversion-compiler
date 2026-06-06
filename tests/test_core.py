from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from percolation_inversion_compiler.core.algebra import (
    AlgebraLawCertificate,
    DomainTypedSemiring,
    FunctorLawCertificate,
)
from percolation_inversion_compiler.core.checker import (
    CheckerContext,
    ObligationRule,
    audit_registry_projection,
)
from percolation_inversion_compiler.core.frontier import FrontierRecord, dominates, pareto_frontier
from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.judgment import (
    CertificateDAG,
    Judgment,
    ObligationSet,
    check_external_verifier_hook,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.order import FiniteOrder, MonotoneMap
from percolation_inversion_compiler.core.records import (
    ClaimRecord,
    ExternalProofObligation,
    ExternalVerifierHook,
    Registry,
)
from percolation_inversion_compiler.core.status import ClaimStatus, StatusRule


def test_status_rule_prevents_settled_promotion() -> None:
    rule = StatusRule(
        hard_domain_obligations={"domain"},
        required_for_settled={"domain", "verify", "settle"},
        required_for_provisional={"domain", "verify"},
        required_for_speculative={"domain"},
    )
    decision = rule.decide({"domain", "verify"})
    assert decision.accepted
    assert decision.status == ClaimStatus.PROVISIONAL
    assert "settle" in decision.missing_obligations


def test_status_rule_rejects_missing_hard_domain() -> None:
    rule = StatusRule(hard_domain_obligations={"domain"})
    decision = rule.decide(set())
    assert not decision.accepted
    assert decision.status == ClaimStatus.REJECTED


def test_ledger_dominance_uses_benefit_and_burden_direction() -> None:
    left = Ledger()
    left = left.add_coordinate("benefit", 2.0, kind=CoordinateKind.BENEFIT)
    left = left.add_coordinate("burden", 1.0, kind=CoordinateKind.BURDEN)
    right = Ledger()
    right = right.add_coordinate("benefit", 1.5, kind=CoordinateKind.BENEFIT)
    right = right.add_coordinate("burden", 1.2, kind=CoordinateKind.BURDEN)
    assert left.dominates(right)
    assert not right.dominates(left)


def test_dependency_dag_reachable_and_topological() -> None:
    dag = DependencyDAG.from_dependencies({"claim": {"witness", "unit"}, "witness": {"base"}})
    assert "claim" in dag.reachable_from("base")
    assert dag.topological_order()[0] == "base"


def test_pareto_frontier_removes_dominated_records() -> None:
    records = [
        FrontierRecord(
            record_id="a",
            benefits={"x": 2.0},
            burdens={"cost": 1.0},
            status=ClaimStatus.SETTLED,
        ),
        FrontierRecord(
            record_id="b",
            benefits={"x": 1.0},
            burdens={"cost": 2.0},
            status=ClaimStatus.PROVISIONAL,
        ),
    ]
    assert [record.record_id for record in pareto_frontier(records)] == ["a"]


def test_finite_order_antichain_and_monotone_map() -> None:
    order = FiniteOrder(elements=["bottom", "left", "right"], leq_pairs=[("bottom", "left")])
    assert order.check().accepted
    assert order.leq("bottom", "left")
    assert order.incomparable("left", "right")
    assert order.dominance_witness("left", "bottom").accepted
    antichain = order.maximal_antichain()
    assert len(antichain) == 2
    assert all(
        order.incomparable(left, right)
        for left in antichain
        for right in antichain
        if left != right
    )

    target = FiniteOrder(elements=["low", "high"], leq_pairs=[("low", "high")])
    monotone = MonotoneMap(
        source=order,
        target=target,
        mapping={"bottom": "low", "left": "high", "right": "high"},
    )
    assert monotone.check().accepted
    non_monotone = monotone.model_copy(update={"mapping": {"bottom": "high", "left": "low"}})
    assert not non_monotone.check().accepted


def test_semiring_and_functor_laws() -> None:
    boolean_semiring = DomainTypedSemiring(
        domain_id="bool",
        elements=["0", "1"],
        zero="0",
        one="1",
        plus_table={"0|0": "0", "0|1": "1", "1|0": "1", "1|1": "1"},
        times_table={"0|0": "0", "0|1": "0", "1|0": "0", "1|1": "1"},
    )
    assert AlgebraLawCertificate(semiring=boolean_semiring).check().accepted
    assert (
        FunctorLawCertificate(
            source=boolean_semiring,
            target=boolean_semiring,
            mapping={"0": "0", "1": "1"},
        )
        .check()
        .accepted
    )
    assert (
        not FunctorLawCertificate(
            source=boolean_semiring,
            target=boolean_semiring,
            mapping={"0": "1", "1": "0"},
        )
        .check()
        .accepted
    )


def test_declared_status_does_not_promote_derived_status() -> None:
    claim = ClaimRecord.from_raw(
        {"claim_id": "c", "kind": "theorem", "label": "C", "status": "settled"}
    )
    assert claim.declared_status == ClaimStatus.SETTLED
    assert claim.derived_status is None
    rule = StatusRule(
        required_for_settled={"verify", "settle"},
        required_for_provisional={"verify"},
        required_for_speculative=set(),
    )
    obligations = ObligationSet(present=set())
    assert obligations.derive_status(rule) == ClaimStatus.SPECULATIVE


def test_empty_settled_rule_does_not_promote_to_settled() -> None:
    decision = StatusRule().decide(set())
    assert decision.status != ClaimStatus.SETTLED
    assert "settled-rule:nonempty-obligations" in decision.missing_obligations


def test_obligation_rule_external_blocks_settled_promotion() -> None:
    rule = ObligationRule(
        rule_id="r",
        required_for_settled={"finite", "external"},
        required_for_provisional={"finite"},
        external_obligation_ids={"external"},
    )
    result = rule.decide(CheckerContext(present_obligations={"finite"}))
    assert result.accepted
    assert result.finite_checks_passed
    assert not result.operationally_usable
    assert not result.settled
    assert result.status == ClaimStatus.PROVISIONAL
    assert "external" in result.missing_obligations


def test_external_verifier_hook_preserves_unresolved_obligations() -> None:
    obligation = ExternalProofObligation(
        obligation_id="hybrid-envelope",
        description="hybrid system envelope requires a domain verifier",
        obligation_category="physical-hybrid-system",
        failure_mode="hybrid-witness-missing",
        failure_modes=["hybrid-envelope-not-certified"],
        accepted_evidence_kind=["instrumented-trace"],
        residual_policy="charge-physical-residual-until-verifier-accepts",
        safe_default="diagnostic-with-physical-obligation",
        residual_charge=Ledger().add_coordinate(
            "hybrid:residual",
            0.25,
            kind=CoordinateKind.RESIDUAL,
        ),
    )
    unresolved = ExternalVerifierHook(
        hook_id="hook",
        verifier_route="adapter.verify_hybrid_envelope",
        obligation_ids={"hybrid-envelope"},
        obligation_categories={"hybrid-envelope": "physical-hybrid-system"},
        accepted_evidence_kind=["instrumented-trace"],
        residual_policy="charge-physical-residual-until-verifier-accepts",
        safe_default="return-diagnostic-with-unresolved-obligations",
        residual_coordinates={"adapter-gap": 0.1},
    )
    unresolved_result = check_external_verifier_hook(unresolved, [obligation])
    assert not unresolved_result.accepted
    assert unresolved_result.status == ClaimStatus.DIAGNOSTIC
    assert "hybrid-envelope" in unresolved_result.missing_obligations
    assert unresolved_result.residual_ledger.burden_sum() >= 0.35

    legacy_resolved = unresolved.model_copy(update={"accepted_obligation_ids": {"hybrid-envelope"}})
    legacy_result = check_external_verifier_hook(legacy_resolved, [obligation])
    assert not legacy_result.accepted
    assert "accepted external verifier hook requires resolution provenance" in (
        legacy_result.reasons
    )

    provenance_bound = legacy_resolved.model_copy(
        update={
            "resolution_id": "resolution:abc",
            "resolution_digest": "a" * 64,
            "evidence_envelope_id": "envelope:abc",
            "evidence_artifact_ids": {"artifact:abc"},
            "provenance_policy": "evidence-policy:production",
        }
    )
    resolved_result = check_external_verifier_hook(provenance_bound, [obligation])
    assert resolved_result.accepted
    assert resolved_result.status == ClaimStatus.SETTLED


def test_external_verifier_hook_rejects_unknown_category_reference() -> None:
    obligation = ExternalProofObligation(
        obligation_id="latent",
        description="latent witness",
        obligation_category="latent-oracle-model",
    )
    hook = ExternalVerifierHook(
        hook_id="hook",
        verifier_route="adapter.verify_latent",
        obligation_ids={"latent"},
        obligation_categories={"other": "latent-oracle-model"},
    )
    result = check_external_verifier_hook(hook, [obligation])
    assert not result.accepted
    assert "external verifier categories reference unknown obligations" in result.reasons


def test_certificate_dag_evaluates_missing_predecessor() -> None:
    dag = CertificateDAG(nodes={"base", "claim"})
    dag.add_dependency("base", "claim")
    traces = dag.evaluate(CheckerContext(present_obligations={"claim"}))
    claim_trace = next(trace for trace in traces if trace.obligation_id == "claim")
    assert not claim_trace.accepted
    assert "base" in claim_trace.missing_obligations


def test_strict_projection_detects_field_mismatch() -> None:
    judgment = Judgment(
        claim_id="c",
        claim_label="C",
        kind="theorem",
        derived_status=ClaimStatus.PROVISIONAL,
        dependencies=["d"],
    )
    registry = Registry(
        claims=[
            ClaimRecord(
                claim_id="c",
                kind="theorem",
                label="Different",
                dependency_labels=["d"],
            )
        ]
    )
    audit = audit_registry_projection(
        {"c": judgment.to_claim_record()},
        registry,
        strict=True,
    )
    assert not audit.accepted
    assert audit.mismatches[0]["field"] == "label"


@given(st.floats(min_value=0.0, max_value=100.0), st.floats(min_value=0.0, max_value=100.0))
def test_ledger_burden_dominance_property(left_burden: float, right_burden: float) -> None:
    left = Ledger().add_coordinate("cost", left_burden, kind=CoordinateKind.BURDEN)
    right = Ledger().add_coordinate("cost", right_burden, kind=CoordinateKind.BURDEN)
    assert left.dominates(right) == (left_burden <= right_burden)


def test_missing_ledger_coordinate_is_not_zero_by_default() -> None:
    left = Ledger()
    right = Ledger().add_coordinate("unknown-cost", 0.0, kind=CoordinateKind.BURDEN)
    assert not left.dominates(right)
    assert left.dominates(right, missing_as_zero=True)


def test_empty_frontier_records_are_incomparable() -> None:
    left = FrontierRecord(record_id="left", stratum="main")
    right = FrontierRecord(record_id="right", stratum="main")
    assert not dominates(left, right)
