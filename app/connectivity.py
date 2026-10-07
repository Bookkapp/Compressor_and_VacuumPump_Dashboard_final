from __future__ import annotations

from datetime import datetime
from typing import Any


OFFLINE_AFTER_SECONDS = 30 * 60


def connection_state(last_seen: Any, device_uid: str | None = None, *, now: datetime | None = None, telemetry_source: str | None = None) -> tuple[str, int | None]:
    if not last_seen:
        return "OFFLINE", None
    if isinstance(last_seen, str):
        try:
            last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        except ValueError:
            return "OFFLINE", None
    else:
        last_seen_dt = last_seen

    current = now if now is not None else datetime.now(last_seen_dt.tzinfo)
    elapsed = max(0, (current - last_seen_dt).total_seconds())
    seconds = int(elapsed)
    if elapsed > OFFLINE_AFTER_SECONDS:
        return "OFFLINE", seconds
    if telemetry_source == "compressor" or (telemetry_source is None and str(device_uid or "").lower().startswith("compressor:")):
        return "ONLINE", seconds
    if elapsed <= 15:
        return "ONLINE", seconds
    if elapsed <= 90:
        return "STALE", seconds
    return "NO_SIGNAL", seconds


def operational_status(status: str, signal_state: str) -> str:
    """Current display status; retained condition/ML evidence stays unchanged."""
    if signal_state == "OFFLINE":
        return "OFFLINE"
    return "NORMAL" if status == "MONITORING" else status
