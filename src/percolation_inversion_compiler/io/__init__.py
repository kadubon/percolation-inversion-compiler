"""Input/output helpers for TeX, registries, schemas, and Zenodo metadata."""

from __future__ import annotations

from percolation_inversion_compiler.io.audit import audit_theory_source
from percolation_inversion_compiler.io.doctor import (
    build_operational_readiness_report,
    readiness_profile,
)
from percolation_inversion_compiler.io.provenance import (
    ProvenanceManifest,
    ProvenanceManifestEntry,
    SchemaBundleDigest,
    create_provenance_manifest,
    schema_bundle_digest,
    verify_provenance_manifest,
)
from percolation_inversion_compiler.io.schema import (
    PortabilitySchemaBundle,
    registry_json_schema,
    schema_bundle,
    schema_by_type,
    validate_data,
)
from percolation_inversion_compiler.io.snapshots import (
    SnapshotAttribution,
    SnapshotCatalog,
    TheorySnapshot,
    TheorySnapshotItem,
    find_snapshot_item,
    list_theory_snapshots,
    load_snapshot_catalog,
    load_theory_snapshot,
    snapshot_delta,
)
from percolation_inversion_compiler.io.tex import (
    ExtractedArtifact,
    ExtractedFile,
    MRRecord,
    count_mr_records_by_category,
    extract_artifact,
    extract_filecontents,
    extract_mr_records,
    extract_theory_coverage,
)
from percolation_inversion_compiler.io.zenodo import (
    CANONICAL_RECORDS,
    CanonicalManifest,
    CanonicalManifestRecord,
    CanonicalRecord,
    canonical_manifest,
    validate_canonical_source,
)

__all__ = [
    "CANONICAL_RECORDS",
    "CanonicalManifest",
    "CanonicalManifestRecord",
    "CanonicalRecord",
    "ExtractedArtifact",
    "ExtractedFile",
    "MRRecord",
    "PortabilitySchemaBundle",
    "ProvenanceManifest",
    "ProvenanceManifestEntry",
    "SchemaBundleDigest",
    "SnapshotAttribution",
    "SnapshotCatalog",
    "TheorySnapshot",
    "TheorySnapshotItem",
    "audit_theory_source",
    "build_operational_readiness_report",
    "canonical_manifest",
    "count_mr_records_by_category",
    "create_provenance_manifest",
    "extract_artifact",
    "extract_filecontents",
    "extract_mr_records",
    "extract_theory_coverage",
    "find_snapshot_item",
    "list_theory_snapshots",
    "load_snapshot_catalog",
    "load_theory_snapshot",
    "readiness_profile",
    "registry_json_schema",
    "schema_bundle",
    "schema_bundle_digest",
    "schema_by_type",
    "snapshot_delta",
    "validate_canonical_source",
    "validate_data",
    "verify_provenance_manifest",
]
