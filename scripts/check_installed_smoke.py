"""Install the built wheel in a clean environment and exercise public resources."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def _run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="pic-installed-smoke-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        _run(str(python), "-m", "pip", "install", f"{wheel}[operation]")

        check = root / "check.py"
        check.write_text(
            """
from importlib.resources import files
from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.operation import (
    OperationAdapterManifest,
    check_operation_adapter,
)
from percolation_inversion_compiler.runtime import (
    AccelerationMeasurementMetrics,
    RuntimeRunReport,
    certify_runtime_acceleration,
)

assert __version__ == EXPECTED_VERSION
data = files("percolation_inversion_compiler.data")
assert data.joinpath("schemas/AccelerationMetricComparison.schema.json").is_file()
assert data.joinpath("docs/resource-matched-measurement.md").is_file()
assert data.joinpath("contracts/v1.1/pic-cross-language-contract.json").is_file()

base_metrics = AccelerationMeasurementMetrics(
    time_to_verified=3, verification_yield=0.4, residual_half_life=4,
    receiver_reuse=0.5, certified_capital_gain=0.1, resource_cost=1,
    error_correlation=0.5, fixed_horizon=True,
    stopping_rule_ref="stopping:installed", evidence_refs=["evidence:baseline"],
)
candidate_metrics = base_metrics.model_copy(update={
    "time_to_verified": 1, "verification_yield": 0.5,
    "residual_half_life": 2, "receiver_reuse": 1,
    "certified_capital_gain": 0.2, "error_correlation": 0,
    "evidence_refs": ["evidence:candidate"],
})
baseline = RuntimeRunReport(
    run_id="baseline:installed", initial_state_id="state:installed",
    threshold_crossing_step=3, resource_units=1, acceleration_metrics=base_metrics,
)
candidate = RuntimeRunReport(
    run_id="candidate:installed", initial_state_id="state:installed",
    threshold_crossing_step=1, resource_units=1, acceleration_metrics=candidate_metrics,
)
certificate = certify_runtime_acceleration(baseline, candidate)
assert certificate.accepted and certificate.acceleration_metrics_certified

adapter = check_operation_adapter(OperationAdapterManifest(**{
    "manifest_id": "installed:read-only",
    "adapter_kind": "https",
    "risk_class": "read_only",
    "fixed_origin": "https://example.com",
    "path_template": "/v1/{object_id}",
    "method": "GET",
}))
assert adapter["accepted"] and not adapter["settled"]
""".replace("EXPECTED_VERSION", repr(args.version)),
            encoding="utf-8",
        )
        _run(str(python), str(check))

    print(json.dumps({"installed_smoke": True, "version": args.version}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
