"""Read-only adapters for the live MySQL telemetry sources.

The dashboard never inserts, updates, or deletes rows in these sources.  It
keeps only dashboard metadata (users, module status, alerts, work orders) in
its own ``pm_*`` database.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
import logging
import queue
from contextlib import contextmanager
import re
import threading
import time
from typing import Any, Callable

import pymysql
from pymysql.cursors import DictCursor

from .config import settings
from .diagnostics import estimate_vacuum_pressure_kpa


log = logging.getLogger("adi.telemetry_sources")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COMPRESSOR_MODULE_NAMES = {
    1: "Index L Arm1", 2: "Index R Arm1", 3: "Index L Arm2", 4: "Index R Arm2",
    5: "SH1", 6: "SH2", 7: "Hot1", 8: "Hot2",
}


def _identifier(value: str, label: str) -> str:
    text = str(value).strip()
    if not IDENTIFIER_RE.fullmatch(text):
        raise ValueError(f"{label} must be a simple MySQL identifier")
    return f"`{text}`"


@lru_cache(maxsize=512)
def _normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if value is None:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        return None


def _machine_code(value: Any) -> str:
    raw = str(value).strip()
    match = re.fullmatch(r"(?:HT9046MX[-_]?|MX[-_]?|VP[-_]?|VACUUM[-_]?)?0*([0-9]{1,20})", raw, flags=re.IGNORECASE)
    if match and match.group(1):
        return f"HT9046MX-{int(match.group(1)):03d}"
    return raw


@dataclass(frozen=True)
class ExternalTelemetrySample:
    source: str
    source_id: str
    device_uid: str
    machine_code: str
    display_name: str
    module_code: str
    module_name: str
    recorded_at: datetime
    temperature_c: float | None = None
    pressure_kpa: float | None = None
    current_a: float | None = None
    accel_x: float | None = None
    accel_y: float | None = None
    accel_z: float | None = None
    vibration: float | None = None
    operating_status: str | None = None
    set_valve_status: str | None = None
    metrics: dict[str, tuple[float, str | None]] = field(default_factory=dict)

    def history_row(self, device_id: int, module_id: int) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "device_id": device_id,
            "module_id": module_id,
            "recorded_at": self.recorded_at,
            "temperature_c": self.temperature_c,
            "pressure_kpa": self.pressure_kpa,
            "current_a": self.current_a,
            "accel_x": self.accel_x,
            "accel_y": self.accel_y,
            "accel_z": self.accel_z,
            "vibration": self.vibration,
            "gyro_x": None,
            "gyro_y": None,
            "gyro_z": None,
            "source": self.source,
            "operating_status": self.operating_status,
            "set_valve_status": self.set_valve_status,
            **{key: value for key, (value, _unit) in self.metrics.items()},
        }


@dataclass(frozen=True)
class ExternalHealthScore:
    machine_code: str
    module_number: int
    recorded_at: datetime
    health_score: float
    condition: str | None
    model_version: str | None


class ReadOnlyTelemetrySources:
    """Read external telemetry without ever changing its schemas or rows."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._source_locks = {source: threading.RLock() for source in ("vacuum", "compressor")}
        self._history_flights = {source: [threading.Lock() for _ in range(64)] for source in ("vacuum", "compressor")}
        self._wide_flights = [threading.Lock() for _ in range(32)]
        self._history_pools = {source: queue.Queue(maxsize=4) for source in ("vacuum", "compressor")}
        self._history_pool_locks = {source: threading.Lock() for source in ("vacuum", "compressor")}
        self._history_pool_sizes = {source: 0 for source in ("vacuum", "compressor")}
        self._conns: dict[str, pymysql.connections.Connection] = {}
        self._latest: dict[tuple[int, int], ExternalTelemetrySample] = {}
        self._health_scores: dict[tuple[str, int], ExternalHealthScore] = {}
        self._history_cache: collections.OrderedDict[tuple[str, str, str, str, int], tuple[float, list[ExternalTelemetrySample]]] = collections.OrderedDict()
        self._compressor_history_rows: collections.OrderedDict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = collections.OrderedDict()
        self._last_error: dict[str, str | None] = {"vacuum": None, "compressor": None}
        self._last_success_at: dict[str, datetime | None] = {"vacuum": None, "compressor": None}
        self._health_last_error: str | None = None
        self._health_last_success_at: datetime | None = None
        self._last_poll_at: datetime | None = None
        self._poll_count = 0
        self._last_sample_count = 0

    @property
    def configured(self) -> bool:
        return self.source_configured("vacuum") and self.source_configured("compressor")

    @staticmethod
    def source_configured(source: str) -> bool:
        if source == "vacuum":
            return bool(settings.telemetry_enabled and settings.vacuum_db_user and settings.vacuum_db_password)
        if source == "compressor":
            return bool(settings.telemetry_enabled and settings.compressor_db_user and settings.compressor_db_password)
        raise ValueError(f"Unknown telemetry source: {source}")

    @staticmethod
    def _credentials(source: str) -> tuple[str, str]:
        if source == "vacuum":
            return settings.vacuum_db_user, settings.vacuum_db_password
        if source == "compressor":
            return settings.compressor_db_user, settings.compressor_db_password
        raise ValueError(f"Unknown telemetry source: {source}")

    def _connect(self, source: str):
        if not self.source_configured(source):
            raise RuntimeError(f"{source.title()} MySQL credentials must be configured")
        with self._source_locks[source]:
            conn = self._conns.get(source)
            if conn is not None:
                try:
                    conn.ping(reconnect=True)
                    return conn
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
            conn = self._open_connection(source)
            self._conns[source] = conn
            return conn

    def _open_connection(self, source: str):
        user, password = self._credentials(source)
        return pymysql.connect(
            host=settings.telemetry_db_host, port=settings.telemetry_db_port,
            user=user, password=password, charset=settings.telemetry_db_charset,
            cursorclass=DictCursor, autocommit=True,
            connect_timeout=settings.telemetry_connect_timeout_seconds,
            read_timeout=settings.telemetry_read_timeout_seconds,
            write_timeout=settings.telemetry_read_timeout_seconds,
        )

    @contextmanager
    def _history_connection(self, source: str):
        pool = self._history_pools[source]
        connection = None
        create = False
        with self._history_pool_locks[source]:
            try:
                connection = pool.get_nowait()
            except queue.Empty:
                if self._history_pool_sizes[source] < pool.maxsize:
                    self._history_pool_sizes[source] += 1
                    create = True
        if create:
            try:
                connection = self._open_connection(source)
            except Exception:
                with self._history_pool_locks[source]:
                    self._history_pool_sizes[source] -= 1
                raise
        elif connection is None:
            connection = pool.get(timeout=settings.telemetry_read_timeout_seconds)
        try:
            connection.ping(reconnect=True)
            yield connection
        except Exception:
            try:
                connection.close()
            finally:
                with self._history_pool_locks[source]:
                    self._history_pool_sizes[source] -= 1
            raise
        else:
            pool.put_nowait(connection)

    def _query(self, source: str, sql: str, params: tuple[Any, ...] = (), *, history: bool = False) -> list[dict[str, Any]]:
        if history:
            # History has a bounded pool, independent of the latest-data poller.
            with self._history_connection(source) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    return list(cursor.fetchall())
        with self._source_locks[source]:
            connection = self._connect(source)
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())

    @staticmethod
    def _row_value(row: dict[str, Any], *aliases: str) -> Any:
        normalized = {_normal(key): value for key, value in row.items()}
        for alias in aliases:
            if _normal(alias) in normalized:
                return normalized[_normal(alias)]
        return None

    @staticmethod
    def _module_value(row: dict[str, Any], aliases: tuple[str, ...], module_number: int) -> Any:
        normalized = {_normal(key): value for key, value in row.items()}
        for alias in aliases:
            base = _normal(alias)
            for candidate in (f"{base}{module_number}", f"{base}m{module_number}", f"m{module_number}{base}"):
                if candidate in normalized:
                    return normalized[candidate]
        return None

    def _vacuum_latest_rows(self) -> list[dict[str, Any]]:
        table = f"{_identifier(settings.vacuum_schema, 'VACUUM_SCHEMA')}.{_identifier(settings.vacuum_table, 'VACUUM_TABLE')}"
        device = _identifier(settings.vacuum_device_column, "VACUUM_DEVICE_COLUMN")
        return self._query(
            "vacuum",
            f"""
            SELECT r.id, r.{device} AS devices_id, r.recorded_at, r.temperature,
                   r.accel_x, r.accel_y, r.accel_z, r.vibration, r.current_amp
            FROM {table} AS r
            INNER JOIN (
                SELECT {device}, MAX(id) AS max_id
                FROM {table}
                GROUP BY {device}
            ) AS newest ON newest.max_id = r.id
            ORDER BY r.{device}
            """
        )

    def _compressor_latest_rows(self) -> list[dict[str, Any]]:
        table = f"{_identifier(settings.compressor_schema, 'COMPRESSOR_SCHEMA')}.{_identifier(settings.compressor_table, 'COMPRESSOR_TABLE')}"
        machine = _identifier(settings.compressor_machine_column, 'COMPRESSOR_MACHINE_COLUMN')
        timestamp = _identifier(settings.compressor_timestamp_column, 'COMPRESSOR_TIMESTAMP_COLUMN')
        return self._query(
            "compressor",
            f"""
            SELECT r.*
            FROM {table} AS r
            INNER JOIN (
                SELECT {machine} AS machine_value, MAX({timestamp}) AS newest_at
                FROM {table}
                WHERE {machine} IS NOT NULL
                GROUP BY {machine}
            ) AS newest
              ON newest.machine_value = r.{machine} AND newest.newest_at = r.{timestamp}
            ORDER BY r.{machine}
            """
        )

    def _compressor_health_latest_rows(self) -> list[dict[str, Any]]:
        table = (
            f"{_identifier(settings.compressor_health_schema, 'COMPRESSOR_HEALTH_SCHEMA')}."
            f"{_identifier(settings.compressor_health_table, 'COMPRESSOR_HEALTH_TABLE')}"
        )
        machine = _identifier(settings.compressor_health_machine_column, "COMPRESSOR_HEALTH_MACHINE_COLUMN")
        module = _identifier(settings.compressor_health_module_column, "COMPRESSOR_HEALTH_MODULE_COLUMN")
        timestamp = _identifier(settings.compressor_health_timestamp_column, "COMPRESSOR_HEALTH_TIMESTAMP_COLUMN")
        score = _identifier(settings.compressor_health_score_column, "COMPRESSOR_HEALTH_SCORE_COLUMN")
        condition = _identifier(settings.compressor_health_condition_column, "COMPRESSOR_HEALTH_CONDITION_COLUMN")
        model = _identifier(settings.compressor_health_model_column, "COMPRESSOR_HEALTH_MODEL_COLUMN")
        return self._query(
            "compressor",
            f"""
            SELECT h.{machine} AS machine_number,
                   h.{module} AS module_id,
                   h.{timestamp} AS recorded_at,
                   h.{score} AS health_score,
                   h.{condition} AS health_condition,
                   h.{model} AS model_version
            FROM {table} AS h
            INNER JOIN (
                SELECT {machine} AS machine_value,
                       {module} AS module_value,
                       MAX({timestamp}) AS newest_at
                FROM {table}
                GROUP BY {machine}, {module}
            ) AS newest
              ON newest.machine_value = h.{machine}
             AND newest.module_value = h.{module}
             AND newest.newest_at = h.{timestamp}
            WHERE h.id = (
                SELECT MAX(tie.id) FROM {table} AS tie
                WHERE tie.{machine} = h.{machine}
                  AND tie.{module} = h.{module}
                  AND tie.{timestamp} = h.{timestamp}
            )
            """,
        )

    def _refresh_compressor_health_scores(self) -> None:
        if not settings.compressor_health_enabled:
            with self._lock:
                self._health_scores = {}
                self._health_last_error = None
            return
        try:
            scores: dict[tuple[str, int], ExternalHealthScore] = {}
            for row in self._compressor_health_latest_rows():
                stamp = _datetime(row.get("recorded_at"))
                score = _number(row.get("health_score"))
                module_match = re.search(r"([1-8])", str(row.get("module_id") or ""))
                if stamp is None or score is None or not module_match:
                    continue
                machine_code = _machine_code(row.get("machine_number"))
                item = ExternalHealthScore(
                    machine_code=machine_code,
                    module_number=int(module_match.group(1)),
                    recorded_at=stamp,
                    health_score=max(0.0, min(100.0, score)),
                    condition=None if row.get("health_condition") is None else str(row.get("health_condition")),
                    model_version=None if row.get("model_version") is None else str(row.get("model_version")),
                )
                scores[(machine_code, item.module_number)] = item
            with self._lock:
                self._health_scores = scores
                self._health_last_error = None
                self._health_last_success_at = datetime.now()
        except Exception as exc:
            log.warning("Could not read Compressor health-score table: %s", exc)
            with self._lock:
                self._health_last_error = f"{type(exc).__name__}: {exc}"

    def _vacuum_sample(self, row: dict[str, Any]) -> ExternalTelemetrySample | None:
        external_id = row.get("devices_id")
        recorded_at = _datetime(row.get("recorded_at"))
        if external_id is None or recorded_at is None:
            return None
        external_key = str(external_id).strip()
        vibration = _number(row.get("vibration"))
        estimated_pressure = estimate_vacuum_pressure_kpa(vibration)
        return ExternalTelemetrySample(
            source="vacuum",
            source_id=f"vacuum:{row.get('id')}",
            device_uid=f"vacuum:{external_key}",
            machine_code=_machine_code(external_key),
            display_name=_machine_code(external_key),
            module_code="vacuum-pump",
            module_name="Vacuum Pump",
            recorded_at=recorded_at,
            temperature_c=_number(row.get("temperature")),
            pressure_kpa=estimated_pressure,
            current_a=_number(row.get("current_amp")),
            accel_x=_number(row.get("accel_x")),
            accel_y=_number(row.get("accel_y")),
            accel_z=_number(row.get("accel_z")),
            vibration=vibration,
            metrics={
                key: (value, unit)
                for key, value, unit in (
                    ("temperature", _number(row.get("temperature")), "C"),
                    ("current_amp", _number(row.get("current_amp")), "A"),
                    ("accel_x", _number(row.get("accel_x")), "g"),
                    ("accel_y", _number(row.get("accel_y")), "g"),
                    ("accel_z", _number(row.get("accel_z")), "g"),
                    ("vibration", vibration, "G rms"),
                    ("estimated_pressure_kpa", estimated_pressure, "kPa"),
                )
                if value is not None
            },
        )

    def _compressor_samples(self, row: dict[str, Any], target_module: int | None = None, *, include_empty: bool = False) -> list[ExternalTelemetrySample]:
        normalized = {_normal(key): value for key, value in row.items()}
        raw_machine = None
        for alias in (settings.compressor_machine_column, "machine_number", "machinenumber"):
            norm_alias = _normal(alias)
            if norm_alias in normalized:
                raw_machine = normalized[norm_alias]
                break
        recorded_at = None
        for alias in (settings.compressor_timestamp_column, "recorded_at", "recordedat"):
            norm_alias = _normal(alias)
            if norm_alias in normalized:
                recorded_at = normalized[norm_alias]
                break
        stamp = _datetime(recorded_at)
        if raw_machine is None or stamp is None:
            return []
        machine_value = str(raw_machine).strip()
        machine_code = _machine_code(machine_value)
        output: list[ExternalTelemetrySample] = []
        aliases = {
            "hp_1st": ("hp_1st", "hp1st", "highpressure1st"),
            "lp_1st": ("lp_1st", "lp1st", "lowpressure1st"),
            "hp_2nd": ("hp_2nd", "hp2nd", "highpressure2nd"),
            "lp_2nd": ("lp_2nd", "lp2nd", "lowpressure2nd"),
            "valve": ("valve", "valveposition"),
            "temperature_hi": ("temphi", "temperaturehi", "hightemperature"),
            "temperature_lo": ("templo", "temperaturelo", "lowtemperature"),
            "status": ("status", "module_status"),
            "busy": ("busy", "is_busy"),
            "sv": ("sv", "setvalue", "set_value"),
        }
        module_range = (target_module,) if target_module else range(1, 9)
        for module_number in module_range:
            values: dict[str, Any] = {}
            for key, names in aliases.items():
                val = None
                for alias in names:
                    base = _normal(alias)
                    for candidate in (f"{base}{module_number}", f"{base}m{module_number}", f"m{module_number}{base}"):
                        if candidate in normalized:
                            val = normalized[candidate]
                            break
                    if val is not None:
                        break
                values[key] = val
            def control_number(value):
                if value is None: return None
                text=str(value).strip().lower()
                return 1.0 if text in {'on','true','1'} else 0.0 if text in {'off','false','0'} else None
            numeric = {key: control_number(value) if key in {'sv','busy'} else _number(value) for key,value in values.items()}
            if not include_empty and not any(numeric[key] is not None for key in ("hp_1st", "lp_1st", "hp_2nd", "lp_2nd", "valve", "temperature_hi", "temperature_lo")):
                continue
            scale = 0.1 if settings.compressor_sensor_scale == "0.1" else 1.0
            numeric = {key: value * scale if value is not None and key not in {"valve", "busy", "sv"} else value for key, value in numeric.items()}
            metrics: dict[str, tuple[float, str | None]] = {
                key: (value, None)
                for key, value in numeric.items()
                if value is not None
            }
            output.append(
                ExternalTelemetrySample(
                    source="compressor",
                    source_id=f"compressor:{machine_value}:{stamp.isoformat()}:{module_number}",
                    device_uid=f"compressor:{machine_value}",
                    machine_code=machine_code,
                    display_name=machine_code,
                    module_code=f"compressor-m{module_number}",
                    module_name=f"M{module_number} · {COMPRESSOR_MODULE_NAMES[module_number]}",
                    recorded_at=stamp,
                    temperature_c=numeric["temperature_hi"],
                    pressure_kpa=numeric["hp_1st"],
                    operating_status=None if values["status"] is None else str(values["status"]),
                    set_valve_status=None if values["sv"] is None else str(values["sv"]),
                    metrics=metrics,
                )
            )
        return output

    def latest_samples(self) -> list[ExternalTelemetrySample]:
        if not settings.telemetry_enabled:
            return []
        self._refresh_compressor_health_scores()
        output: list[ExternalTelemetrySample] = []
        source_queries = (
            ("vacuum", self._vacuum_latest_rows, lambda rows: [sample for row in rows if (sample := self._vacuum_sample(row))]),
            ("compressor", self._compressor_latest_rows, lambda rows: [sample for row in rows for sample in self._compressor_samples(row)]),
        )
        for source, query, decode in source_queries:
            if not self.source_configured(source):
                with self._lock:
                    self._last_error[source] = "Credentials not configured"
                continue
            try:
                samples = decode(query())
                output.extend(samples)
                with self._lock:
                    self._last_error[source] = None
                    self._last_success_at[source] = datetime.now()
            except Exception as exc:
                log.warning("Could not read %s telemetry: %s", source, exc)
                with self._lock:
                    self._last_error[source] = f"{type(exc).__name__}: {exc}"
        with self._lock:
            self._last_poll_at = datetime.now()
            self._poll_count += 1
            self._last_sample_count = len(output)
        return output

    def remember(self, device_id: int, module_id: int, sample: ExternalTelemetrySample) -> None:
        with self._lock:
            self._latest[(device_id, module_id)] = sample

    def latest_for(self, device_id: int, module_id: int) -> ExternalTelemetrySample | None:
        with self._lock:
            return self._latest.get((device_id, module_id))

    def health_for(self, machine_code: str, module_code: str) -> ExternalHealthScore | None:
        match = re.fullmatch(r"compressor-m([1-8])", str(module_code))
        if not match:
            return None
        with self._lock:
            return self._health_scores.get((_machine_code(machine_code), int(match.group(1))))

    def _vacuum_history(self, external_id: str, limit: int) -> list[ExternalTelemetrySample]:
        table = f"{_identifier(settings.vacuum_schema, 'VACUUM_SCHEMA')}.{_identifier(settings.vacuum_table, 'VACUUM_TABLE')}"
        device = _identifier(settings.vacuum_device_column, "VACUUM_DEVICE_COLUMN")
        rows = self._query(
            "vacuum",
            f"""
            SELECT id, {device} AS devices_id, recorded_at, temperature, accel_x, accel_y, accel_z, vibration, current_amp
            FROM {table}
            WHERE {device} = %s
            ORDER BY recorded_at DESC, id DESC
            LIMIT %s
            """,
            (external_id, limit),
            history=True,
        )
        samples = [sample for row in rows if (sample := self._vacuum_sample(row))]
        return list(reversed(samples))

    def _compressor_history(self, machine: str, module_number: int, limit: int) -> list[ExternalTelemetrySample]:
        table = f"{_identifier(settings.compressor_schema, 'COMPRESSOR_SCHEMA')}.{_identifier(settings.compressor_table, 'COMPRESSOR_TABLE')}"
        machine_column = _identifier(settings.compressor_machine_column, 'COMPRESSOR_MACHINE_COLUMN')
        timestamp = _identifier(settings.compressor_timestamp_column, 'COMPRESSOR_TIMESTAMP_COLUMN')
        # A wide source row contains every module: reuse the read for the same
        # machine/limit across module requests, without mixing machine identities.
        key = (machine, limit)
        with self._wide_flights[hash(key) % len(self._wide_flights)]:
            with self._lock:
                cached = self._compressor_history_rows.get(key)
                if cached and cached[0] > time.monotonic():
                    rows = cached[1]
                    self._compressor_history_rows.move_to_end(key)
                else:
                    rows = None
            if rows is None:
                rows = self._query(
                    "compressor",
                    f"SELECT * FROM {table} WHERE {machine_column} = %s ORDER BY {timestamp} DESC LIMIT %s",
                    (machine, limit),
                    history=True,
                )
                with self._lock:
                    self._compressor_history_rows[key] = (time.monotonic() + 3.0, rows)
                    self._compressor_history_rows.move_to_end(key)
                    while len(self._compressor_history_rows) > 8:
                        self._compressor_history_rows.popitem(last=False)
        selected: list[ExternalTelemetrySample] = []
        for row in rows:
            selected.extend(self._compressor_samples(row, target_module=module_number))
        return list(reversed(selected))

    def history_for(
        self,
        device_uid: str,
        module_code: str,
        limit: int,
        *,
        source: str | None = None,
        source_device_key: str | None = None,
    ) -> list[ExternalTelemetrySample] | None:
        source = source or (device_uid.split(":", 1)[0] if ":" in device_uid else None)
        source_device_key = source_device_key or (device_uid.split(":", 1)[1] if ":" in device_uid else None)
        if source not in {"vacuum", "compressor"} or not self.source_configured(source):
            return None
        # Detail history (2,000) and metric (3,000) panels share one bounded
        # source read instead of hitting the same wide Compressor table twice.
        query_limit = 3000 if source == "compressor" and 1000 <= limit <= 3000 else limit
        key = (source, device_uid, module_code, source_device_key or "", query_limit)
        # Coalesce the same identity; release the state lock during I/O/mapping.
        # Fixed stripes bound synchronization memory across arbitrary queries.
        with self._history_flights[source][hash(key) % len(self._history_flights[source])]:
            with self._lock:
                cached = self._history_cache.get(key)
                if cached and cached[0] > time.monotonic():
                    self._history_cache.move_to_end(key)
                    return cached[1][-limit:]
            try:
                result: list[ExternalTelemetrySample] | None = None
                if source == "vacuum" and source_device_key and module_code == "vacuum-pump":
                    result = self._vacuum_history(source_device_key, query_limit)
                else:
                    match = re.fullmatch(r"compressor:(.+)", device_uid)
                    module_match = re.fullmatch(r"compressor-m([1-8])", module_code)
                    compressor_key = source_device_key or (match.group(1) if match else None)
                    if source == "compressor" and compressor_key and module_match:
                        result = self._compressor_history(compressor_key, int(module_match.group(1)), query_limit)
                if result is not None:
                    with self._lock:
                        self._history_cache[key] = (time.monotonic() + 3.0, result)
                        self._history_cache.move_to_end(key)
                        while len(self._history_cache) > 32:
                            self._history_cache.popitem(last=False)
                return result[-limit:] if result is not None else None
            except Exception as exc:
                log.warning("Could not read source history: %s", exc)
                return []

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": settings.telemetry_enabled,
                "configured": self.configured,
                "host": settings.telemetry_db_host,
                "port": settings.telemetry_db_port,
                "poll_interval_seconds": settings.telemetry_poll_interval_seconds,
                "last_poll_at": self._last_poll_at,
                "poll_count": self._poll_count,
                "last_sample_count": self._last_sample_count,
                "sources": {
                    "vacuum": {
                        "configured": self.source_configured("vacuum"),
                        "schema": settings.vacuum_schema,
                        "table": settings.vacuum_table,
                        "last_success_at": self._last_success_at["vacuum"],
                        "error": self._last_error["vacuum"],
                    },
                    "compressor": {
                        "configured": self.source_configured("compressor"),
                        "schema": settings.compressor_schema,
                        "table": settings.compressor_table,
                        "last_success_at": self._last_success_at["compressor"],
                        "error": self._last_error["compressor"],
                    },
                },
                "compressor_health_scores": {
                    "enabled": settings.compressor_health_enabled,
                    "schema": settings.compressor_health_schema,
                    "table": settings.compressor_health_table,
                    "cached_scores": len(self._health_scores),
                    "last_success_at": self._health_last_success_at,
                    "error": self._health_last_error,
                },
            }


