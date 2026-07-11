from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import load_data, load_jsonl_records

runner = CliRunner()


def test_bounded_loader_rejects_yaml_alias_and_negative_zero(tmp_path: Path) -> None:
    alias = tmp_path / "alias.yaml"
    alias.write_text("base: &base {value: 1}\ncopy: *base\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aliases"):
        load_data(alias)

    for value in ("-0", "-0.0"):
        negative_zero = tmp_path / f"negative-{value.replace('.', '-')}.yaml"
        negative_zero.write_text(f"value: {value}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="negative zero"):
            load_data(negative_zero)


def test_bounded_loader_rejects_depth_before_json_parse(tmp_path: Path) -> None:
    deep = tmp_path / "deep.json"
    deep.write_text('{"value":' * 66 + "0" + "}" * 66, encoding="utf-8")
    with pytest.raises(ValueError, match="nesting depth"):
        load_data(deep)

    jsonl = tmp_path / "deep.jsonl"
    jsonl.write_text(deep.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="nesting depth"):
        load_jsonl_records(jsonl)


def test_bounded_loader_rejects_byte_limit(tmp_path: Path) -> None:
    source = tmp_path / "large.json"
    source.write_text('{"value":"0123456789"}', encoding="utf-8")
    with pytest.raises(ValueError, match="byte limit"):
        load_data(source, max_bytes=10)
    with pytest.raises(ValueError, match="item limit"):
        load_data(source, max_items=1)


def test_runtime_cli_rejects_numeric_strings(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "run_id": "baseline:invalid",
                "initial_state_id": "state:invalid",
                "resource_units": "1",
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "runtime",
            "certify-acceleration",
            "--baseline",
            str(baseline),
            "--candidate",
            "examples/runtime_acceleration/candidate.json",
        ],
    )
    assert result.exit_code != 0
