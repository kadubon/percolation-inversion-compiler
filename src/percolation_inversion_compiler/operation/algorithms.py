"""Fail-closed planning, approval, dispatch, and verification for operations."""

from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess  # nosec B404
import sys
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from jsonschema import ValidationError as JsonSchemaError
from jsonschema import validate as validate_json_schema

from percolation_inversion_compiler.core.time import parse_utc_datetime
from percolation_inversion_compiler.operation.records import (
    OperationAdapterKind,
    OperationAdapterManifest,
    OperationApproval,
    OperationDispatchReceipt,
    OperationPlan,
    OperationPreflightReport,
    OperationReplayLedger,
    OperationRiskClass,
    OperationTrustPolicy,
    OperationVerificationReport,
    OperationVerifierReport,
)

OPERATION_NON_CLAIMS = [
    "dispatch receipt is not physical outcome proof",
    "operation approval does not grant legal authority beyond its signed scope",
    "process adapter does not claim containment without external sandbox evidence",
    "physical_outcome_proven remains false",
]

_FORBIDDEN_PROCESS_SUFFIXES = {".bat", ".cmd", ".ps1"}


def canonical_json_bytes(value: Any) -> bytes:
    """Return RFC 8785-compatible bytes for the restricted operation payload domain."""

    _validate_canonical_domain(value)
    return _canonical_json_text(value).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def adapter_manifest_digest(manifest: OperationAdapterManifest) -> str:
    return digest_json(manifest.model_dump(mode="json"))


def operation_plan_digest(plan: OperationPlan) -> str:
    return digest_json(plan.model_dump(mode="json", exclude={"plan_digest", "settled"}))


def check_operation_adapter(manifest: OperationAdapterManifest) -> dict[str, Any]:
    blockers: list[str] = []
    if manifest.timeout_ms <= 0 or manifest.max_request_bytes <= 0:
        blockers.append("invalid resource limit")
    if manifest.max_response_bytes <= 0:
        blockers.append("invalid response limit")
    if manifest.adapter_kind is OperationAdapterKind.HTTPS:
        blockers.extend(_https_manifest_blockers(manifest))
    elif manifest.adapter_kind is OperationAdapterKind.PROCESS:
        blockers.extend(_process_manifest_blockers(manifest))
    return {
        "accepted": not blockers,
        "adapter_digest": adapter_manifest_digest(manifest),
        "adapter_id": manifest.manifest_id,
        "blockers": sorted(set(blockers)),
        "operation_ready": False,
        "provider_dispatch_ready": False,
        "physical_dispatch_ready": False,
        "settled": False,
    }


def build_operation_plan(
    manifest: OperationAdapterManifest,
    *,
    plan_id: str,
    arguments: list[str] | None = None,
    path_parameters: Mapping[str, str] | None = None,
    body: bytes | None = None,
    resource_limits: Mapping[str, int] | None = None,
    scope: list[str] | None = None,
    expires_at: str,
    nonce: str,
    idempotency_key: str,
) -> OperationPlan:
    """Bind all operation-relevant inputs into a deterministic plan digest."""

    if parse_utc_datetime(expires_at) is None:
        raise ValueError("expires_at must be a timezone-qualified ISO-8601 timestamp")
    plan = OperationPlan(
        plan_id=plan_id,
        adapter_manifest=manifest,
        adapter_digest=adapter_manifest_digest(manifest),
        arguments=list(arguments or []),
        path_parameters=dict(sorted((path_parameters or {}).items())),
        body_sha256=hashlib.sha256(body).hexdigest() if body is not None else None,
        resource_limits=dict(sorted((resource_limits or {}).items())),
        scope=sorted(set(scope or [])),
        risk_class=manifest.risk_class,
        expires_at=expires_at,
        nonce=nonce,
        idempotency_key=idempotency_key,
        rollback_contract_ref=manifest.rollback_contract_ref,
        hazard_contract_ref=manifest.hazard_contract_ref,
        verifier_contract_ref=manifest.verifier_contract_ref,
        secret_env_names=sorted(set(manifest.secret_env_names)),
    )
    return plan.model_copy(update={"plan_digest": operation_plan_digest(plan)})