class MySQLTelemetryPoller:
    def __init__(self, sources: ReadOnlyTelemetrySources) -> None:
        self.sources = sources
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._seen: collections.OrderedDict[str, None] = collections.OrderedDict()

    def start(
        self,
        on_sample: Callable[[ExternalTelemetrySample], None],
        on_cycle: Callable[[], None] | None = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def run() -> None:
            while not self._stop.is_set():
                changed = False
                for sample in self.sources.latest_samples():
                    dedupe_id = sample.source_id
                    health = self.sources.health_for(sample.machine_code, sample.module_code)
                    if health:
                        dedupe_id = f"{dedupe_id}:health:{health.recorded_at.isoformat()}"
                    if dedupe_id in self._seen:
                        continue
                    try:
                        on_sample(sample)
                        changed = True
                        self._seen[dedupe_id] = None
                        if len(self._seen) > 10000:
                            for _ in range(2000):
                                self._seen.popitem(last=False)
                    except Exception as exc:
                        log.warning("Could not register live sample %s: %s", sample.source_id, exc)
                if changed and on_cycle:
                    try:
                        on_cycle()
                    except Exception as exc:
                        log.warning("Could not publish telemetry cycle: %s", exc)
                self._stop.wait(settings.telemetry_poll_interval_seconds)

        self._thread = threading.Thread(target=run, name="mysql-telemetry-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)


telemetry_sources = ReadOnlyTelemetrySources()
telemetry_poller = MySQLTelemetryPoller(telemetry_sources)
