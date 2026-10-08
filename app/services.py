from __future__ import annotations

import math
import json
import random
import re
import threading
from functools import wraps
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .auth import verify_password
from .cache import cache
from .config import settings
from .connectivity import connection_state, operational_status
from .db import connection, execute, execute_many, fetch_all, fetch_one, json_dumps
from .diagnostics import compute_diagnostics, normalize_telemetry
from .telemetry_sources import ExternalTelemetrySample, telemetry_sources


CONDITION_RANK = {
    "OFFLINE": 0,
    "NORMAL": 1,
    "WATCH": 3,
    "UNDER_MAINTENANCE": 4,
    "WARNING": 5,
    "MAINTENANCE_REQUIRED": 6,
}

VALID_MODULE_STATUSES = {"NORMAL", "WARNING", "MAINTENANCE_REQUIRED", "UNDER_MAINTENANCE", "OFFLINE"}

_shared_read_locks = {key: threading.RLock() for key in ("devices", "summary")}

def coalesced_read(key):
    """Only one metadata query fills an expired shared snapshot at a time."""
    def decorate(function):
        @wraps(function)
        def read(*args, **kwargs):
            value=cache.get(key)
            if value is not None:return value
            with _shared_read_locks[key]:
                value=cache.get(key)
                return value if value is not None else function(*args, **kwargs)
        return read
    return decorate

METADATA_KEYS = {
    "device_id",
    "deviceId",
    "device_uid",
    "machine_code",
    "machine_name",
    "display_name",
    "module",
    "module_code",
    "module_name",
    "timestamp",
    "recorded_at",
    "firmware_version",
    "mac",
    "units",
}

DEFAULT_UNITS = {
    "temperature": "C",
    "temperature_c": "C",
    "pressure": "kPa",
    "pressure_kpa": "kPa",
    "current": "A",
    "current_a": "A",
    "vibration": "G rms",
    "ax": "g",
    "ay": "g",
    "az": "g",
    "accel.x": "g",
    "accel.y": "g",
    "accel.z": "g",
    "gx": "dps",
    "gy": "dps",
    "gz": "dps",
    "gyro.x": "dps",
    "gyro.y": "dps",
    "gyro.z": "dps",
}


def public_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row.get("full_name"),
        "role": row["role"],
        "is_active": bool(row.get("is_active")),
    }


def json_loads(value: Any, fallback: Any = None) -> Any:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def public_module(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    item["thresholds"] = json_loads(item.pop("thresholds_json", None), {})
    return item


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    row = fetch_one("SELECT * FROM pm_users WHERE username = %s AND is_active = 1", (username,))
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return row


def get_user(user_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM pm_users WHERE id = %s AND is_active = 1", (user_id,))


def list_users() -> list[dict[str, Any]]:
    return [
        public_user(row)
        for row in fetch_all("SELECT * FROM pm_users WHERE is_active = 1 ORDER BY role, username")
    ]


def numeric_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def metric_unit(metric_key: str, units: dict[str, Any]) -> str | None:
    return (
        units.get(metric_key)
        or units.get(metric_key.replace(".", "_"))
        or DEFAULT_UNITS.get(metric_key)
        or DEFAULT_UNITS.get(metric_key.replace(".", "_"))
    )


def flatten_metrics(payload: dict[str, Any], prefix: str = "") -> list[tuple[str, float, str, str | None]]:
    rows: list[tuple[str, float, str]] = []
    units = payload.get("units") if isinstance(payload.get("units"), dict) else {}

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if not path and key in METADATA_KEYS:
                    continue
                if key == "units":
                    continue
                safe_key = str(key).strip().replace(" ", "_")
                child_path = f"{path}.{safe_key}" if path else safe_key
                walk(child, child_path)
            return

        metric_value = numeric_or_none(value)
        if metric_value is None:
            return
        metric_key = path[:160]
        rows.append((metric_key, metric_value, path[:220]))

    walk(payload, prefix)
    normalized: list[tuple[str, float, str, str | None]] = []
    for metric_key, metric_value, source_key in rows:
        normalized.append((metric_key, metric_value, source_key, metric_unit(metric_key, units)))
    return normalized


def ensure_device(sample: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO pm_devices
            (device_uid, machine_code, display_name, firmware_version, status, first_seen, last_seen)
        VALUES (%s, %s, %s, %s, 'NORMAL', NOW(), NOW())
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            firmware_version = COALESCE(VALUES(firmware_version), firmware_version),
            last_seen = NOW(),
            status = IF(status = 'OFFLINE', 'NORMAL', status)
        """,
        (
            sample["device_uid"],
            sample["machine_code"],
            sample["display_name"],
            sample.get("firmware_version"),
        ),
    )


def ensure_module(device_id: int, sample: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO pm_modules (device_id, module_code, module_name, module_type, status)
        VALUES (%s, %s, %s, %s, 'NORMAL')
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            module_name = VALUES(module_name),
            status = IF(status = 'OFFLINE', 'NORMAL', status)
        """,
        (
            device_id,
            sample["module_code"],
            sample["module_name"],
            sample["module_name"],
        ),
    )


def module_history(module_id: int, limit: int = 256) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT *
        FROM pm_sensor_readings
        WHERE module_id = %s
        ORDER BY recorded_at DESC, id DESC
        LIMIT %s
        """,
        (module_id, limit),
    )
    rows.reverse()
    return rows


def insert_reading(device_id: int, module_id: int, sample: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO pm_sensor_readings
            (device_id, module_id, recorded_at, source,
             temperature_c, pressure_kpa, current_a,
             accel_x, accel_y, accel_z, vibration,
             gyro_x, gyro_y, gyro_z, raw_payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            device_id,
            module_id,
            sample["recorded_at"],
            sample["source"],
            sample.get("temperature_c"),
            sample.get("pressure_kpa"),
            sample.get("current_a"),
            sample.get("accel_x"),
            sample.get("accel_y"),
            sample.get("accel_z"),
            sample.get("vibration"),
            sample.get("gyro_x"),
            sample.get("gyro_y"),
            sample.get("gyro_z"),
            json_dumps(sample.get("raw_payload") or {}),
        ),
    )


def insert_sensor_metrics(device_id: int, module_id: int, reading_id: int, sample: dict[str, Any]) -> None:
    metrics = flatten_metrics(sample.get("raw_payload") or {})
    rows = [
        (
            reading_id,
            device_id,
            module_id,
            sample["recorded_at"],
            metric_key,
            metric_value,
            unit,
            source_key,
        )
        for metric_key, metric_value, source_key, unit in metrics
    ]
    execute_many(
        """
        INSERT INTO pm_sensor_metrics
            (reading_id, device_id, module_id, recorded_at, metric_key, metric_value, unit, source_key)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )


def insert_diagnostic(device_id: int, module_id: int, diagnostic: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO pm_diagnostic_snapshots
            (device_id, module_id, recorded_at, source_recorded_at, sample_count, health_score, condition_state,
             temperature_c, temperature_avg_c, temperature_trend_c_per_min,
             pressure_kpa, pressure_avg_kpa, current_a, current_avg_a,
             vibration, vibration_avg, ai_model_version, ai_condition, ai_confidence, ai_notes)
        VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            device_id,
            module_id,
            diagnostic.get("source_recorded_at"),
            diagnostic.get("sample_count"),
            diagnostic.get("health_score"),
            diagnostic.get("condition_state"),
            diagnostic.get("temperature_c"),
            diagnostic.get("temperature_avg_c"),
            diagnostic.get("temperature_trend_c_per_min"),
            diagnostic.get("pressure_kpa"),
            diagnostic.get("pressure_avg_kpa"),
            diagnostic.get("current_a"),
            diagnostic.get("current_avg_a"),
            diagnostic.get("vibration"),
            diagnostic.get("vibration_avg"),
            diagnostic.get("ai_model_version"),
            diagnostic.get("ai_condition"),
            diagnostic.get("ai_confidence"),
            diagnostic.get("ai_notes"),
        ),
    )


ALERT_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


def alert_issue_key(alert: dict[str, Any]) -> str:
    explicit = str(alert.get("issue_key") or "").strip().lower()
    source = explicit or str(alert.get("title") or "diagnostic-alert").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", source).strip("_")
    return (normalized or "diagnostic_alert")[:160]


def _bangkok_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


_alerts_cleared_at: datetime | None = None


def _get_alerts_cleared_at() -> datetime | None:
    global _alerts_cleared_at
    if _alerts_cleared_at is not None:
        return _alerts_cleared_at
    try:
        row = fetch_one("SELECT value_text FROM pm_system_settings WHERE key_name = 'alerts_cleared_at'")
        if row and row.get("value_text"):
            _alerts_cleared_at = datetime.fromisoformat(row["value_text"])
            return _alerts_cleared_at
    except Exception:
        pass
    return None


