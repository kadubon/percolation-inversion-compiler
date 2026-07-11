from __future__ import annotations

import base64
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from percolation_inversion_compiler.operation import (
    OperationAdapterKind,
    OperationAdapterManifest,
    OperationDispatchReceipt,
    OperationRiskClass,
    OperationTrustPolicy,
    OperationVerifierReport,
    adapter_manifest_digest,
    build_operation_plan,
    canonical_json_bytes,
    check_operation_adapter,
    dispatch_operation,
    preflight_operation,
    reconcile_operation_replay,
    sign_operation_approval,
    verify_operation_outcome,
)


def _times() -> tuple[str, str, datetime]:
    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    issued = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    expires = (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    return issued, expires, now


def _key(seed_byte: int) -> tuple[str, str]:
    seed = bytes([seed_byte]) * 32
    private = Ed25519PrivateKey.from_private_bytes(seed)
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(seed).decode(), base64.b64encode(public).decode()


def _manifest(tmp_path: Path, *, sandboxed: bool = True) -> OperationAdapterManifest:
    executable = Path(sys.executable).resolve()
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    platform = (
        "windows"
        if sys.platform.startswith("win")
        else "macos"
        if sys.platform == "darwin"
        else "linux"
    )
    return OperationAdapterManifest(
        manifest_id="process:python-version",
        adapter_kind=OperationAdapterKind.PROCESS,
        risk_class=OperationRiskClass.READ_ONLY,
        executable_path=str(executable),
        executable_sha256_by_platform={platform: digest},
        fixed_argv_prefix=["--version"],
        fixed_cwd=str(tmp_path),
        external_sandbox_attested=sandboxed,
    )


def test_process_operation_is_explicit_digest_bound_and_replay_safe(tmp_path: Path) -> None:
    issued, expires, now = _times()
    manifest = _manifest(tmp_path)
    plan = build_operation_plan(
        manifest,
        plan_id="plan:python-version",
        expires_at=expires,
        nonce="nonce:python-version",
        idempotency_key="idempotency:python-version",
        scope=["process:read-version"],
    )
    policy = OperationTrustPolicy(
        read_only_enabled=True,
        allowed_adapter_ids=[manifest.manifest_id],
    )
    report = preflight_operation(plan, [], policy, reference_time=now)
    assert report.dispatch_ready
    receipt, ledger = dispatch_operation(plan, report, replay_root=tmp_path / "replay")
    assert receipt.accepted
    assert receipt.provider_called
    assert receipt.physical_outcome_proven is False
    assert receipt.physical_outcome_verified is False
    assert ledger.dispatch_uncertain is False
    with pytest.raises(FileExistsError):
        dispatch_operation(plan, report, replay_root=tmp_path / "replay")

    changed = plan.model_copy(update={"idempotency_key": "modified"})
    assert not preflight_operation(changed, [], policy, reference_time=now).plan_valid
    assert issued


def test_unsandboxed_process_requires_two_distinct_approvals(tmp_path: Path) -> None:
    issued, expires, now = _times()
    manifest = _manifest(tmp_path, sandboxed=False).model_copy(
        update={
            "rollback_contract_ref": "rollback:safe-abort",
            "hazard_contract_ref": "hazard:bounded",
            "verifier_contract_ref": "verifier:independent",
        }
    )
    plan = build_operation_plan(
        manifest,
        plan_id="plan:two-person",
        expires_at=expires,
        nonce="nonce:two-person",
        idempotency_key="idempotency:two-person",
        scope=["process:read-version"],
    )
    seed_a, public_a = _key(1)
    seed_b, public_b = _key(2)
    environment = {"KEY_A": seed_a, "KEY_B": seed_b}
    approval_a = sign_operation_approval(
        plan,
        key_id="key-a",
        signer_id="alice",
        private_key_env="KEY_A",
        issued_at=issued,
        expires_at=expires,
        scope=plan.scope,
        environ=environment,
    )
    approval_b = sign_operation_approval(
        plan,
        key_id="key-b",
        signer_id="bob",
        private_key_env="KEY_B",
        issued_at=issued,
        expires_at=expires,
        scope=plan.scope,
        environ=environment,
    )
    policy = OperationTrustPolicy(
        public_keys_b64={"key-a": public_a, "key-b": public_b},
        allowed_adapter_ids=[manifest.manifest_id],
    )
    one = preflight_operation(plan, [approval_a], policy, reference_time=now)
    duplicate = preflight_operation(
        plan,
        [approval_a, approval_a.model_copy(update={"approval_id": "approval:duplicate"})],
        policy,
        reference_time=now,
    )
    same_key_other_signer = sign_operation_approval(
        plan,
        key_id="key-a",
        signer_id="bob",
        private_key_env="KEY_A",
        issued_at=issued,
        expires_at=expires,
        scope=plan.scope,
        environ=environment,
    )
    reused_key = preflight_operation(
        plan,
        [approval_a, same_key_other_signer],
        policy,
        reference_time=now,
    )
    two = preflight_operation(plan, [approval_a, approval_b], policy, reference_time=now)
    assert not one.approvals_valid
    assert not duplicate.approvals_valid
    assert not reused_key.approvals_valid
    assert two.dispatch_ready
    assert two.accepted_key_ids == ["key-a", "key-b"]


def test_https_private_address_and_script_launcher_fail_closed(tmp_path: Path) -> None:
    https = OperationAdapterManifest(
        manifest_id="https:private",
        adapter_kind=OperationAdapterKind.HTTPS,
        risk_class=OperationRiskClass.READ_ONLY,
        fixed_origin="https://127.0.0.1",
        path_template="/status",
        method="GET",
    )
    _, expires, now = _times()
    plan = build_operation_plan(
        https,
        plan_id="plan:private",
        expires_at=expires,
        nonce="nonce:private",
        idempotency_key="idempotency:private",
    )
    report = preflight_operation(
        plan,
        [],
        OperationTrustPolicy(read_only_enabled=True),
        reference_time=now,
    )
    assert not report.dispatch_ready
    assert any("prohibited address" in blocker for blocker in report.blockers)

    fake_script = tmp_path / "unsafe.cmd"
    fake_script.write_text("echo unsafe", encoding="utf-8")
    script = OperationAdapterManifest(
        manifest_id="process:script",
        adapter_kind=OperationAdapterKind.PROCESS,
        risk_class=OperationRiskClass.READ_ONLY,
        executable_path=str(fake_script),
        fixed_cwd=str(tmp_path),
    )
    checked = check_operation_adapter(script)
    assert not checked["accepted"]
    assert "script launchers are forbidden" in checked["blockers"]


def test_operation_cli_models_are_json_serializable(tmp_path: Path) -> None:
    _, expires, _ = _times()
    plan = build_operation_plan(
        _manifest(tmp_path),
        plan_id="plan:json",
        expires_at=expires,
        nonce="nonce:json",
        idempotency_key="idempotency:json",
    )
    assert json.loads(plan.model_dump_json())["settled"] is False


def test_operation_contract_digest_matches_canonical_pack() -> None:
    contract = json.loads(
        (Path(__file__).parents[1] / "contracts/v1.1/pic-cross-language-contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert hashlib.sha256(canonical_json_bytes(contract)).hexdigest() == (
        "a4057f7437f17bd3a1d87403de16ee25a4a5b6ae9f2d979fa55e2e5b1a174c36"
    )
    case = contract["operation_canonical_case"]
    manifest = OperationAdapterManifest.model_validate(case["adapter_manifest"])
    request = case["plan_request"]
    plan = build_operation_plan(manifest, **request)
    assert adapter_manifest_digest(manifest) == case["adapter_digest"]
    assert plan.plan_digest == case["plan_digest"]

    signature_case = contract["approval_signature_case"]
    approval = sign_operation_approval(
        plan,
        key_id="fixture-key",
        signer_id="fixture-signer",
        private_key_env="FIXTURE_KEY",
        issued_at="2029-01-01T00:00:00Z",
        expires_at="2029-12-31T00:00:00Z",
        scope=["read:object"],
        environ={"FIXTURE_KEY": signature_case["fixture_only_private_seed_b64"]},
    )
    assert approval.model_dump(mode="json") == signature_case["approval"]


def test_operation_canonical_domain_and_signing_fail_closed(tmp_path: Path) -> None:
    _, expires, _ = _times()
    with pytest.raises(ValueError, match="floating point"):
        canonical_json_bytes({"unsafe": 0.5})
    with pytest.raises(ValueError, match="keys must be strings"):
        canonical_json_bytes({1: "value"})
    with pytest.raises(ValueError, match="unsupported canonical"):
        canonical_json_bytes({"unsafe": {1, 2}})
    with pytest.raises(ValueError, match="safe integers"):
        canonical_json_bytes({"unsafe": 9_007_199_254_740_992})
    assert canonical_json_bytes({"\ue000": 2, "\U00010000": 1}) == (
        '{"\U00010000":1,"\ue000":2}'.encode()
    )

    plan = build_operation_plan(
        _manifest(tmp_path),
        plan_id="plan:signing-errors",
        expires_at=expires,
        nonce="nonce:signing-errors",
        idempotency_key="idempotency:signing-errors",
    )
    with pytest.raises(ValueError, match="missing private key"):
        sign_operation_approval(
            plan,
            key_id="missing",
            signer_id="missing",
            private_key_env="MISSING",
            issued_at="2026-07-10T11:59:00Z",
            expires_at=expires,
            scope=[],
            environ={},
        )
    with pytest.raises(ValueError, match="32 bytes"):
        sign_operation_approval(
            plan,
            key_id="short",
            signer_id="short",
            private_key_env="SHORT",
            issued_at="2026-07-10T11:59:00Z",
            expires_at=expires,
            scope=[],
            environ={"SHORT": base64.b64encode(b"short").decode()},
        )


def test_operation_dispatch_failure_is_uncertain_and_reconciled(tmp_path: Path) -> None:
    _, expires, now = _times()
    manifest = _manifest(tmp_path).model_copy(update={"argv_patterns": ["[a-z]+"]})
    plan = build_operation_plan(
        manifest,
        plan_id="plan:bad-argument",
        arguments=["BAD-1"],
        expires_at=expires,
        nonce="nonce:bad-argument",
        idempotency_key="idempotency:bad-argument",
    )
    preflight = preflight_operation(
        plan,
        [],
        OperationTrustPolicy(read_only_enabled=True),
        reference_time=now,
    )
    receipt, ledger = dispatch_operation(plan, preflight, replay_root=tmp_path / "replay")
    assert receipt.dispatch_status == "dispatch_uncertain"
    assert not receipt.provider_called
    assert ledger.dispatch_uncertain
    reconciled = reconcile_operation_replay(tmp_path / "replay")
    assert reconciled[0].dispatch_uncertain

    body_plan = build_operation_plan(
        _manifest(tmp_path),
        plan_id="plan:body",
        body=b"expected",
        expires_at=expires,
        nonce="nonce:body",
        idempotency_key="idempotency:body",
    )
    body_preflight = preflight_operation(
        body_plan,
        [],
        OperationTrustPolicy(read_only_enabled=True),
        reference_time=now,
    )
    with pytest.raises(ValueError, match="body digest mismatch"):
        dispatch_operation(
            body_plan,
            body_preflight,
            replay_root=tmp_path / "body-replay",
            body=b"modified",
        )


def test_operation_verifier_signature_scope_and_window(tmp_path: Path) -> None:
    seed_b64, public_b64 = _key(7)
    receipt = OperationDispatchReceipt(
        receipt_id="receipt:verify",
        plan_id="plan:verify",
        plan_digest="a" * 64,
        adapter_id="adapter:verify",
        dispatch_status="completed",
        provider_called=True,
        started_at="2026-07-10T12:00:00Z",
        completed_at="2026-07-10T12:00:01Z",
        idempotency_key="idempotency:verify",
        nonce="nonce:verify",
        accepted=True,
    )
    unsigned = {
        "verifier_report_id": "verifier-report:verify",
        "receipt_id": receipt.receipt_id,
        "plan_digest": receipt.plan_digest,
        "verifier_key_id": "verifier-key",
        "verifier_id": "verifier:independent",
        "scope": ["outcome:verify"],
        "observation_window_start": "2026-07-10T12:00:00Z",
        "observation_window_end": "2026-07-10T12:05:00Z",
        "outcome_digest": "b" * 64,
        "outcome_accepted": True,
    }
    signer = Ed25519PrivateKey.from_private_bytes(base64.b64decode(seed_b64))
    verifier = OperationVerifierReport(
        **unsigned,
        signature_b64=base64.b64encode(signer.sign(canonical_json_bytes(unsigned))).decode(),
    )
    policy = OperationTrustPolicy(verifier_public_keys_b64={"verifier-key": public_b64})
    accepted = verify_operation_outcome(receipt, verifier, policy)
    assert accepted.physical_outcome_verified
    assert accepted.physical_outcome_proven is False

    invalid = verify_operation_outcome(
        receipt,
        verifier.model_copy(
            update={
                "receipt_id": "receipt:other",
                "observation_window_end": "invalid",
                "signature_b64": base64.b64encode(b"invalid").decode(),
            }
        ),
        policy,
    )
    assert not invalid.accepted
    assert len(invalid.blockers) == 3

    reused_approval_key = verify_operation_outcome(
        receipt,
        verifier,
        OperationTrustPolicy(
            public_keys_b64={"approval-key": public_b64},
            verifier_public_keys_b64={"verifier-key": public_b64},
        ),
    )
    assert not reused_approval_key.signature_valid


def test_process_output_limit_is_enforced_while_streaming(tmp_path: Path) -> None:
    _, expires, now = _times()
    manifest = _manifest(tmp_path).model_copy(update={"max_response_bytes": 1})
    plan = build_operation_plan(
        manifest,
        plan_id="plan:bounded-output",
        expires_at=expires,
        nonce="nonce:bounded-output",
        idempotency_key="idempotency:bounded-output",
    )
    preflight = preflight_operation(
        plan,
        [],
        OperationTrustPolicy(read_only_enabled=True),
        reference_time=now,
    )
    receipt, _ = dispatch_operation(plan, preflight, replay_root=tmp_path / "bounded-replay")
    assert receipt.dispatch_status == "dispatch_uncertain"
    assert receipt.blockers == ["process output exceeds byte limit"]


def test_cgnat_https_origin_is_not_public() -> None:
    _, expires, now = _times()
    manifest = OperationAdapterManifest(
        manifest_id="https:cgnat",
        adapter_kind=OperationAdapterKind.HTTPS,
        risk_class=OperationRiskClass.READ_ONLY,
        fixed_origin="https://100.64.0.1",
        path_template="/status",
        method="GET",
    )
    plan = build_operation_plan(
        manifest,
        plan_id="plan:cgnat",
        expires_at=expires,
        nonce="nonce:cgnat",
        idempotency_key="idempotency:cgnat",
    )
    report = preflight_operation(
        plan,
        [],
        OperationTrustPolicy(read_only_enabled=True),
        reference_time=now,
    )
    assert "HTTPS origin resolves to a prohibited address" in report.blockers


def test_operation_adapter_rejects_invalid_limits_and_inline_code(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path).model_copy(
        update={
            "timeout_ms": 0,
            "max_response_bytes": 0,
            "fixed_argv_prefix": ["-c", "print('unsafe')"],
        }
    )
    report = check_operation_adapter(manifest)
    assert not report["accepted"]
    assert "invalid resource limit" in report["blockers"]
    assert "invalid response limit" in report["blockers"]
    assert "inline interpreter commands are forbidden" in report["blockers"]

    non_file = OperationAdapterManifest(
        manifest_id="process:non-file",
        adapter_kind=OperationAdapterKind.PROCESS,
        risk_class=OperationRiskClass.READ_ONLY,
        executable_path=str(tmp_path),
        executable_sha256_by_platform={"windows": "0" * 64},
        fixed_cwd=str(tmp_path / "missing-cwd"),
    )
    non_file_report = check_operation_adapter(non_file)
    assert "process executable is not a regular file" in non_file_report["blockers"]
    assert "process fixed cwd does not exist" in non_file_report["blockers"]


def test_operation_preflight_reports_all_missing_dispatch_requirements(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expires_at"):
        build_operation_plan(
            _manifest(tmp_path),
            plan_id="plan:invalid-expiry",
            expires_at="invalid",
            nonce="nonce:invalid-expiry",
            idempotency_key="idempotency:invalid-expiry",
        )

    manifest = _manifest(tmp_path, sandboxed=False).model_copy(
        update={"secret_env_names": ["OPERATION_CREDENTIAL"]}
    )
    plan = build_operation_plan(
        manifest,
        plan_id="plan:blocked",
        expires_at="2026-07-10T11:00:00Z",
        nonce="nonce:blocked",
        idempotency_key="idempotency:blocked",
    )
    report = preflight_operation(
        plan,
        [],
        OperationTrustPolicy(allowed_adapter_ids=["other-adapter"]),
        reference_time=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        environ={},
    )
    assert not report.dispatch_ready
    assert {
        "adapter is not allowlisted",
        "hazard contract is required",
        "insufficient distinct valid approvals",
        "plan expired or expiry invalid",
        "required operation secret is unavailable",
        "rollback or safe-abort contract is required",
        "verifier contract is required",
    }.issubset(report.blockers)
    with pytest.raises(ValueError, match="not dispatch-ready"):
        dispatch_operation(plan, report, replay_root=tmp_path / "blocked-replay")
    assert reconcile_operation_replay(tmp_path / "missing-replay") == []
