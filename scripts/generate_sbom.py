"""Generate a deterministic SBOM dependency inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from percolation_inversion_compiler.io.sbom import build_sbom_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=["pic", "cyclonedx"], default="pic")
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(build_sbom_document(args.format), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
