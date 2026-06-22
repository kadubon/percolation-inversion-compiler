from __future__ import annotations

from pathlib import Path

from percolation_inversion_compiler.phase_lab import (
    PhaseLabStore,
    build_effective_packet_graph,
    ingest_phase_lab_paths,
    init_phase_lab_store,
    observe_phase_window,
)

ROOT = Path(__file__).resolve().parents[1]


def test_phase_lab_store_ingests_local_reports_without_settlement(tmp_path: Path) -> None:
    store_dir = tmp_path / "phase-lab"
    manifest = init_phase_lab_store(store_dir)
    assert manifest.accepted is True
    assert manifest.settled is False

    ingest = ingest_phase_lab_paths(
        store_dir,
        [ROOT / "examples" / "phase_lab" / "runtime_report_1.json"],
    )
    assert ingest.accepted is True
    assert ingest.executed_command_count == 0
    assert ingest.settled is False
    assert ingest.ingested_events[0].source_path == "runtime_report_1.json"

    store = PhaseLabStore(store_dir)
    window, events = store.load_events("latest")
    graph = build_effective_packet_graph(events).graph
    observation = observe_phase_window(window, events, graph)
    assert observation.accepted_packet_count == 1
    assert observation.settled is False
    assert graph.accepted_packet_capital == 1
    assert graph.non_contributing_volume == 0
