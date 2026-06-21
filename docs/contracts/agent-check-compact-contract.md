# Agent Check Compact Contract

`pic agent check --compact` is the shortest practical PIC contract for agents,
CI jobs, and first-time operators. It does not require adoption approval,
operator packets, approval tokens, or approval state.

Interpretation rules:

- if `settled == false`: do not claim final completion.
- if `accepted == true and settled == false`: treat the output as useful candidate work, not final truth.
- if `unresolved_obligations` is non-empty: route obligations before promotion.
- if `residual_summary` is non-empty: preserve residuals downstream.
- if `next_safe_actions` is non-empty: inspect them; do not execute without authority.
- if adoption sidecar data is absent: continue normal checking.
- if adoption sidecar data is present elsewhere: treat it as operator-facing documentation only.

`accepted=true` means the finite checker accepted the report shape and routing
record. It does not mean settled truth. `workflow_usable=true` means the report
is usable for the next verification or planning step. It does not promote
packets and does not grant execution authority.
