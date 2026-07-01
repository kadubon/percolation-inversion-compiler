from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.interop import trace_normal_form_report

runner = CliRunner()


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _assert_compact(payload: dict[str, object], source_schema: str) -> None:
    assert payload["schema_version"] == "pic.compact_report.v1"
    assert payload["source_schema_version"] == source_schema
    assert "ok" in payload
    assert "settled" in payload
    assert "blockers" in payload
    assert "residual_count" in payload
    assert "next_safe_action" in payload
    assert "non_claims" in payload


def test_interop_compact_cli_outputs(tmp_path: Path) -> None:
    descriptor = _write(
        tmp_path / "descriptor.json",
        {
            "auth_scope": ["read"],
            "descriptor_version": "1",
            "egress_policy": "none",
            "server_id": "srv",
            "server_trust_status": "trusted",
            "side_effect_class": "read_only",
            "tool_name": "read",
        },
    )
    call = _write(
        tmp_path / "call.json",
        {
            "arguments": {"path": "README.md"},
            "canonical_tool_name": "read",
            "output_redaction_policy": "none",
            "trace_logging_enabled": True,
        },
    )
    handoff = _write(
        tmp_path / "handoff.json",
        {
            "agent_card_ref": "agent:srv",
            "declared_authority": {"scope": "read"},
            "handoff_scope": "read-only",
            "idempotency_key": "idem-1",
            "replay_nonce": "nonce-1",
            "task_schema": {"type": "object"},
        },
    )
    trace = _write(
        tmp_path / "trace.json",
        trace_normal_form_report(
            {
                "fixture_mode": True,
                "side_effect_policy": "dry_run_only",
                "trace_id": "trace:compact",
                "steps": [{"step_id": "s1", "tool": "read"}],
            }
        ),
    )

    mcp = runner.invoke(
        app,
        [
            "mcp",
            "invocation-preflight",
            "--descriptor",
            str(descriptor),
            "--call",
            str(call),
            "--compact",
        ],
    )
    a2a = runner.invoke(
        app,
        ["a2a", "handoff-check", "--handoff", str(handoff), "--compact"],
    )
    trc = runner.invoke(
        app,
        ["trc", "operation-gate", "--trace", str(trace), "--compact"],
    )

    assert mcp.exit_code == 0, mcp.output
    assert a2a.exit_code == 0, a2a.output
    assert trc.exit_code == 0, trc.output
    _assert_compact(json.loads(mcp.output), "pic.mcp_tool_invocation_preflight.v1")
    _assert_compact(json.loads(a2a.output), "pic.a2a_task_handoff_report.v1")
    _assert_compact(json.loads(trc.output), "pic.trc_operation_gate_report.v1")
