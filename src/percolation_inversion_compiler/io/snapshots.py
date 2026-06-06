"""Bundled derived theory snapshots for users without canonical TeX files."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.coverage import (
    ExternalObligationCatalog,
    TheoryImplementationRecord,
)


class SnapshotAttribution(BaseModel):
    """CC-BY attribution metadata for a derived non-vendored snapshot."""

    author: str
    year: int
    title: str
    doi: str
    license_id: str
    source_tex_md5: str
    derived_from: str = "canonical TeX metadata extraction"


class TheorySnapshotItem(BaseModel):
    """Small item-id implementation mapping derived from a canonical source."""

    item_id: str
    label: str
    coverage_status: str
    implementation_refs: list[str] = Field(default_factory=list)
    obligation_category: str | None = None
    verifier_route: str | None = None


class TheorySnapshot(BaseModel):
    """Portable snapshot for one canonical theory artifact."""

    artifact_key: str
    artifact: str
    schema_version: str = "theory-snapshot-1.0"
    attribution: SnapshotAttribution
    definitions: int
    claims: int
    mr_records: int
    coverage_counts: dict[str, int]
    coverage_delta: dict[str, int]
    external_obligation_category_summary: dict[str, int] = Field(default_factory=dict)
    external_verifier_route_summary: dict[str, int] = Field(default_factory=dict)
    external_obligation_catalog: ExternalObligationCatalog | None = None
    item_mappings: list[TheorySnapshotItem] = Field(default_factory=list)
    representative_items: list[TheorySnapshotItem] = Field(default_factory=list)


class SnapshotCatalog(BaseModel):
    """Named catalog of bundled derived theory snapshots."""

    catalog_id: str = "percolation-inversion-compiler-derived-snapshots"
    snapshots: dict[str, TheorySnapshot]


_SNAPSHOT_PACKAGE = "percolation_inversion_compiler.data.snapshots"


def _snapshot_path(artifact_key: str) -> Any:
    return files(_SNAPSHOT_PACKAGE).joinpath(f"{artifact_key}.json")


def load_theory_snapshot(artifact_key: str) -> TheorySnapshot:
    key = artifact_key.lower()
    data = json.loads(_snapshot_path(key).read_text(encoding="utf-8"))
    return TheorySnapshot.model_validate(data)


def list_theory_snapshots() -> list[TheorySnapshot]:
    snapshots: list[TheorySnapshot] = []
    for key in ("ecpt", "bit", "trc"):
        snapshots.append(load_theory_snapshot(key))
    return snapshots


def load_snapshot_catalog() -> SnapshotCatalog:
    return SnapshotCatalog(
        snapshots={snapshot.artifact_key: snapshot for snapshot in list_theory_snapshots()}
    )


def find_snapshot_item(
    item_id: str,
    *,
    artifact_key: str | None = None,
    external_only: bool = False,
) -> TheoryImplementationRecord | TheorySnapshotItem | None:
    snapshots = (
        [load_theory_snapshot(artifact_key)]
        if artifact_key is not None
        else list_theory_snapshots()
    )
    for snapshot in snapshots:
        if external_only and snapshot.external_obligation_catalog is not None:
            for obligation in snapshot.external_obligation_catalog.obligations:
                if obligation.item_id == item_id:
                    return obligation
            continue
        for item in snapshot.item_mappings:
            if item.item_id == item_id:
                return item
    return None


def snapshot_item_override(
    artifact: str,
    item_id: str,
) -> TheorySnapshotItem | None:
    artifact_to_key = {
        "Executable Capability Percolation Theory.tex": "ecpt",
        "Bottleneck Inversion Theory.tex": "bit",
        "Typed Reality Compilation.tex": "trc",
    }
    key = artifact_to_key.get(Path(artifact).name)
    if key is None:
        return None
    item = find_snapshot_item(item_id, artifact_key=key)
    return item if isinstance(item, TheorySnapshotItem) else None


def snapshot_delta(
    *,
    artifact_key: str | None,
    coverage_counts: dict[str, int],
    external_category_summary: dict[str, int],
) -> dict[str, object]:
    if artifact_key is None:
        return {}
    try:
        snapshot = load_theory_snapshot(artifact_key)
    except (FileNotFoundError, ModuleNotFoundError):
        return {"available": False, "reason": "bundled snapshot not found"}
    return {
        "available": True,
        "coverage_counts_match": snapshot.coverage_counts == coverage_counts,
        "external_category_summary_match": (
            snapshot.external_obligation_category_summary == external_category_summary
        ),
        "expected_coverage_counts": snapshot.coverage_counts,
        "observed_coverage_counts": coverage_counts,
        "expected_external_category_summary": snapshot.external_obligation_category_summary,
        "observed_external_category_summary": external_category_summary,
    }
