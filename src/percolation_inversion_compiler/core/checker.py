"""Structured checker and audit records for finite theory projections."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.coverage import (
    ExternalObligationCatalog,
    TheoryCoverageRecord,
    TheoryImplementationRecord,
    TheoryItem,
)
from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import (
    CheckResult,
    ClaimRecord,
    ExternalProofObligation,
    Registry,
)
from percolation_inversion_compiler.core.status import ClaimStatus, StatusRule


class CheckerContext(BaseModel):
    """Finite context visible to a checker.

    The context is intentionally JSON-first: obligations, domains, residuals, and
    metadata are explicit finite records rather than Python callbacks.
    """

    context_id: str = "default"
    present_obligations: set[str] = Field(default_factory=set)
    expired_obligations: set[str] = Field(default_factory=set)
    external_obligations: list[ExternalProofObligation] = Field(default_factory=list)
    validity_domain: str | None = None
    residual_ledger: Ledger = Field(default_factory=Ledger)
    metadata: dict[str, object] = Field(default_factory=dict)

    def unresolved_external_ids(self) -> set[str]:
        return {
            obligation.obligation_id
            for obligation in self.external_obligations
            if obligation.obligation_id not in self.present_obligations
        }


class ObligationRule(BaseModel):
    """A portable finite obligation rule used to derive checker status."""

    rule_id: str
    required_for_settled: set[str] = Field(default_factory=set)
    required_for_provisional: set[str] = Field(default_factory=set)
    required_for_speculative: set[str] = Field(default_factory=set)
    hard_domain_obligations: set[str] = Field(default_factory=set)
    external_obligation_ids: set[str] = Field(default_factory=set)

    def as_status_rule(self) -> StatusRule:
        return StatusRule(
            required_for_settled=self.required_for_settled,
            required_for_provisional=self.required_for_provisional,
            required_for_speculative=self.required_for_speculative,
            hard_domain_obligations=self.hard_domain_obligations,
        )

    def decide(self, context: CheckerContext) -> CheckResult:
        rule = self.as_status_rule()
        decision = rule.decide(context.present_obligations, context.expired_obligations)
        unresolved = sorted(
            (self.external_obligation_ids | context.unresolved_external_ids())
            - context.present_obligations
        )
        status = decision.status
        accepted = decision.accepted
        reasons = list(decision.reasons)
        missing = sorted(set(decision.missing_obligations) | set(unresolved))
        if status == ClaimStatus.SETTLED and unresolved:
            status = ClaimStatus.PROVISIONAL
            accepted = True
            reasons.append("external proof obligations remain unresolved; no settled promotion")
        settled = status == ClaimStatus.SETTLED and not missing
        return CheckResult(
            accepted=accepted,
            status=status,
            finite_checks_passed=decision.accepted,
            operationally_usable=settled,
            settled=settled,
            reasons=reasons,
            missing_obligations=missing,
            residual_ledger=context.residual_ledger,
        )


class ObligationTrace(BaseModel):
    """One evaluated obligation node in a certificate dependency graph."""

    obligation_id: str
    accepted: bool
    status: ClaimStatus
    predecessors: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    missing_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)


class ProjectionAudit(BaseModel):
    """Registry-vs-extractor projection audit."""

    accepted: bool
    strict: bool = False
    registry_artifact: str | None = None
    extractor_artifact: str | None = None
    checked_claims: int = 0
    missing_in_extractor: list[str] = Field(default_factory=list)
    mismatches: list[dict[str, object]] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)

    def to_check_result(self) -> CheckResult:
        return CheckResult(
            accepted=self.accepted,
            status=ClaimStatus.SETTLED if self.accepted else ClaimStatus.DIAGNOSTIC,
            reasons=self.reasons,
            missing_obligations=self.missing_in_extractor,
        )


class TheoryAuditReport(BaseModel):
    """Machine-readable audit summary for one TeX source artifact."""

    source: str
    artifact: str
    canonical_key: str | None = None
    canonical: dict[str, object] | None = None
    coverage: TheoryCoverageRecord
    projection_audits: list[ProjectionAudit] = Field(default_factory=list)
    bit_mr_counts: dict[str, int] = Field(default_factory=dict)
    coverage_delta: dict[str, int] = Field(default_factory=dict)
    snapshot_delta: dict[str, object] = Field(default_factory=dict)
    unimplemented_by_section: dict[str, list[TheoryItem]] = Field(default_factory=dict)
    external_obligation_catalog: ExternalObligationCatalog | None = None
    external_obligation_category_summary: dict[str, int] = Field(default_factory=dict)
    external_verifier_route_summary: dict[str, int] = Field(default_factory=dict)
    external_catalog_errors: list[str] = Field(default_factory=list)
    finite_constructive_targets: list[TheoryImplementationRecord] = Field(default_factory=list)
    implemented_with_obligations: list[TheoryImplementationRecord] = Field(default_factory=list)
    unsupported_items: list[TheoryItem] = Field(default_factory=list)
    external_obligation_items: list[TheoryItem] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        canonical_ok = True
        if self.canonical is not None:
            canonical_ok = bool(self.canonical.get("matches"))
        return (
            canonical_ok
            and not self.external_catalog_errors
            and all(audit.accepted for audit in self.projection_audits)
        )


class TheoryAuditSuiteReport(BaseModel):
    """Canonical multi-theory audit report for reproducible release checks."""

    report_id: str = "pic-theory-audit-suite"
    canonical_dir: str
    expected_artifacts: list[str] = Field(default_factory=list)
    audits: dict[str, TheoryAuditReport] = Field(default_factory=dict)
    canonical_results: dict[str, dict[str, object]] = Field(default_factory=dict)
    strict_grammar: dict[str, dict[str, object]] = Field(default_factory=dict)
    snapshot_delta: dict[str, dict[str, object]] = Field(default_factory=dict)
    coverage_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    external_obligation_category_summary: dict[str, dict[str, int]] = Field(default_factory=dict)
    unsupported_total: int = 0
    partial_total: int = 0
    coverage_counts_match: bool = False
    external_category_summary_match: bool = False
    accepted: bool = False
    overall_status: str = "fail"
    reasons: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "canonical suite audits compare local TeX only by declared canonical filenames",
            "snapshot agreement is reproducibility metadata, not new mathematical evidence",
            "unresolved external obligations remain residual obligations after suite acceptance",
        ]
    )


class TheoryFidelityReport(BaseModel):
    """Canonical-suite-derived theory-fidelity summary for v0.4.4 hardening."""

    report_id: str = "pic-theory-fidelity"
    canonical_dir: str = ""
    suite_status: str = "fail"
    theory_summaries: dict[str, dict[str, object]] = Field(default_factory=dict)
    unsupported_total: int = 0
    partial_total: int = 0
    external_obligation_totals: dict[str, int] = Field(default_factory=dict)
    finite_upgrade_candidates: dict[str, list[str]] = Field(default_factory=dict)
    strict_grammar_accepted: dict[str, bool] = Field(default_factory=dict)
    snapshot_health: dict[str, bool] = Field(default_factory=dict)
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "theory-fidelity output is derived from finite canonical-suite audits",
            "external obligations remain explicit residual work",
            "finite upgrade candidates are implementation targets, not proof of real ASI",
        ]
    )


class CanonicalTheorySnapshotSummary(BaseModel):
    """Portable summary for one bundled canonical-theory snapshot."""

    artifact_key: str
    artifact: str
    doi: str | None = None
    source_tex_sha256: str | None = None
    definitions: int = 0
    claims: int = 0
    mr_records: int = 0
    coverage_counts: dict[str, int] = Field(default_factory=dict)
    external_obligation_category_summary: dict[str, int] = Field(default_factory=dict)
    implemented_total: int = 0
    external_obligation_total: int = 0
    unsupported_total: int = 0
    partial_total: int = 0
    finite_upgrade_candidate_count: int = 0
    portability_status: str = "schema-first"


class CanonicalImplementationReadinessReport(BaseModel):
    """Pip-safe canonical readiness report derived from bundled snapshots."""

    report_id: str = "pic-canonical-implementation-readiness"
    profile: str = "development"
    source: str = "bundled-derived-snapshots"
    snapshot_count: int = 0
    expected_theory_keys: list[str] = Field(
        default_factory=lambda: ["ecpt", "bit", "trc", "sqot", "alt"]
    )
    theory_summaries: dict[str, CanonicalTheorySnapshotSummary] = Field(default_factory=dict)
    total_implemented_items: int = 0
    total_external_obligations: int = 0
    unsupported_total: int = 0
    partial_total: int = 0
    finite_upgrade_candidates: dict[str, list[str]] = Field(default_factory=dict)
    residual_category_totals: dict[str, int] = Field(default_factory=dict)
    pip_installable: bool = True
    source_checkout_required: bool = False
    canonical_tex_required_for_this_report: bool = False
    source_tex_vendored: bool = False
    portable_schema_first_contract: bool = True
    cross_language_portability_ready: bool = True
    compact_mode_available: bool = True
    adoption_required_for_core: bool = False
    approval_gate_present: bool = False
    safe_commands_executable_by_pic: bool = False
    automatic_execution_present: bool = False
    settled: bool = False
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    asi_proxy_acceleration_objective: str = (
        "protocol-relative ASI-proxy acceleration through packet percolation, "
        "verifier throughput, residual preservation, SQOT queue visibility, and ALT "
        "abstraction-liquidity reuse"
    )
    acceleration_levers: list[str] = Field(
        default_factory=lambda: [
            "machine-readable packet candidate handling",
            "finite verifier route and residual exposure",
            "SQOT queue diagnostics without queue mutation",
            "BIT bottleneck visibility for finite upgrade candidates",
            "ALT abstraction-liquidity and translation-friction visibility",
            "argv-safe commands for OS-independent agent orchestration",
        ]
    )
    portability_invariants: list[str] = Field(
        default_factory=lambda: [
            "JSON schema names and field names remain English and stable",
            "localized Markdown is display text only and is not parser input",
            "ports must preserve accepted, workflow_usable, and settled as distinct booleans",
            "safe_commands and recommended invocations are inert data",
        ]
    )
    recommended_invocations: list[dict[str, object]] = Field(default_factory=list)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "bundled snapshots are derived metadata and do not vendor TeX/PDF sources",
            "canonical readiness does not prove real ASI, physical truth, simulator truth, "
            "or oracle truth",
            "external obligations remain explicit residual work",
            "accepted readiness does not imply settled=true",
            "PIC does not execute recommended invocations or safe_commands",
        ]
    )
    reasons: list[str] = Field(default_factory=list)


@runtime_checkable
class CheckerProtocol(Protocol):
    """Protocol implemented by structured finite checkers."""

    def check(self, context: CheckerContext) -> CheckResult:
        """Run a finite check in the supplied checker context."""


def boolean_check_result(
    *,
    accepted: bool,
    obligation_id: str,
    success_status: ClaimStatus = ClaimStatus.SETTLED,
    failure_status: ClaimStatus = ClaimStatus.DIAGNOSTIC,
    failure_reason: str = "finite checker rejected the obligation",
    residual_ledger: Ledger | None = None,
) -> CheckResult:
    """Convert a finite boolean predicate into a structured checker result."""

    if accepted:
        return CheckResult(
            accepted=True,
            status=success_status,
            residual_ledger=residual_ledger or Ledger(),
        )
    return CheckResult(
        accepted=False,
        status=failure_status,
        reasons=[failure_reason],
        missing_obligations=[obligation_id],
        residual_ledger=residual_ledger or Ledger(),
    )


def _sorted_strings(values: Iterable[str]) -> list[str]:
    return sorted({str(value) for value in values})


def _domain_projection(claim: ClaimRecord) -> object:
    return None if claim.domain is None else claim.domain.model_dump(mode="json")


def audit_registry_projection(
    extractor_claims: dict[str, ClaimRecord],
    registry: Registry,
    *,
    strict: bool = False,
    extractor_artifact: str | None = None,
) -> ProjectionAudit:
    """Check that a registry is a projection of finite extractor claims.

    Strict mode compares stable projected fields. It does not treat a registry's
    declared status as checker-derived evidence; only explicit ``derived_status``
    fields are compared.
    """

    missing: list[str] = []
    mismatches: list[dict[str, object]] = []
    for claim in registry.claims:
        projected = extractor_claims.get(claim.claim_id)
        if projected is None:
            missing.append(claim.claim_id)
            continue
        if not strict:
            continue
        comparisons: dict[str, tuple[object, object]] = {
            "kind": (projected.kind, claim.kind),
            "label": (projected.label, claim.label),
            "dependency_labels": (
                _sorted_strings(projected.dependency_labels),
                _sorted_strings(claim.dependency_labels),
            ),
            "citation_keys": (
                _sorted_strings(projected.citation_keys),
                _sorted_strings(claim.citation_keys),
            ),
            "ledger_coordinates": (
                _sorted_strings(projected.ledger_coordinates),
                _sorted_strings(claim.ledger_coordinates),
            ),
            "domain": (_domain_projection(projected), _domain_projection(claim)),
        }
        if claim.derived_status is not None:
            comparisons["derived_status"] = (projected.derived_status, claim.derived_status)
        for field, (expected, observed) in comparisons.items():
            if expected != observed:
                mismatches.append(
                    {
                        "claim_id": claim.claim_id,
                        "field": field,
                        "expected": expected,
                        "observed": observed,
                    }
                )
    reasons: list[str] = []
    if missing:
        reasons.append("registry contains claims absent from extractor judgments")
    if mismatches:
        reasons.append("registry fields differ from extractor projection")
    return ProjectionAudit(
        accepted=not missing and not mismatches,
        strict=strict,
        registry_artifact=registry.artifact,
        extractor_artifact=extractor_artifact,
        checked_claims=len(registry.claims),
        missing_in_extractor=sorted(missing),
        mismatches=mismatches,
        reasons=reasons,
    )


def evaluate_dependency_obligations(
    dag: DependencyDAG,
    context: CheckerContext,
) -> list[ObligationTrace]:
    """Evaluate a finite dependency graph against accepted obligations."""

    predecessors = dag.predecessors()
    traces: list[ObligationTrace] = []
    accepted_nodes: set[str] = set()
    for node in dag.topological_order():
        preds = sorted(predecessors.get(node, set()))
        missing_pred = [pred for pred in preds if pred not in accepted_nodes]
        if node in context.expired_obligations:
            traces.append(
                ObligationTrace(
                    obligation_id=node,
                    accepted=False,
                    status=ClaimStatus.EXPIRED,
                    predecessors=preds,
                    reasons=["obligation expired"],
                    missing_obligations=[node],
                    residual_ledger=context.residual_ledger,
                )
            )
            continue
        unresolved_external = node in context.unresolved_external_ids()
        if missing_pred or unresolved_external or node not in context.present_obligations:
            reasons: list[str] = []
            missing = list(missing_pred)
            if unresolved_external:
                reasons.append("external proof obligation unresolved")
                missing.append(node)
            if node not in context.present_obligations:
                reasons.append("obligation absent")
                missing.append(node)
            traces.append(
                ObligationTrace(
                    obligation_id=node,
                    accepted=False,
                    status=ClaimStatus.DIAGNOSTIC,
                    predecessors=preds,
                    reasons=reasons or ["predecessor obligation missing"],
                    missing_obligations=sorted(set(missing)),
                    residual_ledger=context.residual_ledger,
                )
            )
            continue
        accepted_nodes.add(node)
        traces.append(
            ObligationTrace(
                obligation_id=node,
                accepted=True,
                status=ClaimStatus.SETTLED,
                predecessors=preds,
                residual_ledger=context.residual_ledger,
            )
        )
    return traces


def residual_from_reasons(prefix: str, reasons: Iterable[str]) -> Ledger:
    """Create a deterministic residual ledger from rejected finite clauses."""

    ledger = Ledger()
    for index, reason in enumerate(sorted(set(reasons)), start=1):
        ledger = ledger.add_coordinate(
            f"{prefix}:{index}:{reason}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return ledger
