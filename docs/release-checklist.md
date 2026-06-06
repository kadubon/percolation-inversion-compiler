# Release Checklist

- Confirm `pyproject.toml`, `__version__`, `CITATION.cff`, and `CHANGELOG.md` agree.
- Run local quality gates, publish safety scan, Bandit, pip-audit, and Zizmor.
- Verify `pic doctor --profile production --fail-on never` reports expected fail-closed production gaps rather than silent promotion.
- Generate the schema bundle, provenance manifest, SBOM, wheel, and sdist release assets.
- Verify `pic routes bindings`, `pic evidence verify --profile production`,
  `pic evidence discharge --profile production`, and
  `pic doctor --profile production --provenance <manifest> --fail-on fail`.
- Verify `pic sqot schedule`, `pic ecology build-edges`, `pic ecology psi`,
  `pic ecology plan`, and `pic ecology loop` smoke tests.
- Confirm no canonical TeX/PDF files, local paths, secrets, private keys, or build artifacts are staged.
- Confirm certificate, residual-ledger, and `ExternalProofObligation` wording remains
  protocol-relative and does not claim unobserved physical or ASI proof.
- Create an annotated version tag and verify GitHub CI/Security success on `main`.
