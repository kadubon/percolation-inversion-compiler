"""UTC freshness helpers shared by public protocol boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum


class FreshnessState(StrEnum):
    FRESH = "fresh"
    EXPIRED = "expired"
    INVALID = "invalid"
    UNKNOWN = "unknown"


def parse_utc_datetime(value: str | None) -> datetime | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip()
    if normalized.lower() == "expired":
        return datetime.min.replace(tzinfo=UTC)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def freshness_state(
    expires_at: str | None,
    *,
    reference_time: datetime | None = None,
    required: bool = False,
) -> FreshnessState:
    if expires_at in (None, ""):
        return FreshnessState.UNKNOWN if required else FreshnessState.FRESH
    parsed = parse_utc_datetime(expires_at)
    if parsed is None:
        return FreshnessState.INVALID
    reference = (reference_time or datetime.now(UTC)).astimezone(UTC)
    return FreshnessState.EXPIRED if parsed <= reference else FreshnessState.FRESH


def is_expired_or_invalid(
    expires_at: str | None,
    *,
    reference_time: datetime | None = None,
) -> bool:
    return freshness_state(expires_at, reference_time=reference_time) in {
        FreshnessState.EXPIRED,
        FreshnessState.INVALID,
    }
