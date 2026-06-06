"""Pint-backed unit validation helpers."""

from __future__ import annotations

from typing import Any


def assert_compatible_units(left_unit: str, right_unit: str) -> bool:
    try:
        import pint
    except ImportError as exc:  # pragma: no cover - exercised without science extra
        raise RuntimeError("Install the 'science' extra to use unit adapters.") from exc

    registry: Any = pint.UnitRegistry()
    left = registry.Quantity(1.0, left_unit)
    right = registry.Quantity(1.0, right_unit)
    return bool(left.check(right.dimensionality))
