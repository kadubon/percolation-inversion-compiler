# Phase Plan Compact Contract

`pic phase plan --compact` returns a recommendation-only
`PhaseAccelerationPlan`. It does not require operator adoption and does not
execute commands, routes, shell text, live connectors, or repository mutation.

Interpretation rules:

- if `settled == false`: do not claim final completion.
- if `settled_blockers` is non-empty: route blockers before promotion.
- if `cannot_promote_because` is non-empty: preserve residuals and do not promote.
- if `candidate_only_reasons` is non-empty: keep the packet or source as candidate-only.
- if `safe_commands` is non-empty: inspect them; do not execute without authority.
- if adoption sidecar data is absent: continue normal phase planning.
- if adoption sidecar data is present elsewhere: treat it as operator-facing documentation only.

Phase gaps, bottleneck ranks, benchmark scores, identity readiness, external
volume, `accepted`, and `workflow_usable` do not imply `settled=true`.