def sign_operation_approval(
    plan: OperationPlan,
    *,
    key_id: str,
    signer_id: str,
    private_key_env: str,
    issued_at: str,
    expires_at: str,
    scope: list[str],
    environ: Mapping[str, str] | None = None,
) -> OperationApproval:
    """Sign one use of a plan using an environment-resolved raw Ed25519 seed."""

    environment = environ or os.environ
    encoded_key = environment.get(private_key_env)
    if not encoded_key:
        raise ValueError(f"missing private key environment variable: {private_key_env}")
    signing_handle = _ed25519_private_key(encoded_key)
    unsigned = {
        "approval_id": f"approval:{plan.plan_id}:{key_id}",
        "expires_at": expires_at,
        "issued_at": issued_at,
        "key_id": key_id,
        "max_uses": 1,
        "nonce": plan.nonce,
        "plan_digest": plan.plan_digest,
        "scope": sorted(set(scope)),
        "signer_id": signer_id,
    }
    signature = signing_handle.sign(canonical_json_bytes(unsigned))
    return OperationApproval(**unsigned, signature_b64=base64.b64encode(signature).decode("ascii"))


def preflight_operation(
    plan: OperationPlan,
    approvals: list[OperationApproval],
    trust_policy: OperationTrustPolicy,
    *,
    reference_time: datetime | None = None,
    environ: Mapping[str, str] | None = None,
) -> OperationPreflightReport:
    """Validate a parameter-bound plan at the dispatch-time boundary."""

    blockers: list[str] = []
    now = (reference_time or datetime.now(UTC)).astimezone(UTC)
    adapter_report = check_operation_adapter(plan.adapter_manifest)
    adapter_valid = adapter_report["accepted"] is True
    blockers.extend(str(item) for item in adapter_report["blockers"])
    if plan.adapter_manifest.adapter_kind is OperationAdapterKind.HTTPS:
        address_blockers = _https_origin_address_blockers(plan.adapter_manifest)
        blockers.extend(address_blockers)
        adapter_valid = adapter_valid and not address_blockers
    plan_valid = operation_plan_digest(plan) == plan.plan_digest
    plan_valid = (
        plan_valid and adapter_manifest_digest(plan.adapter_manifest) == plan.adapter_digest
    )
    if not plan_valid:
        blockers.append("plan or adapter digest mismatch")
    expiry = parse_utc_datetime(plan.expires_at)
    if expiry is None or expiry <= now:
        plan_valid = False
        blockers.append("plan expired or expiry invalid")
    if trust_policy.allowed_adapter_ids and (
        plan.adapter_manifest.manifest_id not in trust_policy.allowed_adapter_ids
    ):
        adapter_valid = False
        blockers.append("adapter is not allowlisted")
    effective_risk = _effective_risk(plan.adapter_manifest)
    required = _required_approval_count(effective_risk, trust_policy)
    accepted_approvals: list[OperationApproval] = []
    for approval in approvals:
        if _approval_valid(approval, plan, trust_policy, now):
            accepted_approvals.append(approval)
    signer_ids = sorted({approval.signer_id for approval in accepted_approvals})
    key_ids = sorted({approval.key_id for approval in accepted_approvals})
    approvals_valid = len(signer_ids) >= required and len(key_ids) >= required
    if not approvals_valid:
        blockers.append("insufficient distinct valid approvals")
    if effective_risk is not OperationRiskClass.READ_ONLY and not plan.rollback_contract_ref:
        blockers.append("rollback or safe-abort contract is required")
    if effective_risk is OperationRiskClass.IRREVERSIBLE_OR_PHYSICAL:
        if not plan.hazard_contract_ref:
            blockers.append("hazard contract is required")
        if not plan.verifier_contract_ref:
            blockers.append("verifier contract is required")
    environment = environ or os.environ
    secrets_available = all(environment.get(name) for name in plan.secret_env_names)
    if not secrets_available:
        blockers.append("required operation secret is unavailable")
    dispatch_ready = (
        adapter_valid and plan_valid and approvals_valid and secrets_available and not blockers
    )
    return OperationPreflightReport(
        report_id=f"operation-preflight:{plan.plan_id}",
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        effective_risk_class=effective_risk,
        required_approval_count=required,
        accepted_approval_ids=sorted(item.approval_id for item in accepted_approvals),
        accepted_key_ids=key_ids,
        accepted_signer_ids=signer_ids,
        adapter_valid=adapter_valid,
        plan_valid=plan_valid,
        approvals_valid=approvals_valid,
        secrets_available=secrets_available,
        dispatch_ready=dispatch_ready,
        operation_ready=dispatch_ready,
        provider_dispatch_ready=dispatch_ready,
        physical_dispatch_ready=(
            dispatch_ready and effective_risk is OperationRiskClass.IRREVERSIBLE_OR_PHYSICAL
        ),
        accepted=dispatch_ready,
        blockers=sorted(set(blockers)),
        non_claims=OPERATION_NON_CLAIMS,
    )


