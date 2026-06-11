from __future__ import annotations
from datetime import datetime, timezone


def parse_utc(s: str) -> datetime:
    """Parse a datetime stored as ISO format.

    Old records (pre-2026 fix) are naive; treat them as UTC. New records are
    timezone-aware. Always returns an aware datetime in UTC.
    """
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with timezone offset."""
    return datetime.now(timezone.utc).isoformat()
