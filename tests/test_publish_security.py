from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _publish_safety_main() -> int:
    script_path = ROOT / "scripts" / "check_publish_safety.py"
    spec = importlib.util.spec_from_file_location("check_publish_safety", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return int(module.main())


def test_citation_cff_references_all_papers() -> None:
    data = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    dois = {reference["doi"] for reference in data["references"]}
    assert data["version"] == "0.4.4"
    assert data["doi"] == "10.5281/zenodo.20569166"
    assert data["repository-code"] == "https://github.com/kadubon/percolation-inversion-compiler"
    assert "OWNER/" not in data["repository-code"]
    assert "10.5281/zenodo.20535654" in dois
    assert "10.5281/zenodo.20545356" in dois
    assert "10.5281/zenodo.20554083" in dois
    assert "10.5281/zenodo.20526451" in dois
    assert "10.5281/zenodo.20476200" in dois


def test_release_version_metadata_is_consistent() -> None:
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    init_text = (ROOT / "src" / "percolation_inversion_compiler" / "__init__.py").read_text(
        encoding="utf-8"
    )
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert pyproject["project"]["version"] == "0.4.4"
    assert citation["version"] == "0.4.4"
    assert citation["date-released"] == "2026-06-20"
    assert re.search(r"^__version__\s*=\s*[\"']0\.4\.4[\"']", init_text, re.MULTILINE)
    assert re.search(r"^## v0\.4\.4 - 2026-06-20$", changelog, re.MULTILINE)
    assert changelog.index("## v0.4.4 - 2026-06-20") < changelog.index("## v0.4.3")


def test_pyproject_has_pypi_distribution_metadata() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["version"] == "0.4.4"
    urls = project["urls"]
    assert urls["Repository"] == "https://github.com/kadubon/percolation-inversion-compiler"
    assert urls["DOI"] == "https://doi.org/10.5281/zenodo.20569166"
    for key in ["Homepage", "Documentation", "Issues", "Changelog", "Works"]:
        assert urls[key].startswith("https://")
    keywords = set(project["keywords"])
    for keyword in [
        "ai-agents",
        "agent-runtime",
        "evidence-routing",
        "verifier-routing",
        "residual-ledger",
        "sybil-resistance",
        "abstraction-liquidity",
        "ecpt",
        "sqot",
        "alt",
    ]:
        assert keyword in keywords


def test_pypi_publish_workflow_uses_trusted_publishing() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "pypi-publish.yml"
    text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["publish"]
    assert job["environment"] == "pypi"
    assert job["permissions"]["id-token"] == "write"
    assert "PYPI_API_TOKEN" not in text
    assert "password:" not in text.lower()
    uses = [step.get("uses", "") for step in job["steps"] if isinstance(step, dict)]
    assert not any("gh-action-pypi-publish" in use for use in uses)
    runs = [step.get("run", "") for step in job["steps"] if isinstance(step, dict)]
    assert any("twine check" in run for run in runs)
    assert any("uv publish --trusted-publishing always" in run for run in runs)


def test_gitignore_blocks_generated_and_secret_paths() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in [
        ".venv/",
        "__pycache__/",
        ".env",
        "*.pem",
        "*.tex",
        "*.pdf",
        "*.safetensors",
        "*.onnx",
        "*.whl",
        "node_modules/",
        "vendor/",
        ".ipynb_checkpoints/",
    ]:
        assert pattern in gitignore


def test_publishable_files_have_no_local_paths_or_secret_assignments() -> None:
    assert _publish_safety_main() == 0


def test_readme_does_not_contain_user_local_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"C:\\Users\\", readme, re.IGNORECASE)


def test_docs_explain_pip_clone_boundary_and_uv_install() -> None:
    required = [
        "python -m pip install percolation-inversion-compiler",
        "git clone https://github.com/kadubon/percolation-inversion-compiler.git",
        'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "uv sync --all-extras --dev",
    ]
    for relative in [
        "README.md",
        "AGENTS.md",
        "docs/01-quickstart.md",
        "docs/for-agents.md",
        "docs/pypi-distribution.md",
        "docs/cli-reference.md",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in required:
            assert phrase in text
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "The PyPI package is intended for practical agent output checking" in readme
    assert "Clone the repository for canonical TeX audits" in readme


def test_release_checklist_warns_against_local_dist_star_publish() -> None:
    text = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    assert "dist\\percolation_inversion_compiler-0.4.4-py3-none-any.whl" in text
    assert "dist\\percolation_inversion_compiler-0.4.4.tar.gz" in text
    assert "do not publish\n  local `dist/*`" in text
    assert "clean GitHub Trusted Publishing workflow" in text
    assert "production doctor\n  run without provenance is expected to fail closed" in text


def test_readme_frontmatter_explains_scientific_agent_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in [
        "certificate compiler",
        "proof obligations",
        "residual ledgers",
        "typed trace normal forms",
        "frontier extraction",
        "AI agent integration",
        "pic doctor",
        "protocol-relative ASI-proxy phase-control",
        "registry is metadata, not evidence",
    ]:
        assert phrase in readme


def test_agent_docs_exist_and_avoid_local_paths() -> None:
    for relative in [
        "docs/agent-integration.md",
        "docs/tutorial.md",
        "docs/architecture.md",
        "docs/mathematical-contracts.md",
        "docs/porting.md",
        "docs/external-obligations.md",
        "docs/production-readiness.md",
        "docs/provenance-and-sbom.md",
        "docs/verifier-sdk.md",
        "docs/verifier-threat-model.md",
        "docs/runtime.md",
        "docs/runtime-service.md",
        "docs/ecpt-acceleration-score.md",
        "docs/runtime-closed-loop.md",
        "docs/collective-phase-runtime.md",
        "docs/runtime-executor.md",
        "docs/runtime-store.md",
        "docs/edge-relation-verifiers.md",
        "docs/resource-matched-benchmarks.md",
        "docs/packet-promotion.md",
        "docs/acceleration-certificates.md",
        "docs/release-checklist.md",
        "docs/pypi-distribution.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "C:\\Users\\" not in text
        assert "ExternalProofObligation" in text or "certificate" in text.lower()


def test_examples_are_portable_and_secret_free() -> None:
    json_paths = [
        *sorted((ROOT / "examples").glob("*.json")),
        *sorted((ROOT / "src" / "percolation_inversion_compiler" / "data").rglob("*.json")),
    ]
    for path in json_paths:
        text = path.read_text(encoding="utf-8")
        assert "C:\\Users\\" not in text
        assert "Desktop\\Downloads" not in text
        assert "api_key" not in text.lower()
        assert "private_key" not in text.lower()


def test_public_docs_keep_asi_claims_protocol_relative() -> None:
    docs = [
        ROOT / "README.md",
        ROOT / "docs" / "agent-integration.md",
        ROOT / "docs" / "external-obligations.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    assert "protocol-relative ASI-proxy phase-control" in combined
    assert "snapshot" in (ROOT / "README.md").read_text(encoding="utf-8").lower()
    forbidden = [
        "ASI has been achieved",
        "proves ASI",
        "automatic proof of unobserved ASI",
    ]
    for phrase in forbidden:
        assert phrase not in combined
