# v0.5.0 Audit

This document records the v0.5.0 Phase Ecology Lab release boundary. The
release target is the v0.5.0 prompt contract, not full canonical settlement of
every ECPT, TRC, SQOT, ALT, or BIT obligation in the papers.

## Contract Status

- Package version: `0.5.0`.
- Prompt-required v0.5.0 record schemas: exported through `schema_by_type()`,
  `pic schema --type`, and `pic schema --all --output-dir`.
- CLI surfaces: `pic phase lab`, `pic ecology effective-graph`,
  `pic ecology execution-available-paths`, `pic bit`, `pic sqot`,
  `pic alt ecpt-lift`, and `pic trc` expose the v0.5.0 diagnostic workflows.
- SDK surface: top-level imports remain function-focused. Detailed records are
  imported from their owning subpackages.

The schema registry is the complete schema truth source. `schemas/index.json`
and `agent-manifest.json` are indexes for agents and humans, not replacement
registries.

## Safety Boundary

All new v0.5.0 Phase Lab, BIT, SQOT, ALT lift, and TRC adapter outputs are
diagnostic-only unless a narrower finite verifier contract says otherwise.
They do not execute embedded command text, `safe_commands`, tool traces, shell
snippets, repository mutations, network requests, model changes, or external
system actions.

Raw packet volume is not progress. Candidate-only packets, registry metadata,
unverified semantic edges, stale packets, missing rollback support, missing
authority, and salience obstructions remain blockers or residuals. Useful
reports can still have `settled=false`; unresolved obligations must remain
machine-readable instead of being promoted to hidden settlement.

## Pip And Portability

The PyPI path is intended to be practical without cloning the repository:

```powershell
python -m pip install percolation-inversion-compiler
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic phase lab init --output-dir pic-demo/phase-lab
pic phase lab ingest --store pic-demo/phase-lab --report pic-demo/phase_lab_runtime_report.json
pic phase lab observe --store pic-demo/phase-lab --window latest
pic phase lab graph --store pic-demo/phase-lab
pic phase lab closure --store pic-demo/phase-lab
pic phase lab executable-paths --store pic-demo/phase-lab
pic phase lab certify --store pic-demo/phase-lab --threshold pic-demo/phase_lab_threshold.json
```

Human-facing commands use explicit files or repeated options instead of relying
on shell glob expansion. Internal literal-pattern expansion remains available
for argv-style integrations and tests, but docs and demo recommendations do not
depend on shell-specific wildcard behavior.

Release artifact checks are target-version specific because a local `dist/`
directory can contain older wheels and sdists:

```powershell
uv run python -m twine check dist\percolation_inversion_compiler-0.5.0-py3-none-any.whl dist\percolation_inversion_compiler-0.5.0.tar.gz
uv run python scripts\check_distribution_artifacts.py --dist-dir dist --version 0.5.0
```

The wheel includes curated runtime/demo/schema assets. It does not vendor root
`examples/`, canonical TeX/PDF files, local build outputs, secrets, private
keys, model weights, or unchecked archives.

## Residual Obligations

`pic audit canonical-readiness --profile development --format json` keeps the
paper-level residual boundary visible. The current residual counts are:

| Theory | Residual external obligations |
| --- | ---: |
| ECPT | 30 |
| TRC | 32 |
| SQOT | 15 |
| ALT | 54 |
| BIT | 0 |
| Total | 131 |

These residuals are future implementation and verification candidates. They are
not v0.5.0 release blockers, and they must not be silently converted into
accepted packet capital, autonomous execution authority, real ASI evidence, or
`settled=true`.

