"""SQLite-backed local store for Phase Ecology Lab diagnostics."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from percolation_inversion_compiler.phase_lab.algorithms import (
    build_effective_packet_graph,
    build_window_index,
    event_from_payload,
    observe_phase_window,
)
from percolation_inversion_compiler.phase_lab.records import (
    PhaseLabEvent,
    PhaseLabExportManifest,
    PhaseLabIngestReport,
    PhaseLabStoreManifest,
    PhaseLabWindowIndex,
)

STORE_DB_NAME = "phase_lab.sqlite"
STORE_MANIFEST_NAME = "manifest.json"


class PhaseLabStore:
    """Small SQLite store that keeps report payloads inert."""

    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)
        self.db_path = self.store_dir / STORE_DB_NAME

    def init(self) -> PhaseLabStoreManifest:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._create_schema(connection)
        manifest = self.manifest()
        self._write_manifest(manifest)
        return manifest

    def manifest(self) -> PhaseLabStoreManifest:
        if not self.db_path.exists():
            return PhaseLabStoreManifest(
                store_path=self.store_dir.name,
                database_path=STORE_DB_NAME,
                accepted=False,
                reasons=["phase lab store has not been initialized"],
            )
        with self._connect() as connection:
            self._create_schema(connection)
            event_count = int(
                connection.execute("select count(*) from events").fetchone()[0]
            )
            windows = self.list_windows()
        latest = windows[-1].window_id if windows else None
        return PhaseLabStoreManifest(
            store_path=self.store_dir.name,
            database_path=STORE_DB_NAME,
            event_count=event_count,
            window_count=len(windows),
            latest_window_id=latest,
            accepted=True,
            settled=False,
            reasons=["phase lab store is local and non-executing"],
        )

    def ingest_payloads(
        self,
        payloads: list[tuple[dict[str, Any], str | None, str | None]],
    ) -> PhaseLabIngestReport:
        self.init()
        rejected: list[str] = []
        valid_payloads: list[tuple[dict[str, Any], str | None, str | None]] = []
        for payload, source_path, source_kind in payloads:
            if not isinstance(payload, dict):
                rejected.append(Path(source_path or "payload").name)
                continue
            valid_payloads.append((payload, source_path, source_kind))

        with self._connect() as connection:
            self._create_schema(connection)
            sequence = self._next_window_sequence(connection)
            event_offset = self._next_event_sequence(connection)
            window_id = f"phase-window:{sequence:04d}"
            events = [
                event_from_payload(
                    payload,
                    window_id=window_id,
                    sequence=event_offset + index,
                    source_path=source_path,
                    source_kind_override=source_kind,
                )
                for index, (payload, source_path, source_kind) in enumerate(valid_payloads)
            ]
            window = build_window_index(window_id, sequence, events)
            for index, event in enumerate(events):
                self._insert_event(connection, event, event_offset + index)
            self._insert_window(connection, window)
            connection.commit()

        manifest = self.manifest()
        self._write_manifest(manifest)
        return PhaseLabIngestReport(
            report_id=f"phase-lab-ingest:{window.window_id}",
            store_manifest=manifest,
            window=window,
            ingested_events=events,
            rejected_paths=sorted(rejected),
            accepted=bool(events),
            workflow_usable=True,
            settled=False,
            reasons=[
                "ingested files were stored as inert local data",
                (
                    "no embedded command, safe_command, network, repository, "
                    "or model action was executed"
                ),
            ],
        )

    def list_windows(self) -> list[PhaseLabWindowIndex]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            self._create_schema(connection)
            rows = connection.execute(
                "select window_json from windows order by sequence"
            ).fetchall()
        return [PhaseLabWindowIndex.model_validate(json.loads(row[0])) for row in rows]

    def load_events(
        self,
        window: str = "latest",
    ) -> tuple[PhaseLabWindowIndex, list[PhaseLabEvent]]:
        windows = self.list_windows()
        if not windows:
            raise ValueError("phase lab store has no windows")
        selected = self._select_window(windows, window)
        with self._connect() as connection:
            rows = connection.execute(
                "select event_json from events where window_id = ? order by sequence",
                (selected.window_id,),
            ).fetchall()
        events = [PhaseLabEvent.model_validate(json.loads(row[0])) for row in rows]
        return selected, events

    def load_all_events(self) -> list[PhaseLabEvent]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            self._create_schema(connection)
            rows = connection.execute("select event_json from events order by sequence").fetchall()
        return [PhaseLabEvent.model_validate(json.loads(row[0])) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            create table if not exists events (
              event_id text primary key,
              window_id text not null,
              sequence integer not null,
              source_kind text not null,
              schema_hint text not null,
              content_digest text not null,
              payload_json text not null,
              event_json text not null
            )
            """
        )
        connection.execute(
            """
            create table if not exists windows (
              window_id text primary key,
              sequence integer not null,
              window_json text not null
            )
            """
        )
        connection.execute("create index if not exists events_window_idx on events(window_id)")

    @staticmethod
    def _next_window_sequence(connection: sqlite3.Connection) -> int:
        value = connection.execute("select coalesce(max(sequence), -1) + 1 from windows").fetchone()
        return int(value[0])

    @staticmethod
    def _next_event_sequence(connection: sqlite3.Connection) -> int:
        value = connection.execute("select coalesce(max(sequence), -1) + 1 from events").fetchone()
        return int(value[0])

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        event: PhaseLabEvent,
        sequence: int,
    ) -> None:
        event_json = json.dumps(event.model_dump(mode="json"), sort_keys=True)
        payload_json = json.dumps(event.payload, sort_keys=True, default=str)
        connection.execute(
            """
            insert or replace into events (
              event_id, window_id, sequence, source_kind, schema_hint,
              content_digest, payload_json, event_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.window_id,
                sequence,
                event.source_kind,
                event.schema_hint,
                event.content_digest,
                payload_json,
                event_json,
            ),
        )

    @staticmethod
    def _insert_window(connection: sqlite3.Connection, window: PhaseLabWindowIndex) -> None:
        connection.execute(
            "insert or replace into windows (window_id, sequence, window_json) values (?, ?, ?)",
            (
                window.window_id,
                window.sequence,
                json.dumps(window.model_dump(mode="json"), sort_keys=True),
            ),
        )

    @staticmethod
    def _select_window(windows: list[PhaseLabWindowIndex], selector: str) -> PhaseLabWindowIndex:
        normalized = selector.lower()
        if normalized == "latest":
            return windows[-1]
        if normalized == "previous":
            if len(windows) < 2:
                return windows[-1]
            return windows[-2]
        for window in windows:
            if window.window_id == selector:
                return window
        raise ValueError(f"unknown phase lab window {selector!r}")

    def _write_manifest(self, manifest: PhaseLabStoreManifest) -> None:
        (self.store_dir / STORE_MANIFEST_NAME).write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def init_phase_lab_store(output_dir: str | Path) -> PhaseLabStoreManifest:
    """Initialize a local Phase Lab store."""

    return PhaseLabStore(output_dir).init()


def ingest_phase_lab_paths(
    store_dir: str | Path,
    paths: list[Path],
    *,
    source_kind: str | None = None,
) -> PhaseLabIngestReport:
    """Ingest JSON/YAML report files into one new Phase Lab window."""

    payloads: list[tuple[dict[str, Any], str | None, str | None]] = []
    rejected: list[str] = []
    for path in paths:
        try:
            payloads.append((_load_local_data(path), str(path), source_kind))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            rejected.append(f"{path.name}: {exc}")
    report = PhaseLabStore(store_dir).ingest_payloads(payloads)
    if rejected:
        report = report.model_copy(
            update={"rejected_paths": sorted([*report.rejected_paths, *rejected])}
        )
    return report


def ingest_phase_lab_directory(
    store_dir: str | Path,
    directory: Path,
    *,
    source_kind: str | None = None,
) -> PhaseLabIngestReport:
    """Ingest all JSON/YAML files from one local directory as one window."""

    if not directory.is_dir():
        raise ValueError(f"phase lab directory does not exist: {directory}")
    paths = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml"}
    )
    return ingest_phase_lab_paths(store_dir, paths, source_kind=source_kind)


def export_phase_lab_store(store_dir: str | Path, output_dir: str | Path) -> PhaseLabExportManifest:
    """Export sanitized local store summaries and derived diagnostic reports."""

    store = PhaseLabStore(store_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest = store.manifest()
    events = store.load_all_events()
    graph_report = build_effective_packet_graph(
        events,
        graph_id="phase-lab-export-effective-graph",
        source_window_id=manifest.latest_window_id or "adhoc",
    )
    files: list[str] = []

    def write_json(name: str, data: dict[str, Any]) -> None:
        (output / name).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        files.append(name)

    write_json("manifest.json", manifest.model_dump(mode="json"))
    write_json(
        "events.json",
        {
            "events": [event.model_dump(mode="json") for event in events],
            "absolute_paths_sanitized": True,
            "settled": False,
        },
    )
    write_json("effective_graph.json", graph_report.graph.model_dump(mode="json"))
    windows = store.list_windows()
    write_json(
        "windows.json",
        {"windows": [window.model_dump(mode="json") for window in windows], "settled": False},
    )
    if windows:
        window, window_events = store.load_events("latest")
        observation = observe_phase_window(window, window_events, graph_report.graph)
        write_json("phase_window_observation.json", observation.model_dump(mode="json"))

    return PhaseLabExportManifest(
        store_manifest=manifest,
        output_dir=output.name,
        files=sorted(files),
        absolute_paths_sanitized=True,
        accepted=True,
        settled=False,
        reasons=["phase lab export sanitizes local paths and preserves residuals"],
    )


def _load_local_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("phase lab input top-level value must be an object")
    return data
