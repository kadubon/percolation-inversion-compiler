# Third-Party Licenses

Runtime dependencies are selected from permissive or weak-copyleft-compatible
packages suitable for Apache-2.0 distribution:

- Pydantic: MIT
- Typer: MIT
- Rich: MIT
- PyYAML: MIT
- jsonschema: MIT

Optional extras:

- HTTPX: BSD-3-Clause
- NumPy: BSD-3-Clause
- SciPy: BSD-3-Clause
- NetworkX: BSD-3-Clause
- Pint: BSD-3-Clause
- POT: MIT
- HiGHS / highspy: MIT

Development and security tooling:

- Bandit: Apache-2.0
- coverage.py: Apache-2.0
- Hypothesis: MPL-2.0
- mypy: MIT
- pip-audit: Apache-2.0
- pytest: MIT
- pytest-cov: MIT
- Ruff: MIT
- types-jsonschema: Apache-2.0
- types-PyYAML: Apache-2.0

Workflow actions and scanners referenced by CI/security workflows are not
vendored into the package. Dependabot is configured to keep those references
current, and release preparation should re-check upstream licenses for
`actions/checkout`, `actions/setup-python`, `astral-sh/setup-uv`,
`github/codeql-action`, `actions/dependency-review-action`, `gitleaks`, and
`zizmor`.

The ECPT, BIT, TRC, and SQOT Zenodo papers are CC-BY-4.0 according to Zenodo
metadata. They are cited in `NOTICE` and are not included as vendored source
files.
