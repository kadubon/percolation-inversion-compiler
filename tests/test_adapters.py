from __future__ import annotations

import importlib.util

import pytest

from percolation_inversion_compiler.adapters.optimization import solve_linear_release


def test_linear_release_adapter_is_core_deterministic() -> None:
    assert solve_linear_release([1.0, -2.0], [0.0, 1.0], [3.0, 4.0]) == 1.0


def test_networkx_adapter_when_science_extra_present() -> None:
    if importlib.util.find_spec("networkx") is None:
        pytest.skip("networkx science extra is not installed")
    from percolation_inversion_compiler.adapters.graphs import shortest_path_lengths

    assert shortest_path_lengths([("a", "b"), ("b", "c")], "a") == {
        "a": 0,
        "b": 1,
        "c": 2,
    }


def test_pint_adapter_when_science_extra_present() -> None:
    if importlib.util.find_spec("pint") is None:
        pytest.skip("pint science extra is not installed")
    from percolation_inversion_compiler.adapters.units import assert_compatible_units

    assert assert_compatible_units("meter", "kilometer")