def _set_alerts_cleared_at(dt: datetime) -> None:
    global _alerts_cleared_at
    _alerts_cleared_at = dt
    try:
        execute(
            """
            CREATE TABLE IF NOT EXISTS pm_system_settings (
                key_name VARCHAR(64) PRIMARY KEY,
                value_text TEXT,
                updated_at DATETIME
            )
            """
        )
        execute(
            """
            INSERT INTO pm_system_settings (key_name, value_text, updated_at)
            VALUES ('alerts_cleared_at', %s, NOW())
            ON DUPLICATE KEY UPDATE value_text = VALUES(value_text), updated_at = NOW()
            """,
            (dt.isoformat(),),
        )
    except Exception as exc:
        log.warning("Could not persist alerts_cleared_at: %s", exc)


def alert_should_insert(
    device_id: int,
    module_id: int,
    issue_key: str,
    severity: str,
    *,
    sample_time: datetime | None = None,
    now: datetime | None = None,
) -> bool:
    current = now or datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
    cleared_at = _get_alerts_cleared_at()
    if cleared_at:
        check_time = sample_time or current
        if check_time <= cleared_at:
            return False
    current_rank = ALERT_SEVERITY_RANK.get(severity, 0)
    day_start, day_end = _bangkok_day_bounds(current)
    today = fetch_one(
        """
        SELECT severity
        FROM pm_alerts
        WHERE device_id = %s AND module_id = %s AND issue_key = %s
          AND recorded_at >= %s AND recorded_at < %s
        ORDER BY recorded_at DESC, id DESC
        LIMIT 1
        """,
        (device_id, module_id, issue_key, day_start, day_end),
    )
    if today and current_rank <= ALERT_SEVERITY_RANK.get(str(today.get("severity")), 0):
        return False

    acknowledged = fetch_one(
        """
        SELECT severity
        FROM pm_alerts
        WHERE device_id = %s AND module_id = %s AND issue_key = %s
          AND acknowledged = 1 AND suppressed_until > %s
        ORDER BY acknowledged_at DESC, id DESC
        LIMIT 1
        """,
        (device_id, module_id, issue_key, current),
    )
    if acknowledged and current_rank <= ALERT_SEVERITY_RANK.get(str(acknowledged.get("severity")), 0):
        return False
    return True


def insert_alerts(
    device_id: int,
    module_id: int,
    diagnostic_id: int,
    alerts: list[dict[str, str]],
    *,
    sample_time: datetime | None = None,
) -> None:
    for alert in alerts:
        severity = alert.get("severity", "info")
        issue_key = alert_issue_key(alert)
        if not alert_should_insert(device_id, module_id, issue_key, severity, sample_time=sample_time):
            continue
        execute(
            """
            INSERT INTO pm_alerts
                (device_id, module_id, diagnostic_id, issue_key, severity, title, message, recorded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                device_id,
                module_id,
                diagnostic_id,
                issue_key,
                severity,
                alert.get("title", "Diagnostic alert"),
                alert.get("message", ""),
            ),
        )


def update_device_status(device_id: int) -> str:
    modules = fetch_all("SELECT status FROM pm_modules WHERE device_id = %s", (device_id,))
    if not modules:
        status = "OFFLINE"
    else:
        status = max(("NORMAL" if m["status"] == "MONITORING" else m["status"] for m in modules), key=lambda s: CONDITION_RANK.get(s, 0))
    execute("UPDATE pm_devices SET status = %s WHERE id = %s", (status, device_id))
    return status


def ingest_telemetry(payload: dict[str, Any], source: str = "http", topic: str | None = None) -> dict[str, Any]:
    sample = normalize_telemetry(payload, topic=topic, source=source)
    device_id = ensure_device(sample)
    module_id = ensure_module(device_id, sample)
    module_before = fetch_one("SELECT status, thresholds_json FROM pm_modules WHERE id = %s", (module_id,)) or {}
    reading_id = insert_reading(device_id, module_id, sample)
    insert_sensor_metrics(device_id, module_id, reading_id, sample)
    history = module_history(module_id, limit=256)
    diagnostic = compute_diagnostics(history, thresholds=json_loads(module_before.get("thresholds_json"), {}))
    diagnostic["source_recorded_at"] = sample.recorded_at
    diagnostic_id = insert_diagnostic(device_id, module_id, diagnostic)
    insert_alerts(device_id, module_id, diagnostic_id, diagnostic.get("alerts", []))

    diagnostic_status = diagnostic.get("condition_state", "NORMAL")
    current_status = module_before.get("status")
    if current_status == "UNDER_MAINTENANCE":
        module_status = "UNDER_MAINTENANCE"
    else:
        module_status = diagnostic_status
    execute("UPDATE pm_modules SET status = %s WHERE id = %s", (module_status, module_id))
    device_status = update_device_status(device_id)

    device = fetch_one("SELECT * FROM pm_devices WHERE id = %s", (device_id,))
    module = fetch_one("SELECT * FROM pm_modules WHERE id = %s", (module_id,))
    return {
        "type": "telemetry",
        "device_id": device_id,
        "module_id": module_id,
        "reading_id": reading_id,
        "diagnostic_id": diagnostic_id,
        "device_status": device_status,
        "module_status": module_status,
        "device": device,
        "module": module,
        "latest": sample,
        "diagnostic": diagnostic,
    }


def ensure_external_device(sample: ExternalTelemetrySample) -> int:
    """Register a source device once, without changing source telemetry."""
    existing = fetch_one(
        """
        SELECT id
        FROM pm_devices
        WHERE machine_code = %s OR device_uid = %s OR device_uid = %s
        ORDER BY (machine_code = %s) DESC, id ASC
        LIMIT 1
        """,
        (sample.machine_code, sample.device_uid, sample.machine_code, sample.machine_code),
    )
    if existing:
        device_id = int(existing["id"])
        execute(
            """
            UPDATE pm_devices
            SET last_seen = %s,
                machine_code = %s,
                display_name = %s,
                status = IF(status = 'OFFLINE', 'NORMAL', status)
            WHERE id = %s
            """,
            (sample.recorded_at, sample.machine_code, sample.display_name, device_id),
        )
        return device_id
    return execute(
        """
        INSERT INTO pm_devices
            (device_uid, machine_code, display_name, status, first_seen, last_seen)
        VALUES (%s, %s, %s, 'NORMAL', %s, %s)
        """,
        (
            sample.machine_code,
            sample.machine_code,
            sample.display_name,
            sample.recorded_at,
            sample.recorded_at,
        ),
    )


def register_external_sample(sample: ExternalTelemetrySample) -> dict[str, Any]:
    """Mirror live source identity/status into dashboard metadata only.

    ``pm_sensor_readings`` is deliberately not used here: history remains in
    the external MySQL source and is queried on demand by the API.
    """
    device_id = ensure_external_device(sample)
    module_id = ensure_module(
        device_id,
        {
            "module_code": sample.module_code,
            "module_name": sample.module_name,
        },
    )
    source_device_key = sample.device_uid.split(":", 1)[1] if ":" in sample.device_uid else sample.device_uid
    execute(
        "UPDATE pm_modules SET telemetry_source = %s, source_device_key = %s WHERE id = %s",
        (sample.source, source_device_key, module_id),
    )
    telemetry_sources.remember(device_id, module_id, sample)

    module_before = fetch_one("SELECT status, thresholds_json FROM pm_modules WHERE id = %s", (module_id,)) or {}
    health = telemetry_sources.health_for(sample.machine_code, sample.module_code) if sample.source == "compressor" else None
    if sample.source == "compressor" and health:
        diagnostic_status = compressor_condition_state(health.condition, health.health_score)
        diagnostic = {
            "sample_count": 1,
            "health_score": int(round(health.health_score)),
            "condition_state": diagnostic_status,
            "temperature_c": sample.temperature_c,
            "pressure_kpa": sample.pressure_kpa,
            "current_a": sample.current_a,
            "vibration": sample.vibration,
            "ai_model_version": health.model_version,
            "ai_condition": health.condition or diagnostic_status,
            "ai_notes": "Read-only result from Compressor ML MySQL output table.",
            # OPERATION owns Compressor alerts. The dashboard only displays
            # its ML result; Vacuum alerts remain dashboard-owned.
            "alerts": [],
        }
    elif sample.source == "compressor":
        diagnostic_status = module_before.get("status") or "NORMAL"
        diagnostic = {}
    else:
        diagnostic = compute_diagnostics(
            [{
                "recorded_at": sample.recorded_at,
                "temperature_c": sample.temperature_c,
                "pressure_kpa": sample.pressure_kpa,
                "current_a": sample.current_a,
                "vibration": sample.vibration,
            }],
            thresholds=json_loads(module_before.get("thresholds_json"), {}),
            source=sample.source,
        )
        diagnostic_status = diagnostic.get("condition_state", "NORMAL")
    cleared_at = _get_alerts_cleared_at()
    is_suppressed = cleared_at is not None and sample.recorded_at <= cleared_at
    if diagnostic:
        diagnostic["source_recorded_at"] = sample.recorded_at
    diagnostic_id = insert_diagnostic(device_id, module_id, diagnostic) if diagnostic else None
    if diagnostic_id and not is_suppressed:
        insert_alerts(device_id, module_id, diagnostic_id, diagnostic.get("alerts", []), sample_time=sample.recorded_at)
    from .operation_pull import operation_pull
    if operation_pull.status['enabled']:
        from .health_history import record_state
        state_payload = {}
        if sample.source == 'compressor':
            latest = fetch_one('SELECT * FROM pm_operation_latest WHERE module_id=%s', (module_id,))
            fresh = latest and 0 <= (sample.recorded_at-latest['occurred_at']).total_seconds() <= 600
            diagnostic_status = latest['status'] if fresh else 'NOT_EVALUATED'
            state_payload = json_loads(latest['payload_json'], {}) if latest else {}
        with connection() as state_conn:
            state_conn.begin()
            try:
                with state_conn.cursor() as state_cur:
                    record_state(state_cur,module_id=module_id,source=sample.source,at=sample.recorded_at,
                        status="UNDER_MAINTENANCE" if module_before.get("status")=="UNDER_MAINTENANCE" else diagnostic_status,evidence_id=sample.source_id,payload=state_payload,signal_at=sample.recorded_at)
                state_conn.commit()
            except Exception:
                state_conn.rollback();raise
    current_status = module_before.get("status")
    if is_suppressed:
        module_status = "NORMAL"
    elif current_status == "UNDER_MAINTENANCE":
        module_status = "UNDER_MAINTENANCE"
    else:
        module_status = diagnostic_status
    if module_status != "NOT_EVALUATED":
        execute("UPDATE pm_modules SET status = %s WHERE id = %s AND status <> 'UNDER_MAINTENANCE'", (module_status, module_id))
    device_status = update_device_status(device_id)
    cache.invalidate("devices", "summary")
    return {
        "changed": True,
        "type": "mysql_telemetry",
        "source": sample.source,
        "device_id": device_id,
        "module_id": module_id,
        "device_status": device_status,
        "module_status": module_status,
        "latest": sample.history_row(device_id, module_id),
        "diagnostic": diagnostic,
    }


def compressor_condition_state(condition: str | None, score: float | None) -> str:
    value = re.sub(r"[^A-Z0-9]+", "_", str(condition or "").upper()).strip("_")
    if value in {"CRITICAL", "FAULT", "FAIL", "P1_REVIEW", "MAINTENANCE_REQUIRED"}:
        return "MAINTENANCE_REQUIRED"
    if value in {"WARNING", "P2_REVIEW"}:
        return "WARNING"
    if value in {"WATCH", "SHADOW", "MONITORING"}:
        return "WATCH"
    if value in {"NORMAL", "GOOD", "HEALTHY"}:
        return "NORMAL"
    numeric = float(score) if score is not None else None
    if numeric is not None and numeric < 55:
        return "MAINTENANCE_REQUIRED"
    if numeric is not None and numeric < 75:
        return "WARNING"
    if numeric is not None and numeric < 88:
        return "WATCH"
    return "NORMAL"


def compressor_health_alerts(condition: str, score: float) -> list[dict[str, str]]:
    if condition == "MAINTENANCE_REQUIRED":
        severity = "critical"
    elif condition in {"WARNING", "WATCH"}:
        severity = "warning"
    else:
        return []
    return [{
        "severity": severity,
        "issue_key": "compressor_ml_condition",
        "title": "Compressor ML condition requires review",
        "message": f"ML Health Score is {score:.0f}; condition is {condition}.",
    }]


def latest_module_rows() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            d.id AS device_id,
            d.device_uid,
            d.machine_code,
            d.display_name,
            d.location,
            d.status AS device_status,
            d.last_seen,
            TIMESTAMPDIFF(SECOND, d.last_seen, NOW()) AS seconds_since_seen,
            m.id AS module_id,
            m.module_code,
            m.module_name,
            m.module_type,
            m.telemetry_source,
            m.source_device_key,
            m.status AS module_status,
            m.thresholds_json,
            ds.health_score,
            (SELECT prior.health_score FROM pm_diagnostic_snapshots prior
             WHERE prior.module_id = m.id AND prior.health_score IS NOT NULL
               AND prior.recorded_at BETWEEN DATE_SUB(NOW(), INTERVAL 48 HOUR)
                                         AND DATE_SUB(NOW(), INTERVAL 24 HOUR)
             ORDER BY prior.recorded_at DESC, prior.id DESC LIMIT 1) AS health_score_24h_baseline,
            ds.condition_state,
            ds.temperature_c,
            ds.pressure_kpa,
            ds.current_a,
            ds.vibration,
            ds.ai_model_version,
            ds.ai_condition,
            ds.ai_confidence,
            ds.ai_notes,
            ds.recorded_at AS diagnostic_at
        FROM pm_devices d
        LEFT JOIN pm_modules m ON m.device_id = d.id
        LEFT JOIN (
            SELECT ds1.*
            FROM pm_diagnostic_snapshots ds1
            INNER JOIN (
                SELECT module_id, MAX(id) AS max_id
                FROM pm_diagnostic_snapshots
                GROUP BY module_id
            ) ds2 ON ds2.module_id = ds1.module_id AND ds2.max_id = ds1.id
        ) ds ON ds.module_id = m.id
        ORDER BY d.machine_code, m.module_name
        """
    )


