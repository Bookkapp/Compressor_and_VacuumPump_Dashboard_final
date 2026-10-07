"""On-demand, read-only historical browsing. Source time bounds precede LIMIT.

Wide Compressor reads are shared between module requests. Cached values are
raw source rows; callers always decode their own module, preserving nulls.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
import logging
import math
import re
import threading
import time
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .config import settings
from .db import fetch_one
from .telemetry_sources import telemetry_sources, _datetime, _identifier

SIGNALS = {
    "compressor": ("hp_1st", "lp_1st", "hp_2nd", "lp_2nd", "temperature_hi", "temperature_lo", "valve", "busy", "sv"),
    "vacuum": ("temperature_c", "pressure_kpa", "current_a", "vibration", "accel_x", "accel_y", "accel_z"),
}
_cache: OrderedDict = OrderedDict()
_stats: OrderedDict = OrderedDict()
_lock = threading.Lock()
_flights = [threading.Lock() for _ in range(64)]
log = logging.getLogger("adi.history_browser")


def history_window(start: str | None, end: str | None):
    if not start and not end:
        return None, None
    if not start or not end:
        raise HTTPException(422, "Select both start and end date/time")
    try:
        def parse(value):
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo:
                stamp = stamp.astimezone(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
            return stamp
        first, last = parse(start), parse(end)
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid date/time")
    if last <= first or last - first > timedelta(days=31):
        raise HTTPException(422, "Choose an increasing time range of up to 31 days")
    return first, last


def _remember(cache, key, value, capacity):
    with _lock:
        cache[key] = (time.monotonic() + 15, value)
        cache.move_to_end(key)
        while len(cache) > capacity:
            cache.popitem(last=False)


def _cached(cache, key):
    with _lock:
        item = cache.get(key)
        if item and item[0] > time.monotonic():
            cache.move_to_end(key)
            return item[1]
    return None


def source_window(source, source_key, first, last, limit, offset, chart):
    window_key = (source, source_key, first, last)
    key = (*window_key, limit, offset, chart)
    # Coalesce across tabs and across Compressor modules, without serializing
    # unrelated source identities behind the cache lock during network I/O.
    with _flights[hash(window_key) % len(_flights)]:
        cached = _cached(_cache, key)
        if cached is not None:
            return cached
        if source == "compressor":
            table = f"{_identifier(settings.compressor_schema, 'schema')}.{_identifier(settings.compressor_table, 'table')}"
            identity = _identifier(settings.compressor_machine_column, "machine column")
            stamp = _identifier(settings.compressor_timestamp_column, "time column")
        else:
            table = f"{_identifier(settings.vacuum_schema, 'schema')}.{_identifier(settings.vacuum_table, 'table')}"
            identity = _identifier(settings.vacuum_device_column, "device column")
            stamp = "`recorded_at`"
        where = f"{identity} = %s AND {stamp} IS NOT NULL"
        params = [source_key]
        if first is not None:
            where += f" AND {stamp} >= %s AND {stamp} < %s"
            params.extend((first, last))
        query = lambda sql, args: telemetry_sources._query(source, sql, tuple(args), history=True)
        if chart and first is None:
            # "Latest history" is a bounded newest-sample read, not a scan of
            # every year in the source. Explicit date ranges use coverage sampling.
            rows = query(f"SELECT * FROM {table} WHERE {where} ORDER BY {stamp} DESC, id DESC LIMIT %s", [*params, limit])
            rows.reverse()
            column = settings.compressor_timestamp_column if source == "compressor" else "recorded_at"
            result = {"raw_rows": rows, "total": len(rows), "first_at": rows[0][column] if rows else None,
                      "last_at": rows[-1][column] if rows else None, "sampled": False,
                      "sampling": "raw", "bucket_seconds": None, "offset": 0, "limit": limit, "latest_limited": True}
            _remember(_cache, key, result, 16)
            return result
        stats = _cached(_stats, window_key)
        if stats is None:
            stats = query(f"SELECT COUNT(*) AS total, MIN({stamp}) AS first_at, MAX({stamp}) AS last_at FROM {table} WHERE {where}", params)[0]
            _remember(_stats, window_key, stats, 32)
        total = int(stats["total"])
        sampled = chart and total > limit
        bucket_seconds = None
        if sampled:
            lower, upper = _datetime(stats["first_at"]), _datetime(stats["last_at"])
            span_us = max(1, round((upper - lower).total_seconds() * 1_000_000) + 1)
            width_us = max(1, math.ceil(span_us / (limit // 2)))
            bucket_seconds = width_us / 1_000_000
            # Select real first/last readings in every time bucket. Sort by
            # source timestamp + PK (IDs alone need not follow source time).
            packed = f"CONCAT(DATE_FORMAT({stamp}, '%%Y%%m%%d%%H%%i%%s%%f'), LPAD(id, 20, '0'))"
            rows = query(f"""
                SELECT r.* FROM {table} r JOIN (
                    SELECT CAST(RIGHT(MIN({packed}), 20) AS UNSIGNED) AS first_id,
                           CAST(RIGHT(MAX({packed}), 20) AS UNSIGNED) AS last_id
                    FROM {table} WHERE {where}
                    GROUP BY FLOOR(TIMESTAMPDIFF(MICROSECOND, %s, {stamp}) / %s)
                ) buckets ON r.id = buckets.first_id OR r.id = buckets.last_id
                ORDER BY r.{stamp} ASC, r.id ASC
            """, [*params, lower, width_us])
        else:
            rows = query(f"SELECT * FROM {table} WHERE {where} ORDER BY {stamp} DESC, id DESC LIMIT %s OFFSET %s", [*params, limit, offset])
            if chart:
                rows.reverse()
        result = {"raw_rows": rows, **stats, "sampled": sampled,
                  "sampling": "time_bucket_first_last" if sampled else "raw",
                  "bucket_seconds": bucket_seconds, "offset": offset, "limit": limit}
        _remember(_cache, key, result, 16)
        return result


def browse_history(device_id, module_id, start=None, end=None, limit=250, offset=0, chart=False, signals=None):
    first, last = history_window(start, end)
    if not 1 <= limit <= (2000 if chart else 1000) or (chart and limit < 2) or offset < 0 or (chart and offset):
        raise HTTPException(422, "Invalid history page size or offset")
    module = fetch_one("""
        SELECT d.machine_code, m.id AS module_id, m.module_code, m.module_name,
               m.telemetry_source, m.source_device_key
        FROM pm_devices d JOIN pm_modules m ON m.device_id = d.id
        WHERE d.id = %s AND m.id = %s
    """, (device_id, module_id))
    if not module:
        raise HTTPException(404, "Module does not belong to the selected machine")
    source, source_key = module["telemetry_source"], module["source_device_key"]
    module_match = re.fullmatch(r"compressor-m([1-8])", module["module_code"])
    if source not in SIGNALS or not source_key or (source == "compressor" and not module_match) or (source == "vacuum" and module["module_code"] != "vacuum-pump"):
        raise HTTPException(422, "Module has no mapped telemetry source")
    selected = list(dict.fromkeys(signals.split(","))) if signals else list(SIGNALS[source])
    if any(key not in SIGNALS[source] for key in selected):
        raise HTTPException(422, "Signal does not belong to this module family")
    if not telemetry_sources.source_configured(source):
        raise HTTPException(503, "Telemetry source is not configured")
    try:
        result = source_window(source, str(source_key), first, last, limit, offset, chart)
    except Exception:
        log.exception("Historical source read failed (%s)", source)
        raise HTTPException(503, "Could not read historical telemetry; please retry")
    rows = []
    for raw in result["raw_rows"]:
        if source == "vacuum":
            raw = {**raw, "devices_id": raw.get(settings.vacuum_device_column)}
            sample = telemetry_sources._vacuum_sample(raw)
        else:
            samples = telemetry_sources._compressor_samples(raw, int(module_match.group(1)), include_empty=True)
            sample = samples[0] if samples else None
        stamp = sample.recorded_at if sample else _datetime(raw.get(settings.compressor_timestamp_column))
        if stamp is None:
            continue
        values = sample.history_row(device_id, module_id) if sample else {}
        row = {"recorded_at": stamp.replace(tzinfo=ZoneInfo(settings.app_timezone)).isoformat(),
               **{key: values.get(key) for key in selected}}
        if not chart:
            row.update(id=raw.get("id"), machine_code=module["machine_code"], module_name=module["module_name"], source=source)
            if source == "compressor":
                row.update(operating_status=values.get("operating_status"), set_valve_status=values.get("set_valve_status"))
        rows.append(row)
    return {key: value for key, value in result.items() if key != "raw_rows"} | {
        "rows": rows, "source": source, "module_id": module_id,
        "timezone": settings.app_timezone, "start": first, "end": last,
    }
