"""Reported occurrence time is distinct from work creation/service-log time."""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException


def event_context(data, *, default_timezone, existing=None):
    existing = existing or {}
    zone_name = str(data.get("event_timezone") or existing.get("event_timezone") or default_timezone)
    try:
        zone = ZoneInfo(zone_name)
    except (ValueError, ZoneInfoNotFoundError):
        raise HTTPException(400, "event_timezone must be an IANA timezone")

    def parse(name):
        value = data[name] if name in data else existing.get(name)
        if value is None or value == "":
            return None
        try:
            if not isinstance(value, datetime) and "T" not in str(value) and " " not in str(value):
                raise ValueError()
            stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if name not in data and not stamp.tzinfo and existing.get("event_timezone") and existing["event_timezone"] != zone_name:
                stamp = stamp.replace(tzinfo=ZoneInfo(existing["event_timezone"]))
            stamp = stamp.astimezone(zone).replace(tzinfo=None) if stamp.tzinfo else stamp
            if stamp.year < 1000:
                raise ValueError()
            return stamp
        except (ValueError, TypeError):
            raise HTTPException(400, f"{name} must be an ISO datetime")

    start, end = parse("event_started_at"), parse("event_ended_at")
    if end is not None and (start is None or end < start):
        raise HTTPException(400, "event end requires a start and must not precede it")
    precision = str(data.get("event_time_precision") or existing.get("event_time_precision") or "MINUTE")
    if precision not in {"SECOND", "MINUTE", "APPROXIMATE", "UNKNOWN"}:
        raise HTTPException(400, "Invalid event time precision")
    return {"event_started_at": start, "event_ended_at": end,
            "event_timezone": zone_name if start else None,
            "event_time_precision": precision if start else "UNKNOWN"}


def incident_snapshot(order):
    """Immutable-at-service-time report context; never a diagnosis/training label."""
    return {key: order.get(key) for key in (
        "id", "device_id", "module_id", "source_alert_id", "report_origin",
        "title", "created_by", "created_at", "assigned_to",
        "description", "event_started_at", "event_ended_at", "event_timezone", "event_time_precision",
    )} | {"label_status": "UNREVIEWED", "cause_status": "UNKNOWN"}
