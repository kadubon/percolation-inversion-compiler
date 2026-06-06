"""Extractor judgments, obligations, and agent connector records."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.checker import (
    CheckerContext,
    ObligationTrace,
    audit_registry_projection,
    evaluate_dependency_obligations,
)
from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.records import (
    CheckResult,
    ClaimRecord,
    ExternalProofObligation,
    ExternalVerifierHook,
    Registry,
    ValidityDomain,
)
from percolation_inversion_compiler.core.status import ClaimStatus, StatusRule


class ObligationSet(BaseModel):
    """Finite obligation state used to derive claim status."""

    present: set[str] = Field(default_factory=set)
    expired: set[str] = Field(default_factory=set)
    external: list[ExternalProofObligation] = Field(default_factory=list)

    def missing(self, required: Iterable[str]) -> set[str]:
        return set(required) - self.present

    def unresolved_external(self) -> list[ExternalProofObligation]:
        return [
            obligation
            for obligation in self.external
            if obligation.obligation_id not in self.present
        ]

    def derive_status(self, rule: StatusRule) -> ClaimStatus:
        decision = rule.decide(self.present, self.expired)
        if decision.status == ClaimStatus.SETTLED and self.unresolved_external():
            return ClaimStatus.PROVISIONAL
        return decision.status


class Judgment(BaseModel):
    """Finite typed extraction judgment.

    This is the implementation counterpart of TRC-style judgments
    ``Cert |- claim : status @ domain / residual``.
    """

    claim_id: str
    claim_label: str
    kind: str = "claim"
    derived_status: ClaimStatus
    domain: ValidityDomain | None = None
    dependencies: list[str] = Field(default_factory=list)
    ledger_coordinates: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    proof_obligations: list[ExternalProofObligation] = Field(default_factory=list)
    stratum: str | None = None

    def to_claim_record(self, *, artifact: str | None = None) -> ClaimRecord:
        return ClaimRecord(
            claim_id=self.claim_id,
            kind=self.kind,
            label=self.claim_label,
            derived_status=self.derived_status,
            dependency_labels=self.dependencies,
            ledger_coordinates=self.ledger_coordinates,
            citation_keys=self.citation_keys,
            artifact=artifact,
            domain=self.domain,
        )


class ExtractorOutput(BaseModel):
    """Claims emitted by a finite checker/extractor."""

    artifact: str | None = None
    judgments: list[Judgment] = Field(default_factory=list)

    def claim_ids(self) -> set[str]:
        return {judgment.claim_id for judgment in self.judgments}

    def claim_records(self) -> dict[str, ClaimRecord]:
        return {
            judgment.claim_id: judgment.to_claim_record(artifact=self.artifact)
            for judgment in self.judgments
        }

    def as_registry(self) -> Registry:
        return Registry(
            artifact=self.artifact,
            claims=[
                judgment.to_claim_record(artifact=self.artifact) for judgment in self.judgments
            ],
            metadata={"source": "extractor-output"},
        )

    def check_registry_projection(self, registry: Registry, *, strict: bool = False) -> CheckResult:
        audit = audit_registry_projection(
            self.claim_records(),
            registry,
            strict=strict,
            extractor_artifact=self.artifact,
        )
        result = audit.to_check_result()
        if result.accepted:
            return result.model_copy(
                update={
                    "claims": [
                        claim for claim in registry.claims if claim.claim_id in self.claim_ids()
                    ]
                }
            )
        return result


class CertificateDAG(BaseModel):
    """Portable certificate DAG summary for agent and language interop."""

    nodes: set[str] = Field(default_factory=set)
    dependency_edges: list[tuple[str, str]] = Field(default_factory=list)
    obligation_ids: set[str] = Field(default_factory=set)

    def add_dependency(self, dependency: str, dependent: str) -> None:
        self.nodes.update({dependency, dependent})
        self.dependency_edges.append((dependency, dependent))

    def dependency_dag(self) -> DependencyDAG:
        dag = DependencyDAG()
        for node in self.nodes | self.obligation_ids:
            dag.add_node(node)
        for dependency, dependent in self.dependency_edges:
            dag.add_edge(dependency, dependent)
        return dag

    def topological_order(self) -> list[str]:
        return self.dependency_dag().topological_order()

    def evaluate(self, context: CheckerContext) -> list[ObligationTrace]:
        return evaluate_dependency_obligations(self.dependency_dag(), context)


class ProofObligationVerifier(BaseModel):
    """Declarative verifier result for external proof obligations."""

    verifier_id: str
    accepted_obligations: set[str] = Field(default_factory=set)
    rejected_obligations: set[str] = Field(default_factory=set)
    notes: list[str] = Field(default_factory=list)

    def verify(self, obligation: ExternalProofObligation) -> bool:
        if obligation.obligation_id in self.rejected_obligations:
            return False
        return obligation.obligation_id in self.accepted_obligations


def check_external_verifier_hook(
    hook: ExternalVerifierHook,
    obligations: Iterable[ExternalProofObligation],
) -> CheckResult:
    """Check a domain-specific verifier hook without promoting unresolved claims."""

    known_obligations = {obligation.obligation_id: obligation for obligation in obligations}
    reasons: list[str] = []
    residual = Ledger()
    if not hook.verifier_route:
        reasons.append("external verifier route is empty")
    unknown = hook.obligation_ids - set(known_obligations)
    if unknown:
        reasons.append("external verifier references unknown obligations")
    unknown_categories = set(hook.obligation_categories) - hook.obligation_ids
    if unknown_categories:
        reasons.append("external verifier categories reference unknown obligations")
    overlap = hook.accepted_obligation_ids & hook.rejected_obligation_ids
    if overlap:
        reasons.append("external verifier both accepts and rejects an obligation")
    if hook.accepted_obligation_ids and (
        hook.resolution_id is None
        or hook.resolution_digest is None
        or hook.evidence_envelope_id is None
        or not hook.evidence_artifact_ids
    ):
        reasons.append("accepted external verifier hook requires resolution provenance")
    if hook.accepted_obligation_ids and (
        hook.domain_witness_required or hook.residual_external_obligations
    ):
        reasons.append("accepted external verifier hook exceeds settled scope")
    for name, value in hook.residual_coordinates.items():
        if value < 0:
            reasons.append("external verifier residual coordinate is negative")
        residual = residual.add_coordinate(f"external-verifier:{name}", value, kind="residual")
    for obligation_id in hook.obligation_ids:
        obligation = known_obligations.get(obligation_id)
        if obligation is None:
            continue
        residual = residual.combine(obligation.residual_charge)
        if obligation_id in hook.rejected_obligation_ids:
            default_failure = (
                obligation.failure_modes[0] if obligation.failure_modes else obligation.failure_mode
            )
            reasons.append(hook.failure_modes.get(obligation_id, default_failure))
    missing = sorted(hook.obligation_ids - hook.accepted_obligation_ids)
    accepted = not reasons and not missing
    return CheckResult(
        accepted=accepted,
        status=ClaimStatus.SETTLED if accepted else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=missing,
        residual_ledger=residual,
    )


class AgentConnectorSpec(BaseModel):
    """Stable JSON-facing connector description for autonomous-agent libraries."""

    connector_id: str
    capabilities: list[str] = Field(default_factory=list)
    capability_routing: dict[str, str] = Field(default_factory=dict)
    input_contract: dict[str, object] = Field(default_factory=dict)
    output_contract: dict[str, object] = Field(default_factory=dict)
    input_schema: dict[str, object] = Field(default_factory=dict)
    output_schema: dict[str, object] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    status_policy: dict[str, object] = Field(default_factory=dict)
    residual_policy: dict[str, object] = Field(default_factory=dict)
    safe_failure_behavior: str = "return-diagnostic-with-obligations"
    failure_modes: list[str] = Field(default_factory=list)
    deterministic: bool = True
