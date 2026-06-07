# Safety Boundary

This repository is intentionally useful for agents, but it is fail-closed. It helps agents route finite evidence and obligations; it does not grant authority to perform unsafe execution or claim unverified outcomes.

## Non-Claims

- No package-level proof of real ASI.
- No proof of unobserved physical, simulator, oracle, or policy outcomes.
- No requirement for self-rewrite, fine-tuning, or model-weight changes.
- No promotion from declared status, registry metadata, snapshot metadata, queue priority, or agent text.
- No implicit settlement of external obligations.

## Execution Boundary

The standard runtime executor is allowlist-based. It supports finite verification tasks such as evidence verification, schema validation, snapshot verification, parse audit, local packet ingestion, route execution, runtime step/apply/compare/certify, and store operations. Arbitrary shell commands, repository mutation, network access, and live connectors require explicit adapters and policy grants.

Production service defaults:

- bind to loopback unless configured otherwise;
- require bearer authentication;
- reject live connector use unless explicitly requested;
- avoid returning stack traces, secrets, private keys, or local absolute paths;
- preserve residual ledgers rather than hiding unresolved obligations.

## Status Discipline

Use `operationally_usable` for routing decisions. Use `settled` only for scoped finite obligations actually discharged by verifier rules. A useful recommendation may still have `settled=false`.

## Residual Ledgers

Residual coordinates are part of the result, not an error to suppress. They carry missing evidence, external-domain limits, fallback proxy use, stale evidence, hidden-injection rejection, verification backlog, or resource mismatch.

## Recommended Agent Policy

1. Ingest packet candidates.
2. Verify evidence and semantic edges.
3. Promote only packets that pass the production promotion policy.
4. Schedule with SQOT while preserving diagnostic reserve.
5. Execute only allowlisted finite tasks.
6. Apply results into the runtime store.
7. Certify only resource-matched protocol-relative improvements.
