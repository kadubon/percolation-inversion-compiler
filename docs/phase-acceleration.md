# Phase Acceleration Planner

The phase acceleration planner turns existing PIC reports into a ranked list of
safe next steps for humans, CI jobs, and AI agents.

In common terms, **phase acceleration** means improving a workflow by reusing
checked work items, routing evidence, preserving unresolved work, and removing
bottlenecks. In PIC terms, it is protocol-relative ASI-proxy coordination: many
agents can exchange candidate work, verify reusable packet capital, keep SQOT
queues healthy, certify ALT abstraction value, and compare against baselines.
It is not a proof of real ASI, physical outcomes, simulator truth, or oracle
truth.

## First Commands

```powershell
pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
pic phase plan --compact --text "Candidate packet: preserve residuals." --profile development
pic phase plan --request examples/phase_acceleration/phase_acceleration_request.json --compact
pic agent accelerate --compact --text "Candidate packet: preserve residuals." --profile development
pic phase runbook --profile development
pic schema --type PhaseAccelerationPlan
```

`pic agent check --compact` remains the first practical command. Run
`pic phase plan --compact` next when an agent needs to choose what to verify,
repair, certify, or preserve.

## What The Plan Contains

- `phase_gap_vector`: finite Psi component gaps and limiting components.
- `bottlenecks`: ranked ECPT, BIT, TRC, SQOT, ALT, identity, route, and external-candidate work.
- `recommended_actions`: safe next steps with commands, SDK calls, schemas, and fields to inspect.
- `cannot_promote_because`: blockers to packet or capital promotion.
- `candidate_only_reasons`: why external inputs, peer messages, or ALT outputs remain candidates.
- `settled_blockers`: why `settled=false` remains correct.

## Inputs

The planner can use a `RuntimeStepReport` directly, or it can run one local
runtime step from `RuntimeState` and `RuntimeStepInput`. It can also include
adjacent reports through `PhaseAccelerationRequest`: ALT admission decisions,
foundry dashboards, general-intake runtime bridges, agent-message delivery
reports, and identity context.

```powershell
uv run pic phase plan --state examples/runtime_state.json --input examples/runtime_step_input.json --profile development
uv run pic phase plan --request examples/phase_acceleration/phase_acceleration_request.json --compact
uv run pic phase plan --runtime-report runtime-step.json --compact
uv run pic phase trajectory --report runtime-step-1.json --report runtime-step-2.json
uv run pic phase benchmark --profile development
uv run pic phase benchmark-suite --profile development --format json
uv run pic phase dashboard --profile development --format json
```

When `--request` is supplied, the request file is the source of runtime input.
Do not combine it with `--state`, `--input`, `--runtime-report`, `--text`, or
`--text-file`. `--profile`, `--identity-context`, and live-connector flags may
be used as explicit operator overrides.

## Safety Boundary

The planner never executes shell commands, starts background crawling, grants
network authority, mutates a repository, or promotes status. `safe_commands`
are deterministic instructions to inspect or run under operator control. Raw
external packet volume, unsigned peer messages, proxy-only ALT value evidence,
and missing production identity context do not reduce phase gaps or clear
settlement blockers.

`pic phase benchmark-suite` and `pic phase dashboard` are sidecars. They report
diagnostic benchmark and observation metrics only. They do not change phase-gap
computation, approve execution, promote packets, or set `settled=true`.

In `production` and `adversarial` profiles, missing or rejected identity context
appears in `cannot_promote_because` and `settled_blockers`. Passing an accepted
`RuntimeIdentityContext` can remove the identity-readiness blocker, but it does
not settle residual obligations or prove real-world outcomes.

For ports, `PhaseAccelerationPlan`, `PhaseGapVector`, `BottleneckCandidate`,
`SafePhaseAction`, `PhaseComponentGap`, `PhaseTrajectoryReport`, and
`PhaseAccelerationBenchmarkReport` are JSON Schema contracts. Python is the
reference implementation; JSON Schema is the cross-language contract.
