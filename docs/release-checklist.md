# Release Checklist

- Confirm `pyproject.toml`, `__version__`, `CITATION.cff`, and `CHANGELOG.md` agree.
- Run local quality gates, publish safety scan, Bandit, pip-audit, and Zizmor.
- Run `uv build` and `uv run python -m twine check dist\*.whl dist\*.tar.gz` before any PyPI
  publication.
- Run `uv run python scripts\check_distribution_artifacts.py` and confirm the
  wheel contains `py.typed`, bundled theory snapshots, and only the curated
  `percolation_inversion_compiler.data.demo` assets.
- Verify the pip-first installed-package path:
  `pic demo installed-smoke --profile development`,
  `pic demo bootstrap --output-dir pic-demo`, and
  `pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development`.
- Confirm README, AGENTS.md, and quickstart docs separate the PyPI path from
  the clone-recommended full workflow, including
  `git clone https://github.com/kadubon/percolation-inversion-compiler.git`
  and current `uv` install commands.
- Verify `pic doctor --profile production --fail-on never` reports expected fail-closed production gaps rather than silent promotion.
- Generate the schema bundle, provenance manifest, SBOM, wheel, and sdist release assets.
- Verify `pic routes bindings`, `pic evidence verify --profile production`,
  `pic evidence discharge --profile production`, and
  `pic doctor --profile production --provenance <manifest> --fail-on fail`.
- Verify `pic sqot schedule`, `pic ecology build-edges`, `pic ecology psi`,
  `pic ecology plan`, and `pic ecology loop` smoke tests.
- Confirm no canonical TeX/PDF files, local paths, secrets, private keys, or build artifacts are staged.
- Confirm the wheel does not include root `examples/`, local virtualenvs,
  vendored archives, model weights, serialized datasets, credential folders, or
  private-key-like files.
- Confirm `.github/workflows/pypi-publish.yml` uses PyPI Trusted Publishing,
  the `pypi` environment, `id-token: write`,
  `uv publish --trusted-publishing always`, and no API token or password fields.
- Confirm PyPI Trusted Publisher settings match repository
  `kadubon/percolation-inversion-compiler`, workflow `pypi-publish.yml`, and
  environment `pypi`.
- Confirm certificate, residual-ledger, and `ExternalProofObligation` wording remains
  protocol-relative and does not claim unobserved physical or ASI proof.
- Create or verify the annotated version tag, publish from the matching tag via
  Trusted Publishing, and verify GitHub CI/Security success on `main`.
