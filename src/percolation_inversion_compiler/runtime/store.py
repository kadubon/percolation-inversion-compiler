"""Persistent runtime store implementations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from percolation_inversion_compiler.runtime.records import (
    AccelerationCertificate,
    AgentPopulationState,
    CollectivePhaseCertificate,
    RouteExecutionBatch,
    RuntimeEvent,
    RuntimeExecutionReport,
    RuntimeRunReport,
    RuntimeState,
    RuntimeStoreRecord,
    RuntimeStoreSnapshot,
)

_COUNT_SQL = {
    "states": "SELECT COUNT(*) FROM states",
    "events": "SELECT COUNT(*) FROM events",
    "runs": "SELECT COUNT(*) FROM runs",
    "certificates": "SELECT COUNT(*) FROM certificates",
    "execution_reports": "SELECT COUNT(*) FROM execution_reports",
    "route_batches": "SELECT COUNT(*) FROM route_batches",
    "population_snapshots": "SELECT COUNT(*) FROM population_snapshots",
    "collective_phase_certificates": "SELECT COUNT(*) FROM collective_phase_certificates",
    "verified_packets": "SELECT COUNT(*) FROM verified_packets",
    "edge_certificates": "SELECT COUNT(*) FROM edge_certificates",
    "packet_lineage": "SELECT COUNT(*) FROM packet_lineage",
}
_SELECT_SQL = {
    "states": "SELECT payload FROM states WHERE state_id = ?",
    "events": "SELECT payload FROM events WHERE event_id = ?",
    "runs": "SELECT payload FROM runs WHERE run_id = ?",
    "certificates": "SELECT payload FROM certificates WHERE certificate_id = ?",
    "execution_reports": "SELECT payload FROM execution_reports WHERE report_id = ?",
    "route_batches": "SELECT payload FROM route_batches WHERE batch_id = ?",
    "population_snapshots": "SELECT payload FROM population_snapshots WHERE population_id = ?",
    "collective_phase_certificates": (
        "SELECT payload FROM collective_phase_certificates WHERE certificate_id = ?"
    ),
    "verified_packets": "SELECT payload FROM verified_packets WHERE packet_id = ?",
    "edge_certificates": "SELECT payload FROM edge_certificates WHERE certificate_id = ?",
    "packet_lineage": "SELECT payload FROM packet_lineage WHERE lineage_id = ?",
}
_SELECT_ALL_SQL = {
    "states": "SELECT payload FROM states ORDER BY payload",
    "events": "SELECT payload FROM events ORDER BY payload",
    "runs": "SELECT payload FROM runs ORDER BY payload",
    "certificates": "SELECT payload FROM certificates ORDER BY payload",
    "execution_reports": "SELECT payload FROM execution_reports ORDER BY payload",
    "route_batches": "SELECT payload FROM route_batches ORDER BY payload",
    "population_snapshots": "SELECT payload FROM population_snapshots ORDER BY payload",
    "collective_phase_certificates": (
        "SELECT payload FROM collective_phase_certificates ORDER BY payload"
    ),
    "verified_packets": "SELECT payload FROM verified_packets ORDER BY payload",
    "edge_certificates": "SELECT payload FROM edge_certificates ORDER BY payload",
    "packet_lineage": "SELECT payload FROM packet_lineage ORDER BY payload",
}
_UPSERT_SQL = {
    "states": "INSERT OR REPLACE INTO states (state_id, payload) VALUES (?, ?)",
    "events": "INSERT OR REPLACE INTO events (event_id, payload) VALUES (?, ?)",
    "runs": "INSERT OR REPLACE INTO runs (run_id, payload) VALUES (?, ?)",
    "certificates": ("INSERT OR REPLACE INTO certificates (certificate_id, payload) VALUES (?, ?)"),
    "execution_reports": (
        "INSERT OR REPLACE INTO execution_reports (report_id, payload) VALUES (?, ?)"
    ),
    "route_batches": "INSERT OR REPLACE INTO route_batches (batch_id, payload) VALUES (?, ?)",
    "population_snapshots": (
        "INSERT OR REPLACE INTO population_snapshots (population_id, payload) VALUES (?, ?)"
    ),
    "collective_phase_certificates": (
        "INSERT OR REPLACE INTO collective_phase_certificates "
        "(certificate_id, payload) VALUES (?, ?)"
    ),
    "verified_packets": (
        "INSERT OR REPLACE INTO verified_packets (packet_id, payload) VALUES (?, ?)"
    ),
    "edge_certificates": (
        "INSERT OR REPLACE INTO edge_certificates (certificate_id, payload) VALUES (?, ?)"
    ),
    "packet_lineage": "INSERT OR REPLACE INTO packet_lineage (lineage_id, payload) VALUES (?, ?)",
}


class SQLiteRuntimeStore:
    """SQLite-backed append-only store for ECPT runtime state."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.initialize()

    def initialize(self) -> RuntimeStoreRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS states "
                "(state_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS events "
                "(event_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS certificates "
                "(certificate_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_reports "
                "(report_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS route_batches "
                "(batch_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS population_snapshots "
                "(population_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS collective_phase_certificates "
                "(certificate_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS verified_packets "
                "(packet_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS edge_certificates "
                "(certificate_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS packet_lineage "
                "(lineage_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.commit()
        return self.record()

    def append_state(self, state: RuntimeState) -> None:
        self._upsert("states", "state_id", state.state_id, state.model_dump(mode="json"))

    def append_event(self, event: RuntimeEvent) -> None:
        self._upsert("events", "event_id", event.event_id, event.model_dump(mode="json"))

    def append_run(self, run: RuntimeRunReport) -> None:
        self._upsert("runs", "run_id", run.run_id, run.model_dump(mode="json"))

    def append_certificate(self, certificate: AccelerationCertificate) -> None:
        self._upsert(
            "certificates",
            "certificate_id",
            certificate.certificate_id,
            certificate.model_dump(mode="json"),
        )

    def append_execution_report(self, report: RuntimeExecutionReport) -> None:
        self._upsert(
            "execution_reports",
            "report_id",
            report.report_id,
            report.model_dump(mode="json"),
        )

    def append_route_batch(self, batch: RouteExecutionBatch) -> None:
        self._upsert(
            "route_batches",
            "batch_id",
            batch.batch_id,
            batch.model_dump(mode="json"),
        )

    def append_population(self, population: AgentPopulationState) -> None:
        self._upsert(
            "population_snapshots",
            "population_id",
            population.population_id,
            population.model_dump(mode="json"),
        )

    def append_collective_certificate(self, certificate: CollectivePhaseCertificate) -> None:
        self._upsert(
            "collective_phase_certificates",
            "certificate_id",
            certificate.certificate_id,
            certificate.model_dump(mode="json"),
        )

    def load_state(self, state_id: str) -> RuntimeState | None:
        payload = self._load("states", "state_id", state_id)
        return None if payload is None else RuntimeState.model_validate(payload)

    def snapshot(self, *, snapshot_id: str = "runtime-store-snapshot") -> RuntimeStoreSnapshot:
        states = [RuntimeState.model_validate(item) for item in self._load_all("states")]
        events = [RuntimeEvent.model_validate(item) for item in self._load_all("events")]
        runs = [RuntimeRunReport.model_validate(item) for item in self._load_all("runs")]
        certificates = [
            AccelerationCertificate.model_validate(item) for item in self._load_all("certificates")
        ]
        payload = {
            "states": [state.model_dump(mode="json") for state in states],
            "events": [event.model_dump(mode="json") for event in events],
            "runs": [run.model_dump(mode="json") for run in runs],
            "certificates": [certificate.model_dump(mode="json") for certificate in certificates],
        }
        return RuntimeStoreSnapshot(
            snapshot_id=snapshot_id,
            states=states,
            events=events,
            runs=runs,
            certificates=certificates,
            aggregate_sha256=_stable_store_digest(payload),
        )

    def record(self) -> RuntimeStoreRecord:
        with closing(self._connect()) as connection:
            counts = {
                table: int(connection.execute(statement).fetchone()[0])
                for table, statement in _COUNT_SQL.items()
            }
        return RuntimeStoreRecord(
            store_id=f"sqlite-runtime-store:{self.path.name}",
            store_ref=self.path.name,
            state_count=counts["states"],
            event_count=counts["events"],
            run_count=counts["runs"],
            certificate_count=counts["certificates"],
            execution_report_count=counts["execution_reports"],
            route_batch_count=counts["route_batches"],
            population_snapshot_count=counts["population_snapshots"],
            collective_certificate_count=counts["collective_phase_certificates"],
            verified_packet_count=counts["verified_packets"],
            edge_certificate_count=counts["edge_certificates"],
            packet_lineage_count=counts["packet_lineage"],
            accepted=True,
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _upsert(self, table: str, key_name: str, key: str, payload: dict[str, Any]) -> None:
        del key_name
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with closing(self._connect()) as connection:
            connection.execute(_UPSERT_SQL[table], (key, encoded))
            connection.commit()

    def _load(self, table: str, key_name: str, key: str) -> dict[str, Any] | None:
        del key_name
        with closing(self._connect()) as connection:
            row = connection.execute(_SELECT_SQL[table], (key,)).fetchone()
        if row is None:
            return None
        payload = json.loads(str(row[0]))
        return payload if isinstance(payload, dict) else None

    def _load_all(self, table: str) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(_SELECT_ALL_SQL[table]).fetchall()
        return [payload for row in rows if isinstance((payload := json.loads(str(row[0]))), dict)]


def _stable_store_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()
