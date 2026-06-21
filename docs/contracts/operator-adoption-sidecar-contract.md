# Operator Adoption Sidecar Contract

Operator adoption support is an optional sidecar. It is not part of the main
agent workflow and must not gate `pic agent check`, `pic phase plan`,
`pic agent accelerate`, packet inspection, benchmark generation, or dashboard
generation.

Interpretation rules:

- if `adoption_sidecar` is absent: continue normal checking and planning.
- if `adoption_sidecar` is present: treat it as operator-facing documentation only.
- if `operator_adoption` is approved: this may authorize local use in that environment.
- approved adoption does not settle external obligations.
- approved adoption does not prove truth.
- approved adoption does not promote packets.
- missing adoption approval is not a failure condition.
- missing adoption approval is not a `settled_blocker`.

Adoption sidecars are pure output generators. They do not install PIC, clone
repositories, call the network, execute shell commands, mutate runtime state,
modify config files, or create approval state required by other commands.