@coalesced_read("devices")
def list_devices() -> list[dict[str, Any]]:
    cached = cache.get("devices")
    if cached is not None:
        return cached
    rows = latest_module_rows()
    compressor_ids = {row["device_id"] for row in rows if row.get("telemetry_source") == "compressor"}
    devices: dict[int, dict[str, Any]] = {}
    for row in rows:
        device_id = row["device_id"]
        signal_state, signal_age = connection_state(row["last_seen"], row["device_uid"], telemetry_source="compressor" if device_id in compressor_ids else None)
        devices.setdefault(
            device_id,
            {
                "id": device_id,
                "device_uid": row["device_uid"],
                "machine_code": row["machine_code"],
                "display_name": row["display_name"],
                "location": row["location"],
                "status": operational_status(row["device_status"], signal_state),
                "last_seen": row["last_seen"],
                "seconds_since_seen": signal_age,
                "connection_state": signal_state,
                "modules": [],
            },
        )
        if row.get("module_id"):
            module = {
                "id": row["module_id"],
                "module_code": row["module_code"],
                "module_name": row["module_name"],
                "module_type": row["module_type"],
                "telemetry_source": row["telemetry_source"],
                "source_device_key": row["source_device_key"],
                "status": operational_status(row["module_status"], signal_state),
                "thresholds": json_loads(row.get("thresholds_json"), {}),
                "health_score": row["health_score"],
                "health_score_24h_baseline": row["health_score_24h_baseline"],
                "condition_state": row["condition_state"],
                "temperature_c": row["temperature_c"],
                "pressure_kpa": row["pressure_kpa"],
                "current_a": row["current_a"],
                "vibration": row["vibration"],
                "ai_model_version": row["ai_model_version"],
                "ai_condition": row["ai_condition"],
                "ai_confidence": row["ai_confidence"],
                "ai_notes": row["ai_notes"],
                "diagnostic_at": row["diagnostic_at"],
            }
            live = telemetry_sources.latest_for(device_id, int(row["module_id"]))
            if live:
                module.update(
                    {
                        "temperature_c": live.temperature_c,
                        "pressure_kpa": live.pressure_kpa,
                        "current_a": live.current_a,
                        "vibration": live.vibration,
                        "diagnostic_at": live.recorded_at,
                        "telemetry_source": live.source,
                        "source_status": live.operating_status,
                        "source_sv": live.set_valve_status,
                        "metrics": {key: value for key, (value, _unit) in live.metrics.items()},
                        "metric_units": {key: unit for key, (_value, unit) in live.metrics.items()},
                    }
                )
            if row.get("telemetry_source") == "compressor":
                health = telemetry_sources.health_for(row["machine_code"], row["module_code"])
                if health:
                    module.update({
                        "health_score": health.health_score,
                        "condition_state": compressor_condition_state(health.condition, health.health_score),
                        "ai_model_version": health.model_version,
                        "ai_condition": health.condition or compressor_condition_state(None, health.health_score),
                        "ai_notes": "Read-only result from Compressor ML MySQL output table.",
                        "health_score_at": health.recorded_at,
                    })
                else:
                    module.update({
                        "health_score": None,
                        "condition_state": None,
                        "ai_model_version": None,
                        "ai_condition": "AWAITING_ML_SCORE",
                        "ai_notes": "No Compressor ML score is available from the configured MySQL result table.",
                        "health_score_at": None,
                    })
            devices[device_id]["modules"].append(module)
    from .operation_pull import operation_pull
    if operation_pull.status['enabled']:
        op_rows = {r['module_id']:r for r in fetch_all('SELECT * FROM pm_operation_latest')}
        now = datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
        for device in devices.values():
            for module in device['modules']:
                if module.get('telemetry_source') != 'compressor': continue
                row = op_rows.get(module['id'])
                fresh = row and 0 <= (now-row['occurred_at']).total_seconds() <= 600
                payload = json_loads(row['payload_json'], {}) if row else {}
                state = row['status'] if fresh else 'NOT_EVALUATED'
                if device['connection_state'] != 'OFFLINE' and module['status'] != 'UNDER_MAINTENANCE': module['status'] = state
                module.update(condition_state=state,health_score=None,ai_condition=payload.get('category','AWAITING_OPERATION_RESULT') if fresh else 'No recent Operation result',operation_result_fresh=bool(fresh),operation_pull_enabled=True,
                    ai_model_version=payload.get('profile_id'),health_score_at=row['occurred_at'] if row else None,
                    operation_mode=payload.get('mode'),operation_evidence=payload.get('main_evidence'))
            visible=[m['status'] for m in device['modules']]
            if device['connection_state'] != 'OFFLINE' and visible:
                device['status']=max(visible,key=lambda v: {'MAINTENANCE_REQUIRED':5,'WARNING':4,'WATCH':4,'UNDER_MAINTENANCE':3,'NOT_EVALUATED':2,'NORMAL':1,'OFFLINE':0}.get(v,0))
    result = list(devices.values())
    cache.set("devices", result, ttl=3)
    return result


