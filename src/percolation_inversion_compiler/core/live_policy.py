"""Shared bounded-live-communication defaults."""

from __future__ import annotations

LIVE_CONNECTORS_DEFAULT_ENABLED = True
LIVE_CONNECTOR_DEFAULT_MODE = "explicit-source-bounded-candidate-intake"


def default_allow_live_connectors() -> bool:
    """Return the package-wide live connector default."""

    return LIVE_CONNECTORS_DEFAULT_ENABLED


def live_default_mode() -> str:
    """Return the stable public label for the live connector default."""

    return LIVE_CONNECTOR_DEFAULT_MODE


def live_default_safety_invariant() -> str:
    """Return the shared safety invariant for bounded default-live intake."""

    return (
        "live connectors are bounded and candidate-only by default when an explicit "
        "source is supplied"
    )


def live_default_non_authorities() -> list[str]:
    """Return capabilities not granted by default-live communication."""

    return [
        "no background crawling",
        "no autonomous polling",
        "no arbitrary shell execution",
        "no repository mutation",
        "no hidden promotion from accepted or workflow_usable to settled",
    ]
