# Theory Coverage

The package indexes ECPT, BIT, TRC, SQOT, and ALT TeX sources and emits a coverage matrix
with one row per definition, theorem, proposition, lemma, corollary, and
machine-readable record.

Coverage statuses:

- `implemented_constructive`: finite algorithm constructs the claimed object or bound.
- `implemented_checker`: finite checker/certificate validates supplied evidence.
- `implemented_schema`: portable schema exists, but construction/checking is external or elsewhere.
- `partial`: finite interface exists, but not all proof clauses are executable.
- `external_obligation`: the paper requires a domain proof, simulator witness,
  statistical assumption, or external certificate.
- `unsupported`: no stable implementation interface exists yet.

Expected canonical counts from the current Zenodo TeX sources:

| Artifact | Definitions | Claims | Machine-readable records |
| --- | ---: | ---: | ---: |
| ECPT | 79 | 35 | filecontents registry |
| BIT | 22 | 20 | 92 MR records |
| TRC | 70 | 46 | filecontents registry |
| SQOT | 59 | 74 | none |
| ALT | 159 | 197 | none |

The BIT MRRecord total is category-sensitive: the current canonical TeX yields
18 claim records, 9 witness records, 8 dependency records, 53 citation records,
and 4 metadata records, for a total of 92 line-oriented records.

Latest local audit snapshot:

| Artifact | Constructive | Checker | Schema | Partial | External obligation | Unsupported |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ECPT | 18 | 48 | 18 | 0 | 30 | 0 |
| BIT | 15 | 24 | 3 | 0 | 0 | 0 |
| TRC | 20 | 52 | 12 | 0 | 32 | 0 |
| SQOT | 22 | 78 | 18 | 0 | 15 | 0 |
| ALT | 47 | 202 | 53 | 0 | 54 | 0 |

Audit output also reports:

- `coverage_delta`: implemented and unimplemented totals by artifact.
- `unimplemented_by_section`: unsupported rows grouped by section.
- `implemented_with_obligations`: implemented rows that still expose proof obligations or residual coordinates.
- `external_obligation_catalog`: domain-specific or non-finite obligations that must not be promoted.
- `external_obligation_category_summary`: counts by verifier-oriented external category.
- `external_verifier_route_summary`: counts by adapter route.
- `finite_constructive_targets`: unsupported or partial rows that are candidates for finite checkers.

The current canonical audit has no `unsupported` or `partial` rows. Remaining
external areas are thermodynamic and activation-limit clauses, trace and
lifecycle soundness clauses, domain-specific physical envelopes, hybrid residual
propagation, certified submodular redesign, SQOT protocol-integrity/privacy or
adversarial-transfer witnesses, ALT transport/causal/root/telemetry/hazard/
reproduction/target witnesses, and external simulator or oracle claims. These
must remain explicit obligations until a finite checker or verified adapter is
supplied.

For ALT, checker coverage means the repository exposes finite interfaces for
abstraction-token admission, signed lower-bound surplus, negative liquidity,
deprecation/resurrection, baseline refresh, root/finality, telemetry, hazard,
reproduction diagnostics, and ALT-CARA certificates. v0.4.4 also separates
proxy-only value evidence from calibrated proxy bridges and causal evidence
refs. It does not mean that raw external intake, agent text, or problem-solving
traces are capital. A token contributes to ECPT collective phase metrics only
after the finite ALT checks and the existing semantic-edge, verifier-route,
identity/Sybil, rollback, and residual-policy gates accept the scoped claim.

Runtime outputs expose theory coverage in practical form. Prefer the typed
v0.4.4 fields `phase_control_audit`, `frontier_debt_report`, and
`bottleneck_witness_reports`; compatibility summaries remain available as
`phase_control_summary`, `frontier_debt_summary`, and
`bottleneck_witness_tasks`. These are derived convenience fields, not new
settlement rules.

