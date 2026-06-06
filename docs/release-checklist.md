# Release Checklist

- Confirm `pyproject.toml`, `__version__`, `CITATION.cff`, and `CHANGELOG.md` agree.
- Run local quality gates, publish safety scan, Bandit, pip-audit, and Zizmor.
- Verify `pic doctor --profile production --fail-on never` reports expected fail-closed production gaps rather than silent promotion.
- Confirm no canonical TeX/PDF files, local paths, secrets, private keys, or build artifacts are staged.
- Confirm certificate, residual-ledger, and `ExternalProofObligation` wording remains
  protocol-relative and does not claim unobserved physical or ASI proof.
- Create an annotated version tag and verify GitHub CI/Security success on `main`.
