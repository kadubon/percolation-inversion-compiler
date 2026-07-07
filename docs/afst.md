# AFST Satisfaction-Flux Diagnostics

AFST means Abundance-Flux Stabilization. In PIC it is a non-executing
diagnostic checker for one practical question: can certified typed surplus
reduce a declared satisfaction deficit while preserving authority, consent,
refusal, resource balance, stabilization buffers, handover limits, lifecycle
freshness, and residual ledgers?

AFST is not execution authority. An accepted AFST report is not settlement, not
provider dispatch, not physical dispatch, not market or ownership override, not
contract override, not consent bypass, not refusal suppression, not resource
creation, not ALT capital admission, and not ECPT phase promotion.

## When To Use It

Use AFST when an agent or operator needs to inspect a proposed resource flux:

- a source cell has certified local surplus after floors, reserves, legal holds,
  spoilage, transfer loss, observation residuals, lifecycle residuals, and hard
  residuals;
- a target cell has a declared satisfaction deficit;
- a candidate flux connects the source and target in compatible units;
- authority, refusal, optional consent, resource balance, buffer, and handover
  checks must remain visible.

Search terms: AFST, abundance flux stabilization, satisfaction flux, certified
abundance, satisfaction deficit, non-market liquidity, stabilization buffer,
shock envelope, resource balance witness, bounded-friction handover, refusal
channel, consent channel, authority envelope, residual-preserving diagnostics.

## First Commands

From a source checkout:

```powershell
uv run pic afst check --case examples/afst/minimal_accepted.json --compact
uv run pic afst check --case examples/afst/blocked_refusal.json --output afst-report.json
uv run pic afst emit-ccr-tasks --report afst-report.json
uv run pic afst buffer --buffer examples/afst/blocked_missing_shock.json
uv run pic afst handover --handover examples/afst/handover_minimal.json
uv run pic afst balance --witness examples/afst/balance_witness.json
uv run pic schema --type AFSTFluxStabilizationReport
```

From an installed PyPI package without cloning the repository:

```powershell
pic demo bootstrap --output-dir pic-demo --overwrite
pic afst check --case pic-demo/afst/minimal_accepted.json --compact
pic afst check --case pic-demo/afst/blocked_refusal.json --output pic-demo/afst-report.json
pic afst emit-ccr-tasks --report pic-demo/afst-report.json
pic afst buffer --buffer pic-demo/afst/blocked_missing_shock.json
pic afst handover --handover pic-demo/afst/handover_minimal.json
pic afst balance --witness pic-demo/afst/balance_witness.json
pic schema --type AFSTFluxStabilizationReport
```

## Reading The Report

Important top-level fields:

- `accepted`: finite AFST checker acceptance only.
- `flux_admissible`: the candidate flux passed AFST gates; it is still not
  dispatch authority.
- `settled`: always false in AFST v1 outputs.
- `operation_ready`, `provider_dispatch_ready`, `physical_dispatch_ready`: always
  false in AFST v1 top-level reports.
- `blockers`: blocking residual kinds such as `refusal_active`,
  `missing_shock_envelope`, `resource_balance_violation`,
  `missing_authority_envelope`, or `unit_mismatch`.
- `non_claims`: machine-readable warnings against unsafe interpretation.

Missing fields are not treated as zero or false. A missing shock envelope is not
zero shock; missing refusal data is not no refusal; missing authority is not
valid authority.

## Missing Data Policy

AFST audits raw JSON before applying defaults. When a required field is absent,
the report preserves an explicit residual such as
`missing_certified_abundance_cell_id`,
`missing_satisfaction_deficit_target_cell_id`, or
`missing_resource_balance_witness_witness_id`.

This rule is deliberately strict: missing data never becomes available surplus,
no-refusal evidence, valid authority, consent, balance proof, ALT admission, or
ECPT phase progress. Agents should repair these residuals by adding scoped
evidence, not by treating the empty field as zero.

## CCR Repair Tasks

`pic afst emit-ccr-tasks` maps AFST residuals into dry-run CCR task candidates:

- liquidity and deficit blockers become `afst_liquidity_repair`;
- buffer and shock blockers become `afst_buffer_repair`;
- handover blockers become `afst_handover_repair`;
- authority blockers become `afst_authority_repair`;
- refusal and legal-hold blockers become `afst_refusal_channel_repair`;
- consent blockers become `afst_consent_channel_repair`;
- resource-balance blockers become `afst_balance_witness_repair`.

These tasks are candidate-only repair work. They do not execute providers,
mutate repositories, run shells, or promote settlement.