def get_device_detail(device_id: int) -> dict[str, Any]:
    device = fetch_one("SELECT * FROM pm_devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    modules = [d for d in list_devices() if d["id"] == device_id]
    detail = modules[0] if modules else {**device, "modules": []}
    detail["work_orders"] = list_work_orders(device_id=device_id, limit=20)
    detail["maintenance_logs"] = list_maintenance_logs(device_id=device_id, limit=20)
    return detail


def _parse_since(since: str | None) -> datetime | None:
    if not since:
        return None
    try:
        parsed = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(ZoneInfo(settings.app_timezone))
        return parsed.replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def get_history(device_id: int, module_id: int | None = None, limit: int = 240, since: str | None = None) -> list[dict[str, Any]]:
    device = fetch_one("SELECT id, device_uid, machine_code FROM pm_devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    since_dt = _parse_since(since)
    safe_limit = min(limit, 2000)
    external_modules = fetch_all(
        "SELECT id, module_code, module_name, telemetry_source, source_device_key FROM pm_modules WHERE device_id = %s" + (" AND id = %s" if module_id else ""),
        (device_id, module_id) if module_id else (device_id,),
    )
    external_available = False
    external_rows: list[dict[str, Any]] = []
    for module in external_modules:
        samples = telemetry_sources.history_for(
            device["device_uid"],
            module["module_code"],
            safe_limit,
            source=module.get("telemetry_source"),
            source_device_key=module.get("source_device_key"),
        )
        if samples is None:
            continue
        external_available = True
        use_samples = [s for s in samples if s.recorded_at >= since_dt] if since_dt else samples
        for sample in use_samples:
            external_rows.append({
                **sample.history_row(device_id, int(module["id"])),
                "machine_code": device["machine_code"],
                "module_name": module["module_name"],
            })
    if external_available:
        return sorted(external_rows, key=lambda row: (row["recorded_at"], str(row["id"])))[-safe_limit:]

    params: list[Any] = [device_id]
    where = "sr.device_id = %s"
    if module_id:
        where += " AND sr.module_id = %s"
        params.append(module_id)
    if since_dt:
        where += " AND sr.recorded_at >= %s"
        params.append(since_dt)
    params.append(safe_limit)
    rows = fetch_all(
        f"""
        SELECT
            sr.id,
            sr.device_id,
            sr.module_id,
            d.machine_code,
            m.module_name,
            sr.recorded_at,
            sr.temperature_c,
            sr.pressure_kpa,
            sr.current_a,
            sr.accel_x,
            sr.accel_y,
            sr.accel_z,
            sr.vibration,
            sr.gyro_x,
            sr.gyro_y,
            sr.gyro_z
        FROM pm_sensor_readings sr
        INNER JOIN pm_devices d ON d.id = sr.device_id
        INNER JOIN pm_modules m ON m.id = sr.module_id
        WHERE {where}
        ORDER BY sr.recorded_at DESC, sr.id DESC
        LIMIT %s
        """,
        params,
    )
    rows.reverse()
    return rows


def get_metric_history(device_id: int, module_id: int | None = None, limit: int = 600, since: str | None = None) -> list[dict[str, Any]]:
    device = fetch_one("SELECT id, device_uid, machine_code FROM pm_devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    since_dt = _parse_since(since)
    safe_limit = min(limit, 3000)
    external_modules = fetch_all(
        "SELECT id, module_code, module_name, telemetry_source, source_device_key FROM pm_modules WHERE device_id = %s" + (" AND id = %s" if module_id else ""),
        (device_id, module_id) if module_id else (device_id,),
    )
    external_available = False
    external_metrics: list[dict[str, Any]] = []
    for module in external_modules:
        samples = telemetry_sources.history_for(
            device["device_uid"],
            module["module_code"],
            safe_limit,
            source=module.get("telemetry_source"),
            source_device_key=module.get("source_device_key"),
        )
        if samples is None:
            continue
        external_available = True
        use_samples = [s for s in samples if s.recorded_at >= since_dt] if since_dt else samples
        for sample in use_samples:
            for metric_key, (metric_value, unit) in sample.metrics.items():
                if metric_value is None or not math.isfinite(metric_value):
                    continue
                external_metrics.append(
                    {
                        "id": f"{sample.source_id}:{metric_key}",
                        "reading_id": sample.source_id,
                        "device_id": device_id,
                        "module_id": module["id"],
                        "machine_code": device["machine_code"],
                        "module_name": module["module_name"],
                        "recorded_at": sample.recorded_at,
                        "metric_key": metric_key,
                        "metric_value": metric_value,
                        "unit": unit,
                        "source_key": metric_key,
                    }
                )
    if external_available:
        return sorted(external_metrics, key=lambda row: (row["recorded_at"], str(row["id"])), reverse=True)[:safe_limit]

    params: list[Any] = [device_id]
    where = "sm.device_id = %s"
    if module_id:
        where += " AND sm.module_id = %s"
        params.append(module_id)
    if since_dt:
        where += " AND sm.recorded_at >= %s"
        params.append(since_dt)
    params.append(safe_limit)
    return fetch_all(
        f"""
        SELECT
            sm.id,
            sm.reading_id,
            sm.device_id,
            sm.module_id,
            d.machine_code,
            m.module_name,
            sm.recorded_at,
            sm.metric_key,
            sm.metric_value,
            sm.unit,
            sm.source_key
        FROM pm_sensor_metrics sm
        INNER JOIN pm_devices d ON d.id = sm.device_id
        INNER JOIN pm_modules m ON m.id = sm.module_id
        WHERE {where}
        ORDER BY sm.recorded_at DESC, sm.id DESC
        LIMIT %s
        """,
        params,
    )


@coalesced_read("summary")
def get_summary() -> dict[str, Any]:
    cached = cache.get("summary")
    if cached is not None:
        return cached

    status_rows = fetch_all("""SELECT d.device_uid, d.status, d.last_seen,
        EXISTS(SELECT 1 FROM pm_modules m WHERE m.device_id=d.id AND m.telemetry_source='compressor') AS has_compressor
        FROM pm_devices d""")
    counts: dict[str, int] = {s: 0 for s in ["NORMAL", "WATCH", "WARNING", "MAINTENANCE_REQUIRED", "UNDER_MAINTENANCE", "OFFLINE", "NOT_EVALUATED"]}
    connection_counts: dict[str, int] = {"ONLINE": 0, "STALE": 0, "NO_SIGNAL": 0, "OFFLINE": 0}
    from .operation_pull import operation_pull
    displayed = {d['device_uid']:d['status'] for d in list_devices()} if operation_pull.status['enabled'] else {}
    for row in status_rows:
        signal_state, _ = connection_state(row["last_seen"], row["device_uid"], telemetry_source="compressor" if row.get("has_compressor") else None)
        status = displayed.get(row["device_uid"], operational_status(row["status"], signal_state))
        counts[status] = counts.get(status, 0) + 1
        connection_counts[signal_state] = connection_counts.get(signal_state, 0) + 1
    total = sum(counts.values())

    cost = fetch_one("SELECT COALESCE(SUM(cost_baht), 0) AS total_cost FROM pm_maintenance_logs") or {"total_cost": 0}
    open_orders = fetch_one("SELECT COUNT(*) AS count FROM pm_work_orders WHERE status IN ('OPEN', 'IN_PROGRESS')") or {"count": 0}
    result = {
        "total_devices": total,
        "counts": counts,
        "connection_counts": connection_counts,
        "total_repair_cost_baht": float(cost["total_cost"] or 0),
        "open_work_orders": int(open_orders["count"] or 0),
    }
    cache.set("summary", result, ttl=4)
    return result


_health_trend_locks = {"7d": threading.Lock()}


def get_fleet_health_trend(time_range: str = "7d") -> dict[str, Any]:
    """Read 168 durable completed-hour module end-state totals.

    Uncaptured hours stay null. Captured end-state counts use source time and
    signal freshness, never the receiver's arrival time.
    """
    if time_range not in _health_trend_locks:
        raise HTTPException(status_code=422, detail="range must be 7d")
    key = f"fleet_health_trend:{time_range}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    with _health_trend_locks[time_range]:
        cached = cache.get(key)
        if cached is not None:
            return cached
        from .health_history import hourly_trend
        result = hourly_trend(datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None))
        cache.set(key, result, ttl=60)
        return result


def create_device(data: dict[str, Any]) -> dict[str, Any]:
    device_uid = str(data.get("device_uid") or "").strip()
    machine_code = str(data.get("machine_code") or data.get("display_name") or "").strip()
    display_name = str(data.get("display_name") or machine_code).strip()
    if not device_uid or not machine_code:
        raise HTTPException(status_code=400, detail="device_uid and machine_code are required")
    device_id = execute(
        """
        INSERT INTO pm_devices (device_uid, machine_code, display_name, location, status, first_seen)
        VALUES (%s, %s, %s, %s, 'OFFLINE', NOW())
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            machine_code = VALUES(machine_code),
            display_name = VALUES(display_name),
            location = VALUES(location)
        """,
        (device_uid, machine_code, display_name, data.get("location")),
    )
    cache.invalidate("devices", "summary")
    return get_device_detail(device_id)


def update_device(device_id: int, data: dict[str, Any]) -> dict[str, Any]:
    allowed = ["device_uid", "machine_code", "display_name", "location", "firmware_version", "status"]
    fields = [(key, data[key]) for key in allowed if key in data]
    if not fields:
        return get_device_detail(device_id)
    assignments = ", ".join(f"{key} = %s" for key, _ in fields)
    params = [value for _, value in fields] + [device_id]
    execute(f"UPDATE pm_devices SET {assignments} WHERE id = %s", params)
    cache.invalidate("devices", "summary")
    return get_device_detail(device_id)


def delete_device(device_id: int) -> dict[str, Any]:
    execute("DELETE FROM pm_devices WHERE id = %s", (device_id,))
    cache.invalidate("devices", "summary")
    return {"ok": True}


def create_module(device_id: int, data: dict[str, Any]) -> dict[str, Any]:
    module_name = str(data.get("module_name") or "").strip()
    module_code = str(data.get("module_code") or module_name).strip().lower().replace(" ", "-")
    if not module_name:
        raise HTTPException(status_code=400, detail="module_name is required")
    module_id = execute(
        """
        INSERT INTO pm_modules (device_id, module_code, module_name, module_type, status, thresholds_json)
        VALUES (%s, %s, %s, %s, 'OFFLINE', %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            module_name = VALUES(module_name),
            module_type = VALUES(module_type),
            thresholds_json = VALUES(thresholds_json)
        """,
        (
            device_id,
            module_code,
            module_name,
            data.get("module_type") or module_name,
            json_dumps(data.get("thresholds") or {}),
        ),
    )
    cache.invalidate("devices", "summary")
    return public_module(fetch_one("SELECT * FROM pm_modules WHERE id = %s", (module_id,)))


def update_module(module_id: int, data: dict[str, Any]) -> dict[str, Any]:
    allowed = ["module_code", "module_name", "module_type", "status"]
    if "status" in data and data["status"] not in VALID_MODULE_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported module status")
    fields = [(key, data[key]) for key in allowed if key in data]
    if "thresholds" in data:
        module = fetch_one("SELECT module_code, telemetry_source FROM pm_modules WHERE id = %s", (module_id,))
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        if module.get("telemetry_source") == "compressor" or str(module.get("module_code") or "").startswith("compressor-"):
            raise HTTPException(status_code=400, detail="Compressor thresholds are managed by ML")
        thresholds = data["thresholds"]
        if not isinstance(thresholds, dict) or not isinstance(thresholds.get("enabled"), bool):
            raise HTTPException(status_code=400, detail="Advanced thresholds require an enabled flag")
        for metric in ("temperature_c", "current_a", "vibration"):
            pair = thresholds.get(metric)
            if not isinstance(pair, dict):
                raise HTTPException(status_code=400, detail=f"{metric} thresholds are required")
            try:
                warning = float(pair["warning"])
                critical = float(pair["critical"])
            except (KeyError, TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"Invalid {metric} thresholds")
            if not math.isfinite(warning) or not math.isfinite(critical) or warning >= critical:
                raise HTTPException(status_code=400, detail=f"{metric} warning must be below critical")
        fields.append(("thresholds_json", json_dumps(thresholds)))
    if fields:
        assignments = ", ".join(f"{key} = %s" for key, _ in fields)
        params = [value for _, value in fields] + [module_id]
        execute(f"UPDATE pm_modules SET {assignments} WHERE id = %s", params)
    row = fetch_one("SELECT * FROM pm_modules WHERE id = %s", (module_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Module not found")
    update_device_status(row["device_id"])
    cache.invalidate("devices", "summary")
    return public_module(row)


def delete_module(module_id: int) -> dict[str, Any]:
    row = fetch_one("SELECT device_id FROM pm_modules WHERE id = %s", (module_id,))
    execute("DELETE FROM pm_modules WHERE id = %s", (module_id,))
    cache.invalidate("devices", "summary")
    if row:
        update_device_status(row["device_id"])
    return {"ok": True}


def list_work_orders(device_id: int | None = None, assigned_to: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    where = []
    params: list[Any] = []
    if device_id:
        where.append("wo.device_id = %s")
        params.append(device_id)
    if assigned_to:
        where.append("wo.assigned_to = %s")
        params.append(assigned_to)
    clause = "WHERE " + " AND ".join(where) if where else ""
    params.append(min(limit, 500))
    return fetch_all(
        f"""
        SELECT
            wo.*,
            d.machine_code,
            d.display_name,
            m.module_name,
            u.username AS assigned_username,
            u.full_name AS assigned_full_name
        FROM pm_work_orders wo
        INNER JOIN pm_devices d ON d.id = wo.device_id
        LEFT JOIN pm_modules m ON m.id = wo.module_id
        LEFT JOIN pm_users u ON u.id = wo.assigned_to
        {clause}
        ORDER BY FIELD(wo.status, 'OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED'),
                 wo.created_at ASC, wo.id ASC
        LIMIT %s
        """,
        params,
    )


def delete_work_order(work_order_id: int, actor: dict[str, Any]) -> dict[str, Any]:
    """Delete an active order, retaining a database-only audit snapshot."""
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pm_work_orders WHERE id = %s FOR UPDATE", (work_order_id,))
                order = cur.fetchone()
                if not order:
                    raise HTTPException(status_code=404, detail="Work order not found")
                if order["status"] not in {"OPEN", "IN_PROGRESS"}:
                    raise HTTPException(status_code=409, detail="Only active work orders can be deleted")
                cur.execute("SELECT COUNT(*) AS n FROM pm_maintenance_logs WHERE work_order_id = %s", (work_order_id,))
                if int(cur.fetchone()["n"]):
                    raise HTTPException(status_code=409, detail="Work order has service logs")
                cur.execute(
                    "INSERT INTO pm_deletion_audit (entity_type, entity_id, actor_user_id, actor_username, snapshot_json) "
                    "VALUES ('WORK_ORDER', %s, %s, %s, %s)",
                    (work_order_id, int(actor["sub"]), str(actor["username"]), json_dumps(order)),
                )
                cur.execute("DELETE FROM pm_work_orders WHERE id = %s", (work_order_id,))
                if order["status"] == "IN_PROGRESS":
                    scope = "device_id = %s" + (" AND id = %s" if order.get("module_id") else "")
                    args = (order["device_id"], order["module_id"]) if order.get("module_id") else (order["device_id"],)
                    cur.execute(f"SELECT id FROM pm_modules WHERE {scope} FOR UPDATE", args)
                    for module in cur.fetchall():
                        cur.execute(
                            "SELECT COUNT(*) AS n FROM pm_work_orders WHERE device_id = %s "
                            "AND status = 'IN_PROGRESS' AND (module_id = %s OR module_id IS NULL)",
                            (order["device_id"], module["id"]),
                        )
                        if not int(cur.fetchone()["n"]):
                            cur.execute("SELECT condition_state FROM pm_diagnostic_snapshots "
                                        "WHERE module_id = %s ORDER BY recorded_at DESC, id DESC LIMIT 1", (module["id"],))
                            latest = cur.fetchone()
                            restored = latest["condition_state"] if latest else "NORMAL"
                            cur.execute("UPDATE pm_modules SET status = %s "
                                        "WHERE id = %s AND status = 'UNDER_MAINTENANCE'", (restored, module["id"]))
                cur.execute("SELECT status FROM pm_modules WHERE device_id = %s", (order["device_id"],))
                module_states = [row["status"] for row in cur.fetchall()]
                device_status = max(module_states, key=lambda state: CONDITION_RANK.get(state, 0), default="OFFLINE")
                cur.execute("UPDATE pm_devices SET status = %s WHERE id = %s", (device_status, order["device_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    cache.invalidate("devices", "summary")
    return {"ok": True, "deleted_id": work_order_id}


def create_work_order(data: dict[str, Any], created_by: int | None) -> dict[str, Any]:
    from .maintenance_evidence import event_context
    device_id = int(data.get("device_id") or 0)
    title = str(data.get("title") or "").strip()
    if not device_id or not title:
        raise HTTPException(status_code=400, detail="device_id and title are required")
    context = event_context(data, default_timezone=settings.app_timezone)
    if data.get("module_id") and not fetch_one(
        "SELECT id FROM pm_modules WHERE id = %s AND device_id = %s",
        (data["module_id"], device_id),
    ):
        raise HTTPException(400, "Module does not belong to the selected device")
    work_id = execute(
        """
        INSERT INTO pm_work_orders
            (device_id, module_id, title, description, priority, status, assigned_to, created_by, due_at,
             report_origin, event_started_at, event_ended_at, event_timezone, event_time_precision)
        VALUES (%s, %s, %s, %s, %s, 'OPEN', %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            device_id,
            data.get("module_id"),
            title,
            data.get("description"),
            data.get("priority") or "MEDIUM",
            data.get("assigned_to"),
            created_by,
            data.get("due_at"),
            "ADMIN_WORK_ORDER",
            context["event_started_at"], context["event_ended_at"],
            context["event_timezone"], context["event_time_precision"],
        ),
    )
    return fetch_one("SELECT * FROM pm_work_orders WHERE id = %s", (work_id,))


def update_work_order(work_order_id: int, data: dict[str, Any], token: dict[str, Any] | None = None) -> dict[str, Any]:
    if data.get("status") == "DONE":
        raise HTTPException(status_code=400, detail="Complete work by submitting a linked service log")
    existing = fetch_one("SELECT * FROM pm_work_orders WHERE id = %s", (work_order_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Work order not found")

    is_admin = bool(token and token.get("role") == "admin")
    if token and not is_admin:
        user_id = int(token["sub"])
        if int(existing.get("assigned_to") or 0) != user_id:
            raise HTTPException(status_code=403, detail="This work order is not assigned to you")
        if set(data) - {"status"}:
            raise HTTPException(status_code=403, detail="Technicians can update status only")
        if data.get("status") != "IN_PROGRESS":
            raise HTTPException(status_code=400, detail="Unsupported technician status")

    if is_admin and any(key.startswith("event_") for key in data):
        from .maintenance_evidence import event_context
        data = {**data, **event_context(data, default_timezone=settings.app_timezone, existing=existing)}
    allowed = ["title", "description", "priority", "status", "assigned_to", "due_at",
               "event_started_at", "event_ended_at", "event_timezone", "event_time_precision"] if is_admin else ["status"]
    fields = [(key, data[key]) for key in allowed if key in data]
    if fields:
        assignments = ", ".join(f"{key} = %s" for key, _ in fields)
        params = [value for _, value in fields] + [work_order_id]
        execute(f"UPDATE pm_work_orders SET {assignments} WHERE id = %s", params)
    row = fetch_one("SELECT * FROM pm_work_orders WHERE id = %s", (work_order_id,))
    apply_work_order_status(row)
    return row


def apply_work_order_status(row: dict[str, Any]) -> None:
    status = row.get("status")
    device_id = row.get("device_id")
    module_id = row.get("module_id")
    if not device_id:
        return

    if status == "IN_PROGRESS":
        if module_id:
            execute("UPDATE pm_modules SET status = 'UNDER_MAINTENANCE' WHERE id = %s", (module_id,))
        else:
            execute("UPDATE pm_modules SET status = 'UNDER_MAINTENANCE' WHERE device_id = %s", (device_id,))
        update_device_status(int(device_id))
        return

    if status == "DONE":
        if module_id:
            execute("UPDATE pm_modules SET status = 'NORMAL' WHERE id = %s", (module_id,))
        else:
            execute("UPDATE pm_modules SET status = 'NORMAL' WHERE device_id = %s", (device_id,))
        update_device_status(int(device_id))
        return

    if status == "CANCELLED":
        update_device_status(int(device_id))


def list_maintenance_logs(device_id: int | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if device_id:
        where = "WHERE ml.device_id = %s"
        params.append(device_id)
    params.extend((max(1, min(limit, 500)), max(0, offset)))
    rows = fetch_all(
        f"""
        SELECT
            ml.*,
            d.machine_code,
            d.display_name,
            m.module_name,
            wo.title AS work_order_title,
            wo.description AS reported_description,
            wo.source_alert_id, wo.report_origin,
            wo.event_started_at, wo.event_ended_at, wo.event_timezone, wo.event_time_precision
        FROM pm_maintenance_logs ml
        INNER JOIN pm_devices d ON d.id = ml.device_id
        LEFT JOIN pm_modules m ON m.id = ml.module_id
        LEFT JOIN pm_work_orders wo ON wo.id = ml.work_order_id
        {where}
        ORDER BY ml.recorded_at DESC, ml.id DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    return [_maintenance_log_view(row) for row in rows]


def _maintenance_log_view(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("parts_json")
    if isinstance(raw, (bytes, str)):
        try:
            parts = json.loads(raw)
        except (TypeError, ValueError):
            parts = []
    else:
        parts = raw if isinstance(raw, list) else []
    raw_context = row.get("incident_context_json")
    if isinstance(raw_context, (bytes, str)):
        try:
            raw_context = json.loads(raw_context)
        except (TypeError, ValueError):
            raw_context = None
    return {**row, "parts": parts, "incident_context": raw_context if isinstance(raw_context, dict) else None}


def _maintenance_costs(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str, float, float, str]:
    raw_parts = data.get("parts") or []
    if not isinstance(raw_parts, list) or len(raw_parts) > 30:
        raise HTTPException(status_code=400, detail="parts must be a list of at most 30 items")
    parts: list[dict[str, Any]] = []
    for item in raw_parts:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Invalid part item")
        name = str(item.get("name") or "").strip()
        try:
            quantity = float(item.get("quantity"))
            unit_cost = float(item.get("unit_cost_baht"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Part quantity and unit cost must be numbers")
        if not name or len(name) > 160 or not math.isfinite(quantity) or not math.isfinite(unit_cost) or quantity <= 0 or unit_cost < 0 or unit_cost > 9999999999.99:
            raise HTTPException(status_code=400, detail="Invalid part name, quantity or price")
        parts.append({"name": name, "quantity": quantity, "unit_cost_baht": round(unit_cost, 2),
                      "line_cost_baht": round(quantity * unit_cost, 2)})
    try:
        other = float(data.get("other_cost_baht") if "other_cost_baht" in data else data.get("cost_baht") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid other cost")
    if not math.isfinite(other) or other < 0 or other > 9999999999.99:
        raise HTTPException(status_code=400, detail="Invalid other cost")
    total = round(sum(part["line_cost_baht"] for part in parts) + other, 2)
    if total > 9999999999.99:
        raise HTTPException(status_code=400, detail="Total cost exceeds storage limit")
    summary = ", ".join(part["name"] for part in parts)[:220] if parts else str(data.get("parts_used") or "")[:220]
    return parts, json_dumps(parts), round(other, 2), total, summary


def create_maintenance_log(data: dict[str, Any], token: dict[str, Any]) -> dict[str, Any]:
    device_id = int(data.get("device_id") or 0)
    action_taken = str(data.get("action_taken") or "").strip()
    if not device_id or not action_taken:
        raise HTTPException(status_code=400, detail="device_id and action_taken are required")
    user = get_user(int(token["sub"]))
    technician_name = str(data.get("technician_name") or (user and user.get("full_name")) or token["username"])
    parts, parts_json, other_cost, total_cost, parts_summary = _maintenance_costs(data)
    work_order_id = int(data.get("work_order_id") or 0)
    if work_order_id:
        with connection() as conn:
            conn.begin()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM pm_work_orders WHERE id = %s FOR UPDATE", (work_order_id,))
                    work_order = cur.fetchone()
                    if not work_order:
                        raise HTTPException(status_code=404, detail="Work order not found")
                    if token.get("role") != "admin" and int(work_order.get("assigned_to") or 0) != int(token["sub"]):
                        raise HTTPException(status_code=403, detail="This work order is not assigned to you")
                    if work_order["status"] in {"DONE", "CANCELLED"}:
                        raise HTTPException(status_code=409, detail="Work order is already closed")
                    if int(work_order["device_id"]) != device_id:
                        raise HTTPException(status_code=400, detail="Service log device does not match the work order")
                    order_module_id = work_order.get("module_id")
                    requested_module_id = int(data.get("module_id") or 0) or None
                    if order_module_id and requested_module_id not in {None, int(order_module_id)}:
                        raise HTTPException(status_code=400, detail="Service log module does not match the work order")
                    module_id = int(order_module_id) if order_module_id else requested_module_id
                    from .maintenance_evidence import incident_snapshot
                    cur.execute(
                        """INSERT INTO pm_maintenance_logs
                           (device_id, module_id, work_order_id, technician_id, technician_name,
                            action_taken, parts_used, parts_json, other_cost_baht, cost_baht, incident_context_json, recorded_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                        (device_id, module_id, work_order_id, token["sub"], technician_name,
                         action_taken, parts_summary, parts_json, other_cost, total_cost,
                         json_dumps(incident_snapshot(work_order))),
                    )
                    log_id = cur.lastrowid
                    cur.execute("UPDATE pm_work_orders SET status = 'DONE', completed_at = NOW() WHERE id = %s", (work_order_id,))
                    # Completion ends the Repairing state. The next fresh ML/rule
                    # evaluation may raise the condition again if the fault remains.
                    if order_module_id:
                        cur.execute("UPDATE pm_modules SET status = 'NORMAL' WHERE id = %s", (int(order_module_id),))
                    else:
                        cur.execute("UPDATE pm_modules SET status = 'NORMAL' WHERE device_id = %s", (device_id,))
                    cur.execute("SELECT status FROM pm_modules WHERE device_id = %s", (device_id,))
                    module_states = [item["status"] for item in cur.fetchall()]
                    device_status = max(
                        ("NORMAL" if state == "MONITORING" else state for state in module_states),
                        key=lambda state: CONDITION_RANK.get(state, 0),
                        default="OFFLINE",
                    )
                    cur.execute("UPDATE pm_devices SET status = %s WHERE id = %s", (device_status, device_id))
                    cur.execute("SELECT * FROM pm_maintenance_logs WHERE id = %s", (log_id,))
                    row = cur.fetchone()
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        cache.invalidate("devices", "summary")
        return _maintenance_log_view(row)
    log_id = execute(
        """
        INSERT INTO pm_maintenance_logs
            (device_id, module_id, work_order_id, technician_id, technician_name,
             action_taken, parts_used, parts_json, other_cost_baht, cost_baht, recorded_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            device_id,
            data.get("module_id"),
            data.get("work_order_id"),
            token["sub"],
            technician_name,
            action_taken,
            parts_summary,
            parts_json,
            other_cost,
            total_cost,
        ),
    )
    return _maintenance_log_view(fetch_one("SELECT * FROM pm_maintenance_logs WHERE id = %s", (log_id,)))


def update_maintenance_log(log_id: int, data: dict[str, Any]) -> dict[str, Any]:
    action_taken = str(data.get("action_taken") or "").strip()
    technician_name = str(data.get("technician_name") or "").strip()
    if not action_taken or not technician_name or len(technician_name) > 160:
        raise HTTPException(status_code=400, detail="Technician and description are required")
    _parts, parts_json, other_cost, total_cost, parts_summary = _maintenance_costs(data)
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pm_maintenance_logs WHERE id = %s FOR UPDATE", (log_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Maintenance log not found")
                cur.execute(
                    "UPDATE pm_maintenance_logs SET technician_name=%s, action_taken=%s, "
                    "parts_used=%s, parts_json=%s, other_cost_baht=%s, cost_baht=%s WHERE id=%s",
                    (technician_name, action_taken, parts_summary, parts_json, other_cost, total_cost, log_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    cache.invalidate("summary")
    return _maintenance_log_view(fetch_one("SELECT * FROM pm_maintenance_logs WHERE id = %s", (log_id,)))


def delete_maintenance_log(log_id: int, actor: dict[str, Any]) -> dict[str, Any]:
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pm_maintenance_logs WHERE id = %s FOR UPDATE", (log_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Maintenance log not found")
                cur.execute(
                    "INSERT INTO pm_deletion_audit (entity_type, entity_id, actor_user_id, actor_username, snapshot_json) "
                    "VALUES ('MAINTENANCE_LOG', %s, %s, %s, %s)",
                    (log_id, int(actor["sub"]), str(actor["username"]), json_dumps(row)),
                )
                cur.execute("DELETE FROM pm_maintenance_logs WHERE id = %s", (log_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    cache.invalidate("summary", "devices")
    return {"ok": True, "deleted_id": log_id}


def clear_alerts() -> dict[str, Any]:
    now_dt = datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
    _set_alerts_cleared_at(now_dt)
    row = fetch_one("SELECT COUNT(*) AS count FROM pm_alerts") or {"count": 0}
    execute("DELETE FROM pm_alerts")
    try:
        execute("ALTER TABLE pm_alerts AUTO_INCREMENT = 1")
    except Exception:
        pass
    execute("UPDATE pm_modules SET status = 'NORMAL' WHERE status IN ('WARNING', 'WATCH', 'MAINTENANCE_REQUIRED')")
    devices = fetch_all("SELECT id FROM pm_devices")
    for d in devices:
        update_device_status(d["id"])
    cache.invalidate("devices", "summary")
    return {"ok": True, "deleted": int(row["count"] or 0)}


def reset_work_orders(actor: dict[str, Any]) -> dict[str, Any]:
    """Archive every work order to pm_deletion_audit, unlink maintenance logs, and restart numbering at #1."""
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pm_work_orders FOR UPDATE")
                orders = cur.fetchall()
                for order in orders:
                    cur.execute(
                        "INSERT INTO pm_deletion_audit (entity_type, entity_id, actor_user_id, actor_username, snapshot_json) "
                        "VALUES ('WORK_ORDER', %s, %s, %s, %s)",
                        (order["id"], int(actor["sub"]), str(actor["username"]), json_dumps(order)),
                    )
                cur.execute("UPDATE pm_maintenance_logs SET work_order_id = NULL WHERE work_order_id IS NOT NULL")
                cur.execute("DELETE FROM pm_work_orders")
                held: set[int] = set()
                for order in orders:
                    if order.get("status") != "IN_PROGRESS":
                        continue
                    if order.get("module_id"):
                        held.add(int(order["module_id"]))
                    else:
                        cur.execute("SELECT id FROM pm_modules WHERE device_id = %s", (order["device_id"],))
                        held.update(int(row["id"]) for row in cur.fetchall())
                for module_id in sorted(held):
                    cur.execute(
                        "SELECT condition_state FROM pm_diagnostic_snapshots "
                        "WHERE module_id = %s ORDER BY recorded_at DESC, id DESC LIMIT 1",
                        (module_id,),
                    )
                    latest = cur.fetchone()
                    restored = latest["condition_state"] if latest else "NORMAL"
                    cur.execute(
                        "UPDATE pm_modules SET status = %s WHERE id = %s AND status = 'UNDER_MAINTENANCE'",
                        (restored, module_id),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    try:
        execute("ALTER TABLE pm_work_orders AUTO_INCREMENT = 1")
    except Exception:
        pass
    devices = fetch_all("SELECT id FROM pm_devices")
    for d in devices:
        update_device_status(d["id"])
    cache.invalidate("devices", "summary")
    return {"ok": True, "deleted": len(orders)}


def get_numbering_status() -> dict[str, Any]:
    """Current row counts and next auto-increment sequence IDs for pm_alerts and pm_work_orders."""
    with connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SET SESSION information_schema_stats_expiry = 0")
            except Exception:
                pass
            cur.execute(
                "SELECT TABLE_NAME AS name, AUTO_INCREMENT AS next_id FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('pm_alerts', 'pm_work_orders')"
            )
            next_ids = {row["name"]: row["next_id"] for row in cur.fetchall()}
            cur.execute("SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id FROM pm_alerts")
            alerts = cur.fetchone() or {}
            cur.execute(
                "SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id, "
                "COALESCE(SUM(status IN ('OPEN', 'IN_PROGRESS')), 0) AS active FROM pm_work_orders"
            )
            orders = cur.fetchone() or {}
            cur.execute("SELECT COUNT(*) AS count FROM pm_maintenance_logs WHERE work_order_id IS NOT NULL")
            linked = cur.fetchone() or {}

    def resolve_next(table: str, row: dict[str, Any]) -> int:
        val = next_ids.get(table)
        return int(val) if val is not None else int(row.get("max_id") or 0) + 1

    return {
        "alerts": {
            "count": int(alerts.get("count") or 0),
            "max_id": int(alerts.get("max_id") or 0),
            "next_id": resolve_next("pm_alerts", alerts),
        },
        "work_orders": {
            "count": int(orders.get("count") or 0),
            "max_id": int(orders.get("max_id") or 0),
            "active": int(orders.get("active") or 0),
            "linked_logs": int(linked.get("count") or 0),
            "next_id": resolve_next("pm_work_orders", orders),
        },
    }


def reset_numbering(target: str, actor: dict[str, Any]) -> dict[str, Any]:
    target_clean = str(target or "").strip().lower()
    results = {}
    if target_clean in {"alerts", "all"}:
        results["alerts"] = clear_alerts()
    if target_clean in {"work_orders", "workorders", "all"}:
        results["work_orders"] = reset_work_orders(actor)
    if not results:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid target. Must be 'alerts', 'work_orders', or 'all'.")
    return {"ok": True, "target": target_clean, "results": results, "status": get_numbering_status()}


def alert_work_order_spec(alert: dict[str, Any]) -> tuple[str, str, str]:
    severity = str(alert.get("severity") or "info").lower()
    priority = {"critical": "CRITICAL", "warning": "HIGH"}.get(severity, "MEDIUM")
    title = f"Inspect: {str(alert.get('title') or 'Diagnostic alert').strip()}"[:220]
    description = f"Alert #{alert['id']} · {alert.get('issue_key') or 'diagnostic_alert'}\n{alert.get('message') or ''}".strip()
    return title, description, priority


def acknowledge_alert(alert_id: int, user_id: int, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
    suppressed_until = current + timedelta(days=7)
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pm_alerts WHERE id = %s FOR UPDATE", (alert_id,))
                alert = cur.fetchone()
                if not alert:
                    raise HTTPException(status_code=404, detail="Alert not found")
                work_order_id = None
                if str(alert.get("severity") or "").lower() == "critical":
                    cur.execute("SELECT id FROM pm_work_orders WHERE source_alert_id = %s", (alert_id,))
                    order = cur.fetchone()
                else:
                    order = None
                if str(alert.get("severity") or "").lower() == "critical" and not order:
                    cur.execute(
                        "SELECT id FROM pm_users WHERE username = %s AND role = 'user' "
                        "AND is_active = 1 LIMIT 1",
                        (settings.user_username,),
                    )
                    assignee = cur.fetchone()
                    title, description, priority = alert_work_order_spec(alert)
                    cur.execute(
                        """
                        INSERT INTO pm_work_orders
                            (device_id, module_id, source_alert_id, alert_recorded_at, title, description,
                             priority, status, assigned_to, created_by, report_origin)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'OPEN', %s, %s, 'ALERT_LINKED')
                        """,
                        (alert["device_id"], alert["module_id"], alert_id, alert.get("recorded_at"), title,
                         description, priority, (assignee or {}).get("id") or user_id, user_id),
                    )
                    work_order_id = cur.lastrowid
                elif order:
                    work_order_id = order["id"]
                if not alert.get("acknowledged"):
                    cur.execute(
                        """
                        UPDATE pm_alerts
                        SET acknowledged = 1, acknowledged_by = %s,
                            acknowledged_at = %s, suppressed_until = %s
                        WHERE id = %s
                        """,
                        (user_id, current, suppressed_until, alert_id),
                    )
                cur.execute("SELECT * FROM pm_alerts WHERE id = %s", (alert_id,))
                row = cur.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    cache.invalidate("summary")
    return {**row, "work_order_id": work_order_id}


def assert_work_order_access(work_order_id: int, token: dict[str, Any]) -> dict[str, Any]:
    row = fetch_one("SELECT device_id, module_id, assigned_to FROM pm_work_orders WHERE id = %s", (work_order_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Work order not found")
    if token.get("role") != "admin" and int(row.get("assigned_to") or 0) != int(token["sub"]):
        raise HTTPException(status_code=403, detail="This work order is not assigned to you")
    return row


def seed_demo_data() -> None:
    if not settings.seed_demo_data:
        return
    existing = fetch_one("SELECT COUNT(*) AS count FROM pm_devices")
    if existing and int(existing["count"]) > 0:
        return

    rng = random.Random(9046)
    base_time = datetime.now() - timedelta(minutes=90)
    devices = [
        ("ESP32-HT9046-31", "HT9046-31", "Line A / Handler 31", 0.1),
        ("ESP32-HT9046-35", "HT9046-35", "Line A / Handler 35", 0.65),
        ("ESP32-HT9046-39", "HT9046-39", "Line B / Handler 39", 1.0),
    ]
    modules = [
        ("vacuum-pump", "Vacuum Pump"),
        ("drive-motor", "Drive Motor"),
        ("power-unit", "Power Unit"),
    ]

    for device_uid, machine_code, location, fault_level in devices:
        for module_code, module_name in modules:
            module_bias = 0.0 if module_code == "vacuum-pump" else -0.12
            for i in range(36):
                t = i / 8.0
                heat_fault = fault_level * max(0, i - 18) * 0.45 if module_code == "vacuum-pump" else 0
                vib_fault = fault_level * max(0, i - 20) * 0.045 if module_code == "vacuum-pump" else 0
                payload = {
                    "device_id": device_uid,
                    "machine_code": machine_code,
                    "display_name": machine_code,
                    "location": location,
                    "module_code": module_code,
                    "module_name": module_name,
                    "timestamp": (base_time + timedelta(minutes=i * 2.5)).isoformat(),
                    "temperature": 42 + heat_fault + 2.0 * math.sin(t) + rng.uniform(-0.4, 0.4),
                    "pressure": -78 + fault_level * 10 + rng.uniform(-1.5, 1.5),
                    "current": 5.8 + fault_level * 3.2 + module_bias + 0.35 * math.sin(t / 2) + rng.uniform(-0.12, 0.12),
                    "ax": 0.03 + rng.uniform(-0.05, 0.05),
                    "ay": 0.02 + rng.uniform(-0.05, 0.05),
                    "az": 1.0 + rng.uniform(-0.04, 0.04),
                    "vibration": 0.75 + fault_level * 0.9 + vib_fault + rng.uniform(-0.05, 0.05),
                }
                if device_uid.endswith("-39") and module_code == "vacuum-pump" and i > 26:
                    payload["temperature"] += 11
                    payload["current"] += 3.8
                    payload["vibration"] += 0.85
                ingest_telemetry(payload, source="seed", topic="adi/seed/seed/telemetry")

    admin = fetch_one("SELECT id FROM pm_users WHERE username = %s", (settings.admin_username,))
    user = fetch_one("SELECT id FROM pm_users WHERE username = %s", (settings.user_username,))
    target = fetch_one(
        """
        SELECT d.id AS device_id, m.id AS module_id
        FROM pm_devices d
        INNER JOIN pm_modules m ON m.device_id = d.id
        WHERE d.machine_code = 'HT9046-39' AND m.module_code = 'vacuum-pump'
        LIMIT 1
        """
    )
    if admin and user and target:
        create_work_order(
            {
                "device_id": target["device_id"],
                "module_id": target["module_id"],
                "title": "Inspect HT9046-39 vacuum pump",
                "description": "Temperature, current, and vibration are trending above the maintenance band.",
                "priority": "HIGH",
                "assigned_to": user["id"],
            },
            created_by=admin["id"],
        )
