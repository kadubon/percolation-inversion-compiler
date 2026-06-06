# Theory Coverage

The package indexes ECPT, BIT, TRC, and SQOT TeX sources and emits a coverage matrix
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
adversarial-transfer witnesses, and external simulator or oracle claims. These
must remain explicit obligations until a finite checker or verified adapter is
supplied.

Bundled snapshots expose the same coverage shape without TeX:

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact ecpt
uv run pic snapshot show --artifact sqot
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
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\\Typed Reality Compilation.tex" --fail-on projection
```
