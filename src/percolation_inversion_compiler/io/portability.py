"""Portability conformance verification helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from percolation_inversion_compiler.core.operations import PortabilityConformanceReport
from percolation_inversion_compiler.io.schema import (
    load_data,
    schema_by_type,
    schema_model_map,
    validate_data,
)


def _sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def verify_portability_conformance(manifest: str | Path) -> PortabilityConformanceReport:
    """Validate a portability conformance manifest and referenced JSON examples."""

    manifest_path = Path(manifest)
    data = load_data(manifest_path)
    examples = data.get("examples", [])
    negative_examples = data.get("negative_examples", [])
    reasons: list[str] = []
    checked: dict[str, str] = {}
    checked_negative: dict[str, str] = {}
    schema_names: dict[str, str] = {}
    hashes: dict[str, str] = {}
    if not isinstance(examples, list):
        reasons.append("manifest examples must be a list")
        examples = []
    if not isinstance(negative_examples, list):
        reasons.append("manifest negative_examples must be a list")
        negative_examples = []
    for entry in examples:
        if not isinstance(entry, dict):
            reasons.append("manifest example entry must be an object")
            continue
        file_name = entry.get("file")
        schema_name = entry.get("schema")
        expected_sha256 = entry.get("sha256")
        if not isinstance(file_name, str) or not isinstance(schema_name, str):
            reasons.append("manifest example entries require string file and schema")
            continue
        target = manifest_path.parent / file_name
        schema_names[file_name] = schema_name
        if not target.exists():
            checked[file_name] = "missing"
            reasons.append(f"{file_name}: example file is missing")
            continue
        actual_sha256 = _sha256(target)
        hashes[file_name] = actual_sha256
        if isinstance(expected_sha256, str) and expected_sha256 != actual_sha256:
            checked[file_name] = "sha256-mismatch"
            reasons.append(f"{file_name}: sha256 does not match manifest")
            continue
        try:
            schema = schema_by_type(schema_name)
        except ValueError as exc:
            checked[file_name] = "unknown-schema"
            reasons.append(f"{file_name}: {exc}")
            continue
        errors = validate_data(load_data(target), schema)
        if errors:
            checked[file_name] = "schema-invalid"
            reasons.extend(f"{file_name}: {error}" for error in errors)
            continue
        checked[file_name] = "valid"
    expected_failure_count = 0
    unexpected_failure_count = 0
    for entry in negative_examples:
        if not isinstance(entry, dict):
            reasons.append("manifest negative example entry must be an object")
            unexpected_failure_count += 1
            continue
        file_name = entry.get("file")
        schema_name = entry.get("schema")
        expected_status = entry.get("expected_status", "schema-invalid")
        expected_sha256 = entry.get("sha256")
        if (
            not isinstance(file_name, str)
            or not isinstance(schema_name, str)
            or not isinstance(expected_status, str)
        ):
            reasons.append(
                "manifest negative example entries require string file, schema, and expected_status"
            )
            unexpected_failure_count += 1
            continue
        target = manifest_path.parent / file_name
        schema_names[file_name] = schema_name
        status = "valid"
        if not target.exists():
            status = "missing"
        else:
            actual_sha256 = _sha256(target)
            hashes[file_name] = actual_sha256
            if isinstance(expected_sha256, str) and expected_sha256 != actual_sha256:
                status = "sha256-mismatch"
            else:
                try:
                    schema = schema_by_type(schema_name)
                except ValueError:
                    status = "unknown-schema"
                else:
                    try:
                        errors = validate_data(load_data(target), schema)
                    except (OSError, ValueError, json.JSONDecodeError):
                        status = "schema-invalid"
                    else:
                        status = "schema-invalid" if errors else "valid"
        checked_negative[file_name] = status
        if status == expected_status and status != "valid":
            expected_failure_count += 1
        else:
            unexpected_failure_count += 1
            reasons.append(f"{file_name}: expected {expected_status}, got {status}")
    schema_digest_input = {
        "schema_names": dict(sorted(schema_names.items())),
        "public_schema_count": len(schema_model_map()),
    }
    schema_digest = hashlib.sha256(
        json.dumps(schema_digest_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    accepted = (
        bool(checked) and not reasons and all(status == "valid" for status in checked.values())
    )
    invariants = data.get("invariants", [])
    return PortabilityConformanceReport(
        manifest_path=str(manifest_path),
        checked_examples=dict(sorted(checked.items())),
        checked_negative_examples=dict(sorted(checked_negative.items())),
        schema_names=dict(sorted(schema_names.items())),
        sha256=dict(sorted(hashes.items())),
        schema_digest=schema_digest,
        positive_example_count=len(checked),
        negative_example_count=len(checked_negative),
        expected_failure_count=expected_failure_count,
        unexpected_failure_count=unexpected_failure_count,
        semantic_invariants=[str(item) for item in invariants]
        if isinstance(invariants, list)
        else [],
        accepted=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
    )
