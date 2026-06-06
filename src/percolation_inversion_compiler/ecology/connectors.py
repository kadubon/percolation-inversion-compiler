"""Optional live connectors for packet ingestion."""

from __future__ import annotations

import importlib
import re
from typing import Any
from urllib.parse import quote_plus, urlparse

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.ecology.algorithms import packet_from_text
from percolation_inversion_compiler.ecology.records import (
    PacketIngestionReport,
    PacketSourceKind,
)


def ingest_live_source(
    source: str,
    *,
    kind: PacketSourceKind,
    token: str | None = None,
    timeout: float = 20.0,
) -> PacketIngestionReport:
    """Ingest one live metadata source through optional ``httpx``."""

    try:
        httpx = importlib.import_module("httpx")
    except ModuleNotFoundError:
        return _diagnostic_report(
            kind,
            source,
            "optional connector dependency 'httpx' is not installed",
        )
    try:
        if kind == PacketSourceKind.GITHUB:
            return _ingest_github(source, httpx, token=token, timeout=timeout)
        if kind == PacketSourceKind.ZENODO:
            return _ingest_zenodo(source, httpx, timeout=timeout)
        if kind == PacketSourceKind.ARXIV:
            return _ingest_arxiv(source, httpx, timeout=timeout)
    except httpx.HTTPError as exc:
        return _diagnostic_report(kind, source, f"connector request failed: {exc}")
    return _diagnostic_report(kind, source, f"unsupported live connector kind {kind.value!r}")


def infer_live_kind(source: str) -> PacketSourceKind:
    """Infer connector kind from a URL-like source."""

    host = urlparse(source).netloc.lower()
    if "github.com" in host or (source.count("/") == 1 and not source.startswith("http")):
        return PacketSourceKind.GITHUB
    if "zenodo.org" in host or "zenodo" in source.lower():
        return PacketSourceKind.ZENODO
    if "arxiv.org" in host or source.lower().startswith("arxiv:"):
        return PacketSourceKind.ARXIV
    return PacketSourceKind.LOCAL


def _ingest_github(
    source: str,
    httpx_module: Any,
    *,
    token: str | None,
    timeout: float,
) -> PacketIngestionReport:
    repo = _github_repo(source)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}"
    response = httpx_module.get(url, headers=headers, timeout=timeout)
    if response.status_code >= 400:
        return _diagnostic_report(
            PacketSourceKind.GITHUB,
            source,
            f"github status {response.status_code}",
        )
    data = response.json()
    text = "\n".join(
        [
            str(data.get("full_name", repo)),
            str(data.get("description", "")),
            f"stars:{data.get('stargazers_count', 0)}",
            f"language:{data.get('language', '')}",
        ]
    )
    packet = packet_from_text(
        text,
        packet_id=f"packet:github:{repo.replace('/', ':')}",
        source_kind=PacketSourceKind.GITHUB,
        source_ref=repo,
        tags=["github", "code"],
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:github:{repo}",
        accepted=True,
        source_kind=PacketSourceKind.GITHUB,
        packets=[packet],
    )


def _ingest_zenodo(source: str, httpx_module: Any, *, timeout: float) -> PacketIngestionReport:
    record_id = source.rstrip("/").split("/")[-1]
    url = f"https://zenodo.org/api/records/{record_id}"
    response = httpx_module.get(url, timeout=timeout)
    if response.status_code >= 400:
        return _diagnostic_report(
            PacketSourceKind.ZENODO,
            source,
            f"zenodo status {response.status_code}",
        )
    data = response.json()
    metadata = data.get("metadata", {})
    title = str(metadata.get("title", record_id))
    description = str(metadata.get("description", ""))
    packet = packet_from_text(
        f"{title}\n{description}",
        packet_id=f"packet:zenodo:{record_id}",
        source_kind=PacketSourceKind.ZENODO,
        source_ref=record_id,
        tags=["zenodo", "paper"],
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:zenodo:{record_id}",
        accepted=True,
        source_kind=PacketSourceKind.ZENODO,
        packets=[packet],
    )


def _ingest_arxiv(source: str, httpx_module: Any, *, timeout: float) -> PacketIngestionReport:
    query = source.replace("arxiv:", "")
    url = f"https://export.arxiv.org/api/query?search_query={quote_plus(query)}&max_results=1"
    response = httpx_module.get(url, timeout=timeout)
    if response.status_code >= 400:
        return _diagnostic_report(
            PacketSourceKind.ARXIV,
            source,
            f"arxiv status {response.status_code}",
        )
    entry = _first_tag(response.text, "entry")
    if entry is None:
        return _diagnostic_report(PacketSourceKind.ARXIV, source, "arxiv returned no entries")
    title = (_first_tag(entry, "title") or "").strip()
    summary = (_first_tag(entry, "summary") or "").strip()
    arxiv_id = (_first_tag(entry, "id") or source).split("/")[-1]
    packet = packet_from_text(
        f"{title}\n{summary}",
        packet_id=f"packet:arxiv:{arxiv_id}",
        source_kind=PacketSourceKind.ARXIV,
        source_ref=arxiv_id,
        tags=["arxiv", "paper"],
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:arxiv:{arxiv_id}",
        accepted=True,
        source_kind=PacketSourceKind.ARXIV,
        packets=[packet],
    )


def _github_repo(source: str) -> str:
    if source.startswith("http"):
        parts = [part for part in urlparse(source).path.split("/") if part]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return source.strip("/")


def _first_tag(text: str, tag: str) -> str | None:
    match = re.search(
        rf"<(?:[A-Za-z0-9_]+:)?{re.escape(tag)}[^>]*>(.*?)</(?:[A-Za-z0-9_]+:)?{re.escape(tag)}>",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _diagnostic_report(
    kind: PacketSourceKind,
    source: str,
    reason: str,
) -> PacketIngestionReport:
    return PacketIngestionReport(
        report_id=f"packet-ingestion:{kind.value}:diagnostic",
        accepted=False,
        source_kind=kind,
        rejected_sources=[source],
        reasons=[reason],
        residual_ledger=Ledger().add_coordinate(
            f"connector:{kind.value}:unavailable",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        ),
    )
