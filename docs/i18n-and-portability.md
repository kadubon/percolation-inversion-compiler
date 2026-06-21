# I18n And Portability

PIC keeps machine contracts language-stable:

- JSON keys, schema names, enum-like identifiers, command ids, and safety flags
  remain English and stable for SDKs, CLIs, CI, and cross-language ports.
- Markdown renderers may localize display headings and explanatory text.
- Localized Markdown never changes `accepted`, `workflow_usable`, `settled`,
  residual, adoption, approval, or command-execution semantics.
- `argv` arrays are the portable command representation. Shell command strings
  are display text only and are not executed by PIC.
- `pic audit canonical-readiness` exposes bundled ECPT/BIT/TRC/SQOT/ALT
  implementation coverage without local TeX sources, so ports can start from a
  pip-installed schema-first contract.

Current localized Markdown surfaces:

```powershell
pic adoption packet --format markdown --language ja
pic adoption request --format markdown --language ja
pic agent autonomy-audit --format markdown --language ja
```

Porting guidance:

- Preserve `settled=false` unless scoped finite verifier rules settle the
  relevant obligations.
- Treat adoption, benchmark scores, phase dashboards, and packet exchange as
  sidecars, not gates.
- Treat canonical readiness as snapshot-derived implementation metadata, not a
  TeX source audit and not a settled truth claim.
- Do not use localized prose as a parser input when JSON schemas are available.
- Keep OS-specific quoting out of protocol records by using `argv` arrays.
