from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_v060_version_metadata_is_consistent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    init_text = (ROOT / "src/percolation_inversion_compiler/__init__.py").read_text(
        encoding="utf-8"
    )
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert pyproject["project"]["version"] == "0.7.0"
    assert citation["version"] == "0.7.0"
    assert re.search(r"^__version__\s*=\s*[\"']0\.7\.0[\"']", init_text, re.MULTILINE)
    assert re.search(r"^## v0\.7\.0 - 2026-07-01$", changelog, re.MULTILINE)


def test_readme_keeps_core_commands_before_optional_sidecars() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    core = readme.index("## For AI Agents")
    sidecars = readme.index("## Optional Sidecars")
    assert core < sidecars
    assert "They do not gate the main workflow" in readme
    assert "pic agent check --compact" in readme[:sidecars]


def test_changelog_mentions_optional_sidecars() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    entry = changelog.split("## v0.4.3", maxsplit=1)[0]
    assert "optional adoption sidecars" in entry
    assert "without gating `pic agent check`" in entry
    assert "do not imply `settled=true`" in entry


def test_v044_schema_commands_export() -> None:
    for schema_name in [
        "OperatorAdoptionPacket",
        "AgentToOperatorRequest",
        "AgentCommandInvocation",
        "AgentAutonomyAuditReport",
        "CanonicalImplementationReadinessReport",
        "CanonicalTheorySnapshotSummary",
        "PhaseBenchmarkSuiteReport",
        "PacketExchangeEnvelope",
        "PhaseDashboardReport",
    ]:
        assert schema_by_type(schema_name)["title"] == schema_name
        result = runner.invoke(app, ["schema", "--type", schema_name])
        assert result.exit_code == 0
        assert json.loads(result.output)["title"] == schema_name


def test_negative_phrase_lint_allows_only_negated_claims() -> None:
    checked_paths = [
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "docs/operator-adoption.md",
        ROOT / "docs/agent-to-operator-request.md",
        ROOT / "docs/contracts/operator-adoption-sidecar-contract.md",
        ROOT / "docs/benchmarks/phase-benchmark-suite.md",
        ROOT / "docs/phase-dashboard.md",
        ROOT / "docs/i18n-and-portability.md",
        ROOT / "docs/canonical-implementation-readiness.md",
    ]
    forbidden = [
        "proves real ASI",
        "guarantees ASI",
        "proves physical truth",
        "oracle truth guaranteed",
        "safe autonomous execution",
        "execute safe_commands automatically",
        "accepted means settled",
        "workflow_usable means settled",
        "identity readiness means settled",
        "adoption approval means settled",
        "operator approval is required for phase plan",
        "operator approval is required for agent check",
    ]
    allowed_prefixes = ("does not ", "do not ", "not ", "cannot ")
    for path in checked_paths:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            start = 0
            lowered = phrase.lower()
            while True:
                index = text.find(lowered, start)
                if index == -1:
                    break
                context = text[max(0, index - 40) : index]
                assert any(prefix in context for prefix in allowed_prefixes), (path, phrase)
                start = index + len(lowered)
