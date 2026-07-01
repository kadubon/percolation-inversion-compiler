"""Validate built wheel/sdist contents for PyPI distribution safety."""

from __future__ import annotations

import argparse
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WHEEL_MEMBERS = {
    "percolation_inversion_compiler/py.typed",
    "percolation_inversion_compiler/data/demo/agent_output.txt",
    "percolation_inversion_compiler/data/demo/alt_admission_packet.json",
    "percolation_inversion_compiler/data/demo/general_intake_policy.json",
    "percolation_inversion_compiler/data/demo/manifest.json",
    "percolation_inversion_compiler/data/demo/packet_envelope.json",
    "percolation_inversion_compiler/data/demo/phase_lab_runtime_report.json",
    "percolation_inversion_compiler/data/demo/phase_lab_threshold.json",
    "percolation_inversion_compiler/data/demo/phase_dashboard.json",
    "percolation_inversion_compiler/data/demo/runtime_state.json",
    "percolation_inversion_compiler/data/demo/runtime_step_input.json",
    "percolation_inversion_compiler/data/demo/runtime_step_report.json",
    "percolation_inversion_compiler/data/snapshots/alt.json",
    "percolation_inversion_compiler/data/snapshots/bit.json",
    "percolation_inversion_compiler/data/snapshots/ecpt.json",
    "percolation_inversion_compiler/data/snapshots/sqot.json",
    "percolation_inversion_compiler/data/snapshots/trc.json",
    "percolation_inversion_compiler/data/schemas/token-extraction-pipeline-report.schema.json",
    "percolation_inversion_compiler/data/schemas/token-admissibility-report.schema.json",
    "percolation_inversion_compiler/data/schemas/performance-report.schema.json",
    "percolation_inversion_compiler/data/examples/asi_proxy_loop_bundle/target.json",
    "percolation_inversion_compiler/data/examples/asi_proxy_loop_bundle/performance_report.example.json",
    "percolation_inversion_compiler/data/docs/asi-proxy-loop.md",
    "percolation_inversion_compiler/data/docs/cross-repo-loop-conformance.md",
}
REQUIRED_SDIST_SUFFIXES = {
    "src/percolation_inversion_compiler/py.typed",
    "src/percolation_inversion_compiler/data/demo/agent_output.txt",
    "src/percolation_inversion_compiler/data/demo/alt_admission_packet.json",
    "src/percolation_inversion_compiler/data/demo/general_intake_policy.json",
    "src/percolation_inversion_compiler/data/demo/manifest.json",
    "src/percolation_inversion_compiler/data/demo/packet_envelope.json",
    "src/percolation_inversion_compiler/data/demo/phase_lab_runtime_report.json",
    "src/percolation_inversion_compiler/data/demo/phase_lab_threshold.json",
    "src/percolation_inversion_compiler/data/demo/phase_dashboard.json",
    "src/percolation_inversion_compiler/data/demo/runtime_state.json",
    "src/percolation_inversion_compiler/data/demo/runtime_step_input.json",
    "src/percolation_inversion_compiler/data/demo/runtime_step_report.json",
    "src/percolation_inversion_compiler/data/snapshots/alt.json",
    "src/percolation_inversion_compiler/data/snapshots/bit.json",
    "src/percolation_inversion_compiler/data/snapshots/ecpt.json",
    "src/percolation_inversion_compiler/data/snapshots/sqot.json",
    "src/percolation_inversion_compiler/data/snapshots/trc.json",
    "schemas/token-extraction-pipeline-report.schema.json",
    "schemas/token-admissibility-report.schema.json",
    "schemas/performance-report.schema.json",
    "examples/asi_proxy_loop_bundle/target.json",
    "examples/asi_proxy_loop_bundle/performance_report.example.json",
    "docs/asi-proxy-loop.md",
    "docs/cross-repo-loop-conformance.md",
}
FORBIDDEN_WHEEL_SUFFIXES = {
    ".7z",
    ".bin",
    ".cer",
    ".ckpt",
    ".crt",
    ".gz",
    ".key",
    ".onnx",
    ".p12",
    ".pckl",
    ".pdf",
    ".pem",
    ".pfx",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".rar",
    ".safetensors",
    ".tar",
    ".tex",
    ".tgz",
    ".whl",
    ".zip",
}
FORBIDDEN_SDIST_SUFFIXES = {
    ".ckpt",
    ".key",
    ".onnx",
    ".p12",
    ".pdf",
    ".pem",
    ".pfx",
    ".pt",
    ".pth",
    ".safetensors",
    ".tex",
}
FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "downloads",
    "private",
    "secrets",
    "site-packages",
    "venv",
}


def project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _parts(name: str) -> set[str]:
    return {part for part in Path(name).parts if part}


def validate_wheel(wheel: Path) -> list[str]:
    failures: list[str] = []
    if not wheel.exists():
        return [f"missing wheel: {wheel}"]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    missing = sorted(REQUIRED_WHEEL_MEMBERS - names)
    failures.extend(f"wheel missing required member: {name}" for name in missing)
    for name in sorted(names):
        suffixes = Path(name).suffixes
        if any(suffix.lower() in FORBIDDEN_WHEEL_SUFFIXES for suffix in suffixes):
            failures.append(f"wheel contains forbidden artifact suffix: {name}")
        if _parts(name) & FORBIDDEN_PARTS:
            failures.append(f"wheel contains forbidden artifact path: {name}")
    return failures


def validate_sdist(sdist: Path) -> list[str]:
    failures: list[str] = []
    if not sdist.exists():
        return [f"missing sdist: {sdist}"]
    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
    missing = sorted(
        suffix
        for suffix in REQUIRED_SDIST_SUFFIXES
        if not any(name.endswith(f"/{suffix}") for name in names)
    )
    failures.extend(f"sdist missing required member ending with: {name}" for name in missing)
    for name in sorted(names):
        if _parts(name) & {".git", ".venv", "dist", "downloads", "private", "secrets", "venv"}:
            failures.append(f"sdist contains forbidden artifact path: {name}")
        suffixes = Path(name).suffixes
        if any(suffix.lower() in FORBIDDEN_SDIST_SUFFIXES for suffix in suffixes):
            failures.append(f"sdist contains forbidden artifact suffix: {name}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--version", default=project_version())
    args = parser.parse_args()

    dist_dir = ROOT / args.dist_dir
    version = str(args.version)
    wheel = dist_dir / f"percolation_inversion_compiler-{version}-py3-none-any.whl"
    sdist = dist_dir / f"percolation_inversion_compiler-{version}.tar.gz"
    failures = [*validate_wheel(wheel), *validate_sdist(sdist)]
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