`PhaseAccelerationPlan` is the practical aggregation layer over those typed
reports. It does not change canonical coverage counts. It combines ECPT phase
gaps, BIT bottleneck witnesses, TRC frontier debt, SQOT queue diagnostics, ALT
admission/foundry signals, external candidate-only reports, and identity
readiness into ranked safe next actions. This makes theory coverage usable by
first-time agents and non-Python ports while preserving all residual
obligations.

For the ASI-proxy objective, these reports expose the finite conditions that a
network of agents can repeatedly inspect: verified packet reuse, residual debt,
queue reserve, bottleneck release, abstraction liquidity, and verifier routes.
They are theory-fidelity instruments, not evidence that real ASI or external
physical outcomes have been achieved.

The current theory-fidelity layer adds finite diagnostics for ECPT
split-certified quotient readiness, duplicate-mass exclusion, proxy grounding,
baseline comparison, execution availability, and queue/capacity margin; BIT
bottleneck witnesses as portable verifier tasks; TRC physical null-channel,
hybrid propagation, telemetry resource-cost, progressive-fidelity, and
trace-normal-form debt; SQOT distributed/adversarial transfer, sovereignty,
privacy/rejoin, discharge, reserve, rollback, aggregation, and label-laundering
signals; and ALT common-estimand, conditional proxy bridge, causal evidence,
transportability, instrumentation/contamination, baseline refresh, negative
liquidity, CARA residual, and foundry capacity labels. These diagnostics expose
finite subclaims while preserving residual external obligations.

Bundled snapshots expose the same coverage shape without TeX:

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact ecpt
uv run pic snapshot show --artifact sqot
uv run pic snapshot show --artifact alt
uv run pic schema --type PhaseAccelerationPlan
uv run pic phase plan --compact --profile development
```

When canonical TeX is available, `pic audit theory` also emits `snapshot_delta`
so CI can detect drift between extracted coverage and the bundled derived
snapshot.

```powershell
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\\Typed Reality Compilation.tex" --canonical-key trc --fail-on snapshot
```

For one external item, emit the verifier contract:

```powershell
uv run pic explain external def:null-channel-routing
```

Run:

```powershell
$env:PIC_CANONICAL_TEX_DIR = "path\\to\\canonical\\tex\\directory"
uv run pic coverage --source "$env:PIC_CANONICAL_TEX_DIR\\Typed Reality Compilation.tex"
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\\Typed Reality Compilation.tex" --canonical-key trc
uv run pic sqot audit --source "$env:PIC_CANONICAL_TEX_DIR\\Salience-Queue Occupation Theory.tex" --strict-grammar
uv run pic alt audit --source "$env:PIC_CANONICAL_TEX_DIR\\Abstraction Liquidity Theory.tex" --strict-grammar
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\\Typed Reality Compilation.tex" --fail-on projection
```

For release and commercial-readiness checks, audit the full canonical suite in
one command. This command only accepts the five canonical filenames and excludes
unrelated TeX sources from SQOT/ALT snapshot comparisons.

```powershell
uv run pic audit canonical-suite --canonical-dir "$env:PIC_CANONICAL_TEX_DIR"
uv run pic audit fidelity --canonical-dir "$env:PIC_CANONICAL_TEX_DIR"
```

`pic audit fidelity` is derived from the same canonical-suite audit. It reports
strict grammar status, snapshot health, external-obligation totals, and finite
upgrade candidates. It does not erase external obligations or claim real ASI
evidence.

For installed agents without local canonical TeX files, use the snapshot-derived
canonical readiness sidecar:

```powershell
pic audit canonical-readiness --profile development --format json
pic schema --type CanonicalImplementationReadinessReport
```

This report exposes the bundled ECPT/BIT/TRC/SQOT/ALT implementation coverage,
residual categories, finite upgrade candidates, and argv-safe next actions. It
does not vendor TeX/PDF sources, replace source-level fidelity audits, or set
`settled=true`.