def dispatch_operation(
    plan: OperationPlan,
    preflight: OperationPreflightReport,
    *,
    replay_root: Path,
    body: bytes | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[OperationDispatchReceipt, OperationReplayLedger]:
    """Dispatch one preflighted plan exactly once at the local nonce boundary."""

    started = datetime.now(UTC)
    if not preflight.dispatch_ready or preflight.plan_digest != plan.plan_digest:
        raise ValueError("operation preflight is not dispatch-ready for this plan")
    if body is not None and hashlib.sha256(body).hexdigest() != plan.body_sha256:
        raise ValueError("operation body digest mismatch")
    nonce_path = _consume_nonce(replay_root, plan.nonce, plan.plan_digest)
    receipt = OperationDispatchReceipt(
        receipt_id=f"operation-receipt:{plan.plan_id}:{plan.idempotency_key}",
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        adapter_id=plan.adapter_manifest.manifest_id,
        dispatch_status="dispatch_uncertain",
        started_at=started.isoformat().replace("+00:00", "Z"),
        idempotency_key=plan.idempotency_key,
        nonce=plan.nonce,
    )
    try:
        if plan.adapter_manifest.adapter_kind is OperationAdapterKind.HTTPS:
            result = _dispatch_https(plan, body or b"", environ or os.environ)
        else:
            result = _dispatch_process(plan, environ or os.environ)
        completed = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        receipt = receipt.model_copy(
            update={
                **result,
                "completed_at": completed,
                "accepted": result.get("dispatch_status") == "completed",
            }
        )
        _finish_nonce(nonce_path, receipt)
    except Exception as error:
        receipt = receipt.model_copy(
            update={"blockers": [_redact_error(error, plan, environ or os.environ)]}
        )
        _finish_nonce(nonce_path, receipt)
    return receipt, OperationReplayLedger(
        ledger_id=f"operation-replay:{plan.plan_id}",
        root=str(replay_root.resolve()),
        nonce_digest=nonce_path.stem,
        status=receipt.dispatch_status,
        receipt_id=receipt.receipt_id,
        dispatch_uncertain=receipt.dispatch_status == "dispatch_uncertain",
    )


def verify_operation_outcome(
    receipt: OperationDispatchReceipt,
    verifier: OperationVerifierReport,
    trust_policy: OperationTrustPolicy,
) -> OperationVerificationReport:
    """Verify an independent signed outcome observation without proving physical truth."""

    blockers: list[str] = []
    signature_valid = _verifier_signature_valid(verifier, trust_policy)
    if not signature_valid:
        blockers.append("verifier signature invalid")
    scope_valid = (
        verifier.receipt_id == receipt.receipt_id and verifier.plan_digest == receipt.plan_digest
    )
    if not scope_valid:
        blockers.append("verifier scope does not match receipt")
    start = parse_utc_datetime(verifier.observation_window_start)
    end = parse_utc_datetime(verifier.observation_window_end)
    observation_valid = bool(start and end and start < end)
    if not observation_valid:
        blockers.append("observation window invalid")
    accepted = signature_valid and scope_valid and observation_valid and verifier.outcome_accepted
    return OperationVerificationReport(
        report_id=f"operation-verification:{receipt.receipt_id}",
        receipt_id=receipt.receipt_id,
        verifier_report_id=verifier.verifier_report_id,
        signature_valid=signature_valid,
        scope_valid=scope_valid,
        observation_window_valid=observation_valid,
        physical_outcome_proven=False,
        physical_outcome_verified=accepted,
        accepted=accepted,
        blockers=sorted(set(blockers)),
    )


def reconcile_operation_replay(replay_root: Path) -> list[OperationReplayLedger]:
    """List consumed nonces; pending entries remain dispatch-uncertain."""

    if not replay_root.exists():
        return []
    ledgers: list[OperationReplayLedger] = []
    for path in sorted(replay_root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        status = str(data.get("dispatch_status") or data.get("status") or "dispatch_uncertain")
        ledgers.append(
            OperationReplayLedger(
                ledger_id=f"operation-replay:{path.stem}",
                root=str(replay_root.resolve()),
                nonce_digest=path.stem,
                status=status,
                receipt_id=data.get("receipt_id"),
                dispatch_uncertain=status in {"pending", "dispatch_uncertain"},
            )
        )
    return ledgers


def _validate_canonical_domain(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            raise ValueError("operation signature integers must be IEEE-754 safe integers")
        return
    if isinstance(value, float):
        raise ValueError("operation signature payloads use integers, not floating point")
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("unpaired Unicode surrogate is not allowed")
        return
    if isinstance(value, list):
        for item in value:
            _validate_canonical_domain(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical object keys must be strings")
            _validate_canonical_domain(item)
        return
    raise ValueError(f"unsupported canonical payload type: {type(value).__name__}")


def _canonical_json_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json_text(item) for item in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: item[0].encode("utf-16-be"))
        return (
            "{"
            + ",".join(
                f"{json.dumps(key, ensure_ascii=False)}:{_canonical_json_text(item)}"
                for key, item in items
            )
            + "}"
        )
    raise ValueError(f"unsupported canonical payload type: {type(value).__name__}")


def _https_manifest_blockers(manifest: OperationAdapterManifest) -> list[str]:
    blockers: list[str] = []
    parsed = urlsplit(manifest.fixed_origin or "")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username not in {None, ""}
        or parsed.password not in {None, ""}
    ):
        blockers.append("HTTPS adapter requires a fixed credential-free HTTPS origin")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        blockers.append("fixed_origin must not contain path, query, or fragment")
    if not manifest.path_template or not manifest.path_template.startswith("/"):
        blockers.append("HTTPS adapter requires an absolute path template")
    if (manifest.method or "").upper() not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
        blockers.append("HTTPS method is unsupported")
    return blockers


def _https_origin_address_blockers(manifest: OperationAdapterManifest) -> list[str]:
    parsed = urlsplit(manifest.fixed_origin or "")
    try:
        addresses = {
            str(item[4][0])
            for item in socket.getaddrinfo(
                parsed.hostname or "",
                parsed.port or 443,
                type=socket.SOCK_STREAM,
            )
        }
    except OSError:
        return ["HTTPS origin DNS resolution failed"]
    if not addresses or any(not _public_ip(address) for address in addresses):
        return ["HTTPS origin resolves to a prohibited address"]
    return []


def _process_manifest_blockers(manifest: OperationAdapterManifest) -> list[str]:
    blockers: list[str] = []
    path = Path(manifest.executable_path or "")
    if not path.is_absolute():
        blockers.append("process executable must be an absolute path")
        return blockers
    if path.suffix.lower() in _FORBIDDEN_PROCESS_SUFFIXES:
        blockers.append("script launchers are forbidden")
    if any(
        item.lower() in {"-c", "-command", "-encodedcommand"} for item in manifest.fixed_argv_prefix
    ):
        blockers.append("inline interpreter commands are forbidden")
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        blockers.append("process executable does not exist")
        return blockers
    executable_is_file = resolved.is_file()
    if not executable_is_file:
        blockers.append("process executable is not a regular file")
    if _path_contains_symlink(path):
        blockers.append("process executable path contains a symlink")
    expected = manifest.executable_sha256_by_platform.get(_platform_key())
    if not expected or not executable_is_file or _sha256_path(resolved) != expected.lower():
        blockers.append("process executable digest mismatch")
    cwd = Path(manifest.fixed_cwd or "")
    if not manifest.fixed_cwd or not cwd.is_absolute():
        blockers.append("process adapter requires a fixed absolute cwd")
    else:
        try:
            resolved_cwd = cwd.resolve(strict=True)
        except OSError:
            blockers.append("process fixed cwd does not exist")
        else:
            if not resolved_cwd.is_dir():
                blockers.append("process fixed cwd is not a directory")
            if _path_contains_symlink(cwd):
                blockers.append("process fixed cwd path contains a symlink")
    return blockers


def _effective_risk(manifest: OperationAdapterManifest) -> OperationRiskClass:
    if (
        manifest.adapter_kind is OperationAdapterKind.PROCESS
        and not manifest.external_sandbox_attested
    ):
        return OperationRiskClass.IRREVERSIBLE_OR_PHYSICAL
    return manifest.risk_class


def _required_approval_count(
    risk: OperationRiskClass,
    trust_policy: OperationTrustPolicy,
) -> int:
    if risk is OperationRiskClass.READ_ONLY:
        return 0 if trust_policy.read_only_enabled else 1
    if risk is OperationRiskClass.REVERSIBLE_WRITE:
        return 1
    return 2


def _approval_valid(
    approval: OperationApproval,
    plan: OperationPlan,
    policy: OperationTrustPolicy,
    reference_time: datetime,
) -> bool:
    if (
        approval.plan_digest != plan.plan_digest
        or approval.nonce != plan.nonce
        or approval.max_uses != 1
        or not set(plan.scope).issubset(approval.scope)
    ):
        return False
    issued = parse_utc_datetime(approval.issued_at)
    expires = parse_utc_datetime(approval.expires_at)
    if issued is None or expires is None or issued > reference_time or expires <= reference_time:
        return False
    public = policy.public_keys_b64.get(approval.key_id)
    if not public:
        return False
    unsigned = approval.model_dump(mode="json", exclude={"signature_b64"})
    return _verify_ed25519(public, approval.signature_b64, canonical_json_bytes(unsigned))


def _verifier_signature_valid(
    verifier: OperationVerifierReport,
    policy: OperationTrustPolicy,
) -> bool:
    public = policy.verifier_public_keys_b64.get(verifier.verifier_key_id)
    if not public:
        return False
    if public in policy.public_keys_b64.values():
        return False
    unsigned = verifier.model_dump(mode="json", exclude={"signature_b64"})
    return _verify_ed25519(public, verifier.signature_b64, canonical_json_bytes(unsigned))


def _ed25519_private_key(encoded: str) -> Any:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != 32:
        raise ValueError("Ed25519 private key seed must be 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(raw)


def _verify_ed25519(public_b64: str, signature_b64: str, payload: bytes) -> bool:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64, validate=True))
        public.verify(base64.b64decode(signature_b64, validate=True), payload)
    except (InvalidSignature, ValueError):
        return False
    return True


def _consume_nonce(root: Path, nonce: str, plan_digest: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve(strict=True)
    digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    target = resolved_root / f"{digest}.json"
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"plan_digest": plan_digest, "status": "pending"}, stream, sort_keys=True)
    return target


