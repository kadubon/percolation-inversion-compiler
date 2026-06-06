# Agent Integration

Percolation Inversion Compiler is intended to be called by autonomous agents as a
deterministic certificate service. The service does not tell an agent that a
physical or ASI claim is true. It tells the agent which finite certificates are
accepted, which proof obligations remain, and which residual ledger coordinates
must be charged.

## Stable Calls

Use these commands as integration boundaries:

```powershell
uv run pic check --source tests\fixtures\minimal_claims.tex --strict-projection --derive-status
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --fail-on projection
uv run pic schema --type AgentConnectorSpec
uv run pic schema --all --output-dir schemas
uv run pic demo datacenter
uv run pic explain external def:null-channel-routing
uv run pic doctor --fail-on warn
```

The JSON outputs are designed for language-neutral consumers:

- statuses are strings;
- finite sets and tuples are arrays at schema boundaries;
- proof obligations and residual ledgers are explicit objects;
- failure modes are strings intended for routing and policy checks.

## Connector Policy

An agent connector should implement this policy:

1. Validate input JSON against the emitted schema bundle.
2. Run `pic doctor` in the execution environment before operational use.
3. Run a checker command before using registry or frontier records.
4. Treat `declared_status` as metadata and `derived_status` as checker output.
5. Refuse main operational actions when `missing_obligations` is nonempty.
6. Route external proof obligations to domain adapters through
   `ExternalVerifierHook`.
7. Preserve residual ledgers in logs and downstream planning records.

## Routing Recipe

For each audit report:

1. Read `coverage_delta`; fail CI or agent planning when `unsupported_total` is
   nonzero.
2. Read `external_obligation_category_summary`; choose adapter families by
   category, not by informal label text.
3. For every external item, call `pic explain external <item-id>` and validate
   the result against `TheoryImplementationRecord.schema.json`.
4. Call the domain adapter only when it can produce an `ExternalVerifierHook`
   with accepted or rejected obligation ids and explicit residual coordinates.
5. Keep the safe default when the hook is missing, rejected, nondeterministic, or
   outside the advertised verifier contract.

Minimal unresolved hook shape:

```json
{
  "hook_id": "example-null-channel-verifier",
  "verifier_route": "trc.adapters.physical_hybrid.verify_envelope",
  "obligation_ids": ["obligation:def:null-channel-routing"],
  "accepted_obligation_ids": [],
  "rejected_obligation_ids": [],
  "safe_default": "return-diagnostic-with-unresolved-obligations",
  "residual_coordinates": {
    "null-channel-unverified": 1.0
  }
}
```

## Safe Failure

Diagnostic output is not a crash. It is the expected safe result when evidence is
missing, a domain verifier is absent, a trace is stale, or a physical assumption
has not been certified. Agents should keep the diagnostic record and either ask
for more evidence, run a domain adapter, or return a partial frontier.

## ASI-Proxy Framing

The intended use is protocol-relative ASI-proxy phase-control research. Agents
can use the package to organize capability, bottleneck, and cyber-physical
frontier evidence. They must not treat it as evidence for unobserved ASI,
unconditional phase transition claims, or uncertified simulator output.
