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
    RuntimeEvent,
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
}
_SELECT_SQL = {
    "states": "SELECT payload FROM states WHERE state_id = ?",
    "events": "SELECT payload FROM events WHERE event_id = ?",
    "runs": "SELECT payload FROM runs WHERE run_id = ?",
    "certificates": "SELECT payload FROM certificates WHERE certificate_id = ?",
}
_SELECT_ALL_SQL = {
    "states": "SELECT payload FROM states ORDER BY payload",
    "events": "SELECT payload FROM events ORDER BY payload",
    "runs": "SELECT payload FROM runs ORDER BY payload",
    "certificates": "SELECT payload FROM certificates ORDER BY payload",
}
_UPSERT_SQL = {
    "states": "INSERT OR REPLACE INTO states (state_id, payload) VALUES (?, ?)",
    "events": "INSERT OR REPLACE INTO events (event_id, payload) VALUES (?, ?)",
    "runs": "INSERT OR REPLACE INTO runs (run_id, payload) VALUES (?, ?)",
    "certificates": ("INSERT OR REPLACE INTO certificates (certificate_id, payload) VALUES (?, ?)"),
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
