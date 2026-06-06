"""Optimal-transport adapters."""

from __future__ import annotations


def sinkhorn_transport(
    source: list[float],
    target: list[float],
    cost: list[list[float]],
    *,
    regularization: float = 1.0,
) -> list[list[float]]:
    try:
        import ot  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised without ot extra
        raise RuntimeError("Install the 'ot' extra to use transport adapters.") from exc

    plan = ot.sinkhorn(source, target, cost, regularization)
    return [[float(value) for value in row] for row in plan.tolist()]
