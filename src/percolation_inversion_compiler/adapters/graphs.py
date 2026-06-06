"""NetworkX-backed graph helpers kept outside the lean core."""

from __future__ import annotations


def shortest_path_lengths(edges: list[tuple[str, str]], source: str) -> dict[str, int]:
    try:
        import networkx as nx  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised without science extra
        raise RuntimeError("Install the 'science' extra to use graph adapters.") from exc

    graph = nx.DiGraph()
    graph.add_edges_from(edges)
    lengths = nx.single_source_shortest_path_length(graph, source)
    return {str(node): int(distance) for node, distance in lengths.items()}
