# ASI-Proxy Acceleration

v0.8.0 treats ASI-proxy/CARA acceleration as a target-valid comparison:
the target set, baseline upper envelope, and runtime capital witnesses must be
declared before outcome observation. A report can become a certified
acceleration candidate only when admitted lower-bound capital crosses the
declared target with positive margin before a resource-matched baseline upper
envelope.

Search terms: ASI-proxy acceleration, CARA, runtime capital witness, baseline
upper envelope, target-validity certificate, phase acceleration report, PIC,
CCR, residual ledger, MCP, A2A, SQOT, BIT, TRC.

ASI-proxy acceleration means measurable improvement in protocol-relative
workflow formation, not evidence of real ASI.

PIC exposes acceleration through finite artifacts:

- phase gap vectors and bottleneck candidates;
- ALT liquidity and negative-liquidity diagnostics;
- SQOT queue, diagnostic reserve, and salience occupation reports;
- TRC trace normal forms with authority, rollback, and resource residuals;
- BIT machine-readable witness records.

CCR can consume these artifacts as JSON or JSONL task and residual inputs. PIC
interop output remains provider evidence for CCR; it is not CCR settlement,
automatic provider execution, or permission to discard residuals.

For real-world operation candidates, PIC's TRC checker requires a finite trace
normal form with an authority envelope, resource ledger, rollback or escrow
obligation, tolerance ledger, preconditions, and postconditions. A trace may be
execution-available only as a checked operation candidate; PIC does not execute
the action and does not prove the physical outcome.

The conservative rule is monotone non-promotion: a new candidate can add routes,
residuals, or tasks, but it cannot become settled unless the required verifier
and baseline obligations are discharged.

`capital_admitted=true` is lower-bound evidence, not settlement. Proxy-only
evidence cannot increase safe capital. Raw packet count, duplicate mass, and
unchecked candidate inflow do not count as positive progress.

`pic.phase_acceleration_report.v1` is fail-closed. Missing or stale baseline
envelopes, unapproved authority, non-accepted mission/generated/externality
laws, rejected hazard/capability/viability envelopes, absent admitted runtime
capital witnesses, proxy-only capital, and raw-net floor failures set `ok=false`
with explicit residual blockers. A report can still be well formed while
`certified_acceleration_candidate=false` if the target margin is not positive.

MCP descriptors are checked before invocation. A descriptor with
`descriptor_changed_after_approval=true` is rejected at descriptor-report time
and again at invocation-preflight time.

## Benchmark Interpretation

The `examples/asi_proxy_benchmark_bundle/` files are a dry-run bundle. They
show whether candidate work becomes easier to route and verify. They do not
measure autonomous general intelligence.
