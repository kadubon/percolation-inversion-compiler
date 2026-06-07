from __future__ import annotations

import importlib.util
import re
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
    assert data["version"] == "0.3.2"
    assert data["repository-code"] == "https://github.com/kadubon/percolation-inversion-compiler"
    assert "OWNER/" not in data["repository-code"]
    assert "10.5281/zenodo.20535654" in dois
    assert "10.5281/zenodo.20545356" in dois
    assert "10.5281/zenodo.20554083" in dois
    assert "10.5281/zenodo.20526451" in dois


def test_gitignore_blocks_generated_and_secret_paths() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in [".venv/", "__pycache__/", ".env", "*.pem", "*.tex", "*.pdf"]:
        assert pattern in gitignore


def test_publishable_files_have_no_local_paths_or_secret_assignments() -> None:
    assert _publish_safety_main() == 0


def test_readme_does_not_contain_user_local_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"C:\\Users\\", readme, re.IGNORECASE)


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