def _finish_nonce(path: Path, receipt: OperationDispatchReceipt) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(receipt.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _dispatch_https(
    plan: OperationPlan,
    body: bytes,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    manifest = plan.adapter_manifest
    parsed = urlsplit(manifest.fixed_origin or "")
    host = parsed.hostname or ""
    port = parsed.port or 443
    addresses = sorted(
        {str(item[4][0]) for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    )
    if not addresses or any(not _public_ip(address) for address in addresses):
        raise ValueError("HTTPS origin resolves to a prohibited address")
    path = manifest.path_template or "/"
    for key, value in sorted(plan.path_parameters.items()):
        path = path.replace("{" + key + "}", quote(value, safe=""))
    if "{" in path or "}" in path or not path.startswith("/") or "?" in path:
        raise ValueError("HTTPS path template is unresolved or unsafe")
    if len(body) > manifest.max_request_bytes:
        raise ValueError("HTTPS request exceeds byte limit")
    if manifest.request_schema is not None and body:
        validate_json_schema(json.loads(body), manifest.request_schema)
    headers = {"Host": host, "Content-Type": "application/json"}
    for name in manifest.secret_env_names:
        headers[name] = environ[name]
    connection = http.client.HTTPSConnection(
        host,
        port,
        timeout=manifest.timeout_ms / 1000,
        context=ssl.create_default_context(),
    )
    pinned_ip = addresses[0]
    connection._create_connection = (  # type: ignore[attr-defined]  # DNS-rebinding guard.
        lambda _address, timeout=None, source_address=None: socket.create_connection(
            (pinned_ip, port), timeout, source_address
        )
    )
    connection.request(manifest.method or "GET", path, body=body or None, headers=headers)
    response = connection.getresponse()
    payload = response.read(manifest.max_response_bytes + 1)
    connection.close()
    if 300 <= response.status < 400:
        raise ValueError("HTTPS redirects are forbidden")
    if len(payload) > manifest.max_response_bytes:
        raise ValueError("HTTPS response exceeds byte limit")
    if manifest.response_schema is not None and payload:
        validate_json_schema(json.loads(payload), manifest.response_schema)
    return {
        "dispatch_status": "completed",
        "provider_called": True,
        "response_sha256": hashlib.sha256(payload).hexdigest(),
        "response_status": response.status,
    }


def _dispatch_process(plan: OperationPlan, environ: Mapping[str, str]) -> dict[str, Any]:
    manifest = plan.adapter_manifest
    blockers = _process_manifest_blockers(manifest)
    if blockers:
        raise ValueError(", ".join(blockers))
    if len(plan.arguments) != len(manifest.argv_patterns):
        raise ValueError("process argument count does not match schema")
    if any(value.lower() in {"-c", "-command", "-encodedcommand"} for value in plan.arguments):
        raise ValueError("inline interpreter commands are forbidden")
    for value, pattern in zip(plan.arguments, manifest.argv_patterns, strict=True):
        if not re.fullmatch(pattern, value):
            raise ValueError("process argument does not match schema")
    executable = str(Path(manifest.executable_path or "").resolve(strict=True))
    argv = [executable, *manifest.fixed_argv_prefix, *plan.arguments]
    child_env = {
        name: environ[name]
        for name in sorted(set([*manifest.environment_allowlist, *manifest.secret_env_names]))
        if name in environ
    }
    # The executable is absolute and digest-pinned; argv is schema-checked.
    process = subprocess.Popen(  # nosec B603
        argv,
        cwd=str(Path(manifest.fixed_cwd or "").resolve(strict=True)),
        env=child_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise ValueError("process output pipes are unavailable")
    size_lock = threading.Lock()
    output_size = 0
    output_limit_exceeded = threading.Event()
    digests: dict[str, str] = {}

    def drain(name: str, stream: Any) -> None:
        nonlocal output_size
        digest = hashlib.sha256()
        try:
            while chunk := stream.read(64 * 1024):
                with size_lock:
                    output_size += len(chunk)
                    if output_size > manifest.max_response_bytes:
                        output_limit_exceeded.set()
                        process.kill()
                        break
                digest.update(chunk)
        except OSError:
            pass
        digests[name] = digest.hexdigest()

    threads = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        return_code = process.wait(timeout=manifest.timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        return_code = process.wait()
    for thread in threads:
        thread.join(timeout=1)
    if any(thread.is_alive() for thread in threads):
        process.stdout.close()
        process.stderr.close()
        for thread in threads:
            thread.join(timeout=1)
    if timed_out:
        raise ValueError("process timed out")
    if output_limit_exceeded.is_set():
        raise ValueError("process output exceeds byte limit")
    return {
        "dispatch_status": "completed",
        "provider_called": True,
        "response_status": return_code,
        "stdout_sha256": digests.get("stdout", hashlib.sha256().hexdigest()),
        "stderr_sha256": digests.get("stderr", hashlib.sha256().hexdigest()),
    }


def _public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if not address.is_global:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        return not (address.ipv4_mapped or address.sixtofour or address.teredo)
    return True


def _path_contains_symlink(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _platform_key() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _redact_error(
    error: Exception,
    plan: OperationPlan,
    environment: Mapping[str, str],
) -> str:
    message = str(error)
    for name in plan.secret_env_names:
        credential_value = environment.get(name)
        if credential_value:
            message = message.replace(credential_value, "[REDACTED]")
    if isinstance(error, (JsonSchemaError, json.JSONDecodeError)):
        return "operation payload failed schema validation"
    return message[:500]
