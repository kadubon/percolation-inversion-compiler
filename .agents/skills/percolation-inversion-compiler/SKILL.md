---
name: percolation-inversion-compiler
description: "Check AI-agent outputs and compile finite inputs into residual-preserving capability, verifier-routing, and evidence structures with Percolation Inversion Compiler. Use for capability packets, proof obligations, agent-result admission, finite trace/provenance checks, bottleneck inversion, safe operation planning, or protocol-relative ASI-proxy diagnostics. Start check-only; do not use to claim real ASI, settlement, execution, physical success, legal authority, or general scientific proof."
license: Apache-2.0
metadata:
  author: K. Takahashi
  repository: https://github.com/kadubon/percolation-inversion-compiler
  version: "1.0"
---

# Percolation Inversion Compiler

Preserve unknowns and obligation failures; acceptance is a scoped diagnostic state, never a collapsed success claim.

## Fast path

1. Start with `pic doctor` and identify the finite input, profile, and desired check.
2. Run the non-executing first-pass checker.
3. Inspect accepted, finite checks, operational usability, settled state, blockers, residuals, and acceleration certification separately.
4. Use a plan/runbook before any integration or operation path.
5. Stop for explicit authority before consequential external action.
6. Report evidence, residuals, scope, and non-claims separately.

## When to use

Use for general agent outputs, capability packets, finite trace verification, verifier routing, proof obligations, residual ledgers, resource-matched acceleration, approval-bounded operation planning, and explicit protocol-relative ASI-proxy diagnostics. For a primary verification-evidence object use VEK; for persistent agent memory use CMGL; for autonomous science use Audit-Closed; for trust-fixture evaluation use ATRB.

## Do not use

- To claim real ASI, model improvement, settlement, legal authority, or physical-world success.
- To execute a real external operation without an explicit user request and host authorization.
- As a substitute for generic unit tests, a deployment controller, or a physical-world verifier.

## Workflow

Default to check-only:

```text
uv run pic doctor
uv run pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
uv run pic agent runbook --profile development
uv run pic phase plan --compact --text "Candidate packet: preserve residuals." --profile development
```

Use `pic agent intake` or `percolation_inversion_compiler.agent.run_agent_intake` only when the full intake report is needed. Inspect `accepted`, `finite_checks_passed` where emitted, `workflow_usable`/`operationally_usable`, `settled`, `missing_obligations`, `residual_ledger`, and any acceleration metrics independently. Read [result semantics](references/result-semantics.md) before interpreting the report.

Operation mode is exceptional and must remain explicitly sequenced:

```text
adapter-check -> plan -> preflight -> approve -> dispatch -> verify -> reconcile
```

Do not dispatch from a provider receipt alone. Read [operation boundary](references/operation-boundary.md) only if the user explicitly requested an operation and authority exists.

## Evidence and result semantics

`accepted=true` does not imply settled, action allowed, dispatch occurred, physical outcome, real ASI, model improvement, or legal authority. A provider receipt is evidence of the provider's reported event, not proof of a physical result. Plans are recommendation-only unless a separately authorized dispatcher and later verification/reconciliation establish more.

## Retrieve only what is needed

- Read `docs/for-agents.md` for the smallest safe CLI/API path.
- Read [result semantics](references/result-semantics.md) for output interpretation.
- Read [operation boundary](references/operation-boundary.md) only for an authorized operation request.
- Read `docs/01-quickstart.md` or `docs/agent-external-communication.md` only for the chosen integration surface.

## Validate

```text
uv run pytest
uv run pic doctor
uv run pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
```

## Report

State outcome; exact checked fields/evidence; blockers and residuals; authority/profile scope; non-claims; and the next safe action. Do not use a bare word such as “success.”

## Required non-claims

- Accepted is not settled, dispatched, physically verified, or legally authorized.
- Finite checks and acceleration diagnostics are protocol-relative.
- Unknowns and residual ledgers must remain explicit.
