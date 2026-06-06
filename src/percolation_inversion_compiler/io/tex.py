"""Extract machine-readable records from TeX source artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.coverage import (
    TheoryCoverageRecord,
    TheoryItem,
    classify_theory_item,
    implementation_metadata,
)
from percolation_inversion_compiler.core.judgment import ExtractorOutput, Judgment
from percolation_inversion_compiler.core.records import ClaimRecord, Registry
from percolation_inversion_compiler.core.status import ClaimStatus


class ExtractedFile(BaseModel):
    """One ``filecontents*`` block from a TeX artifact."""

    name: str
    text: str

    def json_data(self) -> dict[str, Any] | None:
        if not self.name.lower().endswith(".json"):
            return None
        data = json.loads(self.text)
        if not isinstance(data, dict):
            raise ValueError(f"{self.name} does not contain a JSON object")
        return data


class MRRecord(BaseModel):
    """Line-oriented BIT ``MRRecord`` family entry."""

    record_type: str
    identifier: str
    fields: dict[str, str | list[str]] = Field(default_factory=dict)
    raw: str
    line_number: int


class TexGrammarDiagnostic(BaseModel):
    """Strict TeX grammar diagnostic for fail-closed source audits."""

    diagnostic_id: str
    kind: str
    severity: str = "error"
    line_number: int
    message: str
    raw: str


class StrictTexParseReport(BaseModel):
    """Strict parse report for theorem-like and MRRecord syntax."""

    source: str
    accepted: bool
    diagnostics: list[TexGrammarDiagnostic] = Field(default_factory=list)


class ExtractedArtifact(BaseModel):
    """Machine-readable projection extracted from a TeX artifact."""

    source: str
    filecontents: list[ExtractedFile] = Field(default_factory=list)
    json_blocks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    mr_records: list[MRRecord] = Field(default_factory=list)
    registries: list[Registry] = Field(default_factory=list)

    def merged_registry(self) -> Registry:
        claims: list[ClaimRecord] = []
        metadata: dict[str, object] = {}
        for registry in self.registries:
            claims.extend(registry.claims)
            metadata.update(registry.metadata)
        merged = Registry(artifact=self.source, claims=claims, metadata=metadata)
        merged.require_unique_claim_ids()
        return merged

    def extractor_output(self) -> ExtractorOutput:
        judgments: list[Judgment] = []
        for registry in self.registries:
            for claim in registry.claims:
                status = claim.derived_status
                if status is None:
                    status = ClaimStatus.PROVISIONAL
                judgments.append(
                    Judgment(
                        claim_id=claim.claim_id,
                        claim_label=claim.label,
                        kind=claim.kind,
                        derived_status=status,
                        dependencies=claim.dependency_labels,
                        ledger_coordinates=claim.ledger_coordinates,
                        citation_keys=claim.citation_keys,
                    )
                )
        return ExtractorOutput(artifact=self.source, judgments=judgments)


_FILECONTENTS_RE = re.compile(
    r"\\begin\{filecontents\*\}(?:\[[^\]]*\])?\{([^}]+)\}\s*(.*?)\\end\{filecontents\*\}",
    re.DOTALL,
)
_SECTION_RE = re.compile(r"\\section\*?\{(.+?)\}")
_DEFINITION_RE = re.compile(r"\\begin\{definition\}\[(.*?)\](?:\\label\{([^}]+)\})?")
_CLAIM_RE = re.compile(
    r"\\begin\{(theorem|proposition|lemma|corollary)\}\[(.*?)\](?:\\label\{([^}]+)\})?"
)
_ALLOWED_ITEM_ENVIRONMENTS = {"definition", "theorem", "proposition", "lemma", "corollary"}
_KNOWN_NONEXTRACTED_THEOREM_ENVIRONMENTS = {"axiom", "assumption"}
_BEGIN_ENV_RE = re.compile(r"\\begin\{([^}]+)\}")
_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_MR_ARITY = {
    "MRRecord": 3,
    "MRClaim": 2,
    "MRWitness": 2,
    "MRDepends": 2,
    "MRCitation": 3,
}


def extract_filecontents(source_text: str) -> list[ExtractedFile]:
    """Extract TeX ``filecontents*`` blocks."""

    return [
        ExtractedFile(name=name.strip(), text=body.strip())
        for name, body in _FILECONTENTS_RE.findall(source_text)
    ]


def _parse_macro_args(line: str, macro_name: str) -> list[str]:
    prefix = f"\\{macro_name}"
    index = line.find(prefix)
    if index < 0:
        return []
    args: list[str] = []
    cursor = index + len(prefix)
    while cursor < len(line):
        while cursor < len(line) and line[cursor].isspace():
            cursor += 1
        if cursor >= len(line) or line[cursor] != "{":
            break
        depth = 0
        start = cursor + 1
        cursor += 1
        while cursor < len(line):
            char = line[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                if depth == 0:
                    args.append(line[start:cursor])
                    cursor += 1
                    break
                depth -= 1
            cursor += 1
        else:
            break
    return args


def _parse_fields(text: str) -> dict[str, str | list[str]]:
    fields: dict[str, str | list[str]] = {}
    if not text:
        return fields
    for part in text.split(";"):
        if not part:
            continue
        key, sep, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if not sep:
            fields[key] = value
            continue
        if "," in value:
            fields[key] = [item.strip() for item in value.split(",") if item.strip()]
        else:
            fields[key] = value
    return fields


def extract_mr_records(source_text: str) -> list[MRRecord]:
    """Extract BIT line-oriented ``MR*`` records from TeX source."""

    records: list[MRRecord] = []
    for line_number, line in enumerate(source_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("\\MR"):
            continue
        if stripped.startswith("\\MRRecord"):
            args = _parse_macro_args(stripped, "MRRecord")
            if len(args) >= 3:
                records.append(
                    MRRecord(
                        record_type=args[0],
                        identifier=args[1],
                        fields=_parse_fields(args[2]),
                        raw=stripped,
                        line_number=line_number,
                    )
                )
        elif stripped.startswith("\\MRClaim"):
            args = _parse_macro_args(stripped, "MRClaim")
            if len(args) >= 2:
                records.append(
                    MRRecord(
                        record_type="claim",
                        identifier=args[0],
                        fields=_parse_fields(args[1]),
                        raw=stripped,
                        line_number=line_number,
                    )
                )
        elif stripped.startswith("\\MRWitness"):
            args = _parse_macro_args(stripped, "MRWitness")
            if len(args) >= 2:
                records.append(
                    MRRecord(
                        record_type="witness",
                        identifier=args[0],
                        fields=_parse_fields(args[1]),
                        raw=stripped,
                        line_number=line_number,
                    )
                )
        elif stripped.startswith("\\MRDepends"):
            args = _parse_macro_args(stripped, "MRDepends")
            if len(args) >= 2:
                records.append(
                    MRRecord(
                        record_type="depends",
                        identifier=args[0],
                        fields={
                            "depends_on": [
                                item.strip() for item in args[1].split(",") if item.strip()
                            ]
                        },
                        raw=stripped,
                        line_number=line_number,
                    )
                )
        elif stripped.startswith("\\MRCitation"):
            args = _parse_macro_args(stripped, "MRCitation")
            if len(args) >= 3:
                records.append(
                    MRRecord(
                        record_type="citation",
                        identifier=args[0],
                        fields={"doi": args[1], "source": args[2]},
                        raw=stripped,
                        line_number=line_number,
                    )
                )
    return records


def strict_tex_parse_report(source: str | Path) -> StrictTexParseReport:
    """Diagnose claim-like TeX shapes that the extractor would otherwise ignore."""

    path = Path(source)
    lines = path.read_text(encoding="utf-8").splitlines()
    diagnostics: list[TexGrammarDiagnostic] = []
    seen_item_ids: dict[str, int] = {}
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if begin_match := _BEGIN_ENV_RE.search(stripped):
            environment = begin_match.group(1)
            if environment in {"claim", "conjecture"}:
                diagnostics.append(
                    TexGrammarDiagnostic(
                        diagnostic_id=f"tex-unknown-theorem-env:{index}",
                        kind="unknown-theorem-environment",
                        line_number=index,
                        message=f"unsupported theorem-like environment {environment!r}",
                        raw=stripped,
                    )
                )
            if environment in _KNOWN_NONEXTRACTED_THEOREM_ENVIRONMENTS:
                label_match = _LABEL_RE.search(stripped)
                if label_match is not None and label_match.group(1) in seen_item_ids:
                    label_id = label_match.group(1)
                    diagnostics.append(
                        TexGrammarDiagnostic(
                            diagnostic_id=f"tex-duplicate-label:{index}",
                            kind="duplicate-item-id",
                            line_number=index,
                            message=(
                                f"duplicate item id {label_id!r}; first seen at line "
                                f"{seen_item_ids[label_id]}"
                            ),
                            raw=stripped,
                        )
                    )
                if label_match is not None:
                    seen_item_ids[label_match.group(1)] = index
            if environment in _ALLOWED_ITEM_ENVIRONMENTS:
                if environment == "definition":
                    parsed = _DEFINITION_RE.search(stripped)
                else:
                    parsed = _CLAIM_RE.search(stripped)
                if parsed is None:
                    diagnostics.append(
                        TexGrammarDiagnostic(
                            diagnostic_id=f"tex-unparsed-item:{index}",
                            kind="unparsed-claim-like-line",
                            line_number=index,
                            message="claim-like environment could not be parsed by strict grammar",
                            raw=stripped,
                        )
                    )
                    if index < len(lines) and _LABEL_RE.search(lines[index]):
                        diagnostics.append(
                            TexGrammarDiagnostic(
                                diagnostic_id=f"tex-multiline-label:{index + 1}",
                                kind="multi-line-label-parse-failure",
                                line_number=index + 1,
                                message="label was split away from theorem header",
                                raw=lines[index].strip(),
                            )
                        )
                else:
                    label = parsed.groups()[-1]
                    if label is None and index < len(lines) and _LABEL_RE.search(lines[index]):
                        diagnostics.append(
                            TexGrammarDiagnostic(
                                diagnostic_id=f"tex-multiline-label:{index + 1}",
                                kind="multi-line-label-parse-failure",
                                line_number=index + 1,
                                message="label was split away from theorem header",
                                raw=lines[index].strip(),
                            )
                        )
                    if label is not None:
                        if label in seen_item_ids:
                            diagnostics.append(
                                TexGrammarDiagnostic(
                                    diagnostic_id=f"tex-duplicate-label:{index}",
                                    kind="duplicate-item-id",
                                    line_number=index,
                                    message=(
                                        f"duplicate item id {label!r}; first seen at line "
                                        f"{seen_item_ids[label]}"
                                    ),
                                    raw=stripped,
                                )
                            )
                        seen_item_ids[label] = index
        labels = _LABEL_RE.findall(stripped)
        if labels and _BEGIN_ENV_RE.search(stripped) is None:
            for label in labels:
                if label.startswith(("def:", "thm:", "lem:", "prop:", "cor:")):
                    diagnostics.append(
                        TexGrammarDiagnostic(
                            diagnostic_id=f"tex-orphan-label:{index}:{label}",
                            kind="orphan-label",
                            line_number=index,
                            message=f"item label {label!r} is not attached to a parsed header",
                            raw=stripped,
                        )
                    )
        if stripped.startswith("\\MR"):
            for macro_name, required_arity in _MR_ARITY.items():
                if stripped.startswith(f"\\{macro_name}"):
                    args = _parse_macro_args(stripped, macro_name)
                    if len(args) != required_arity:
                        diagnostics.append(
                            TexGrammarDiagnostic(
                                diagnostic_id=f"tex-mr-arity:{index}:{macro_name}",
                                kind="mr-macro-arity-mismatch",
                                line_number=index,
                                message=(
                                    f"{macro_name} expected {required_arity} arguments, "
                                    f"parsed {len(args)}"
                                ),
                                raw=stripped,
                            )
                        )
                    break
    return StrictTexParseReport(
        source=str(path),
        accepted=not any(diagnostic.severity == "error" for diagnostic in diagnostics),
        diagnostics=diagnostics,
    )


def count_mr_records_by_category(records: list[MRRecord]) -> dict[str, int]:
    """Return deterministic BIT MRRecord category counts."""

    claims = sum(1 for record in records if record.record_type == "claim")
    witnesses = sum(1 for record in records if record.record_type == "witness")
    depends = sum(1 for record in records if record.record_type == "depends")
    citations = sum(1 for record in records if record.record_type == "citation")
    total = len(records)
    return {
        "total": total,
        "claims": claims,
        "witnesses": witnesses,
        "depends": depends,
        "citations": citations,
        "metadata": total - claims - witnesses - depends - citations,
    }


def extract_theory_coverage(source: str | Path) -> TheoryCoverageRecord:
    """Extract definition, claim, and MRRecord coverage rows from TeX source."""

    path = Path(source)
    text = path.read_text(encoding="utf-8")
    section: str | None = None
    items: list[TheoryItem] = []
    definition_count = 0
    claim_count = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if section_match := _SECTION_RE.search(line):
            section = section_match.group(1)
        if definition_match := _DEFINITION_RE.search(line):
            definition_count += 1
            label = definition_match.group(1)
            item_id = definition_match.group(2) or f"definition:{definition_count}"
            coverage_status, refs = classify_theory_item(
                label,
                item_id=item_id,
                artifact=path.name,
            )
            metadata = implementation_metadata(item_id, coverage_status, refs, label)
            items.append(
                TheoryItem(
                    item_id=item_id,
                    artifact=path.name,
                    kind="definition",
                    label=label,
                    line_number=line_number,
                    section=section,
                    coverage_status=coverage_status,
                    implementation_refs=refs,
                    **metadata,
                )
            )
        if claim_match := _CLAIM_RE.search(line):
            claim_count += 1
            kind, label, label_id = claim_match.groups()
            item_id = label_id or f"{kind}:{claim_count}"
            coverage_status, refs = classify_theory_item(
                label,
                item_id=item_id,
                artifact=path.name,
            )
            metadata = implementation_metadata(item_id, coverage_status, refs, label)
            items.append(
                TheoryItem(
                    item_id=item_id,
                    artifact=path.name,
                    kind=kind,
                    label=label,
                    line_number=line_number,
                    section=section,
                    coverage_status=coverage_status,
                    implementation_refs=refs,
                    **metadata,
                )
            )
    return TheoryCoverageRecord(
        source=str(path),
        artifact=path.name,
        definitions=definition_count,
        claims=claim_count,
        mr_records=len(extract_mr_records(text)),
        items=items,
    )


def registry_from_json_block(name: str, data: dict[str, Any]) -> Registry | None:
    claims = data.get("claims")
    if not isinstance(claims, list):
        return None
    claim_records = [
        ClaimRecord.from_raw(claim, artifact=name) for claim in claims if isinstance(claim, dict)
    ]
    return Registry(
        schema_version=str(data.get("schema_version", "registry-1.0")),
        artifact=str(data.get("artifact", name)),
        claims=claim_records,
        metadata={key: value for key, value in data.items() if key != "claims"},
    )


def registry_from_mr_records(source: str, records: list[MRRecord]) -> Registry | None:
    claim_records: dict[str, ClaimRecord] = {}
    dependencies: dict[str, list[str]] = {}
    citations: list[str] = []
    for record in records:
        if record.record_type == "claim":
            label = str(record.fields.get("guarantee", record.identifier))
            ledger = [
                key
                for key in ["inputs", "witness", "guarantee", "failure", "proof", "proof-pattern"]
                if key in record.fields
            ]
            claim_records[record.identifier] = ClaimRecord(
                claim_id=record.identifier,
                kind="claim",
                label=label,
                ledger_coordinates=ledger,
                artifact=source,
            )
        elif record.record_type == "depends":
            deps = record.fields.get("depends_on", [])
            dependencies[record.identifier] = (
                [str(item) for item in deps] if isinstance(deps, list) else [str(deps)]
            )
        elif record.record_type == "citation":
            citations.append(record.identifier)
    if not claim_records:
        return None
    for claim_id, deps in dependencies.items():
        if claim_id in claim_records:
            claim = claim_records[claim_id]
            claim_records[claim_id] = claim.model_copy(
                update={"dependency_labels": sorted(set(claim.dependency_labels) | set(deps))}
            )
    for claim_id, claim in list(claim_records.items()):
        claim_records[claim_id] = claim.model_copy(update={"citation_keys": citations})
    return Registry(
        schema_version="bit-mr-records-1.0",
        artifact=source,
        claims=list(claim_records.values()),
        metadata={"mr_record_count": len(records)},
    )


def extract_artifact(source: str | Path) -> ExtractedArtifact:
    """Extract all machine-readable projections from a TeX source file."""

    path = Path(source)
    text = path.read_text(encoding="utf-8")
    filecontents = extract_filecontents(text)
    json_blocks: dict[str, dict[str, Any]] = {}
    registries: list[Registry] = []
    for block in filecontents:
        data = block.json_data()
        if data is None:
            continue
        json_blocks[block.name] = data
        registry = registry_from_json_block(block.name, data)
        if registry is not None:
            registries.append(registry)
    mr_records = extract_mr_records(text)
    mr_registry = registry_from_mr_records(path.name, mr_records)
    if mr_registry is not None:
        registries.append(mr_registry)
    return ExtractedArtifact(
        source=str(path),
        filecontents=filecontents,
        json_blocks=json_blocks,
        mr_records=mr_records,
        registries=registries,
    )
