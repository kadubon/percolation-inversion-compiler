# Tutorial

This tutorial uses local fixtures so it can run without vendoring the canonical
TeX sources.

## 1. Install

```powershell
uv sync --all-extras --dev
```

## 2. Check a Minimal Registry

```powershell
uv run pic check --source tests\fixtures\minimal_claims.tex --strict-projection --derive-status
```

Expected behavior:

- the registry projection is accepted;
- declared status is not promoted;
- the derived status summary remains checker-derived.

## 2a. Use Snapshots Without TeX

Users who do not have the canonical TeX files can still inspect the derived
coverage and external-obligation contracts:

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact trc
uv run pic explain external def:null-channel-routing --from-snapshot
uv run pic snapshot routes
uv run pic doctor --fail-on never
```

Snapshots contain DOI/checksum attribution, coverage counts, item-id mappings,
and external verifier contracts. They do not include TeX or PDF content.
`pic doctor` reports whether schemas, snapshots, adapter routes, optional
dependencies, and canonical TeX metadata are operationally ready.

## 3. Emit Schemas

```powershell
uv run pic schema --all --output-dir schemas
```

The bundle includes core records such as `Judgment`, `ObligationSet`,
`TheoryAuditReport`, `ExternalVerifierHook`, theorem-level BIT/ECPT
certificates, and `AgentConnectorSpec`.

## 4. Audit Theory Coverage

```powershell
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --fail-on projection
```

For canonical paper audits, set `PIC_CANONICAL_TEX_DIR` to a local directory that
contains the TeX files. The repository does not vendor those files.

## 5. Run the Datacenter Demo

```powershell
uv run pic demo datacenter
```

The demo emits a TRC compile result with main, diagnostic, relaxed, and partial
frontier records. Main-frontier records require accepted executable trace normal
forms; a self-declared trace flag is not enough.

## 6. Read Coverage

```powershell
uv run pic coverage --source tests\fixtures\minimal_claims.tex
uv run pic explain coverage def:no-status
```

Coverage statuses distinguish finite constructive algorithms, finite checkers,
portable schemas, external proof obligations, and unsupported items. Canonical
coverage should keep `unsupported` at zero.

## 7. Route External Obligations

For canonical sources, external items can be explained as verifier contracts:

```powershell
uv run pic explain external def:null-channel-routing
```

The output is a `TheoryImplementationRecord` with an obligation category,
verifier route, accepted evidence kinds, residual policy, safe default, and
failure modes. Agent integrations should use that record to decide whether to
call a domain adapter or keep a diagnostic/partial result.

When TeX is unavailable, add `--from-snapshot` to read the bundled derived
metadata instead.
