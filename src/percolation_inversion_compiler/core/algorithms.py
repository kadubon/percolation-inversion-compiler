"""Finite statistical, graph, and certificate helper algorithms."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from math import exp, log, sqrt


def dkw_radius(sample_size: int, alpha: float) -> float:
    """Dvoretzky-Kiefer-Wolfowitz-Massart radius for an iid split certificate."""

    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    return sqrt(log(2.0 / alpha) / (2.0 * sample_size))


def good_turing_unseen(counts: Sequence[int]) -> float:
    """Good-Turing unseen-mass estimate ``N_1 / N`` for finite observations."""

    total = sum(counts)
    if total <= 0:
        raise ValueError("counts must contain positive total mass")
    singletons = sum(1 for count in counts if count == 1)
    return singletons / total


def empirical_bernstein_radius(
    values: Sequence[float], alpha: float, upper_bound: float = 1.0
) -> float:
    """A finite empirical Bernstein-style radius for bounded observations."""

    n = len(values)
    if n <= 1:
        raise ValueError("at least two observations are required")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    log_term = log(2.0 / alpha)
    return sqrt(2.0 * variance * log_term / n) + 7.0 * upper_bound * log_term / (3.0 * (n - 1))


def split_lower_confidence_bound(
    values: Sequence[float], alpha: float, lower_bound: float = 0.0
) -> float:
    """Lower confidence bound using the empirical Bernstein radius."""

    mean = sum(values) / len(values)
    return max(lower_bound, mean - empirical_bernstein_radius(values, alpha))


def finite_difference_interval(
    baseline: float,
    perturbed: float,
    epsilon: float,
    *,
    residual: float = 0.0,
) -> tuple[float, float]:
    """Two-sided interval for a finite-difference response certificate."""

    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    estimate = (perturbed - baseline) / epsilon
    width = abs(residual) / epsilon
    return estimate - width, estimate + width


def gibbs_distribution(energies: dict[str, float], beta: float = 1.0) -> dict[str, float]:
    """Finite Gibbs distribution over a declared compatible configuration space."""

    if not energies:
        raise ValueError("energies must not be empty")
    weights = {key: exp(-beta * energy) for key, energy in energies.items()}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Gibbs normalizer must be positive")
    return {key: value / total for key, value in weights.items()}


def expected_value(distribution: dict[str, float], observable: Callable[[str], float]) -> float:
    """Expected value of a bounded observable over a finite distribution."""

    return sum(probability * observable(state) for state, probability in distribution.items())


def trapezoid_integral(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Finite trapezoidal integral."""

    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("xs and ys must have the same length >= 2")
    total = 0.0
    for left_x, right_x, left_y, right_y in zip(
        xs[:-1],
        xs[1:],
        ys[:-1],
        ys[1:],
        strict=True,
    ):
        if right_x < left_x:
            raise ValueError("xs must be sorted nondecreasing")
        total += 0.5 * (right_y + left_y) * (right_x - left_x)
    return total
