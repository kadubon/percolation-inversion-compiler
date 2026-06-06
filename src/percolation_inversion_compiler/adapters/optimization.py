"""Finite LP adapter for release-style certificates."""

from __future__ import annotations


def solve_linear_release(
    objective: list[float],
    lower_bounds: list[float],
    upper_bounds: list[float],
) -> float:
    """Solve a bounded separable linear release objective.

    This intentionally keeps the public adapter simple and deterministic. More
    complex constrained LPs should be represented as external proof obligations
    unless a full matrix certificate is supplied.
    """

    if len(objective) != len(lower_bounds) or len(objective) != len(upper_bounds):
        raise ValueError("objective and bound vectors must have equal length")
    value = 0.0
    for coeff, lower, upper in zip(objective, lower_bounds, upper_bounds, strict=True):
        if lower > upper:
            raise ValueError("lower bound exceeds upper bound")
        value += coeff * (upper if coeff >= 0 else lower)
    return value
