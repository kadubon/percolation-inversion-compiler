# Canonical Implementation Readiness

`pic audit canonical-readiness` is a pip-safe sidecar for agents and language
ports that need canonical ECPT/BIT/TRC/SQOT/ALT implementation coverage without
local TeX sources:

```powershell
pic audit canonical-readiness --profile development --format json
pic audit canonical-readiness --profile development --format markdown
pic schema --type CanonicalImplementationReadinessReport
```

The report is derived from bundled snapshot metadata. It does not vendor TeX or
PDF files, does not replace `pic audit fidelity` when canonical source files are
available, and does not claim new mathematical evidence.

Use the report to inspect:

- per-theory implemented item counts, external obligations, unsupported items,
  and partial items;
- residual category totals and finite upgrade candidates;
- pip-safe, argv-shaped next invocations for agents;
- stable schema-first portability invariants for non-Python ports.

Safety boundary:

- `accepted=true` means the bundled snapshot set is complete enough for
  installed workflow inspection.
- `settled` remains `false`; external obligations remain explicit residual
  work.
- Adoption, approval, benchmark scores, dashboard metrics, and canonical
  readiness do not gate `pic agent check`, `pic phase plan`, `pic agent
  accelerate`, or `pic agent intake`.
- `safe_commands` and recommended invocations are inert data. PIC does not
  execute them.

For source-level release verification, use:

```powershell
pic audit canonical-suite --canonical-dir <canonical-tex-dir>
pic audit fidelity --canonical-dir <canonical-tex-dir>
```

