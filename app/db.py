from __future__ import annotations

import json
import logging
import queue
import threading
from contextlib import contextmanager
from typing import Any, Iterable

import pymysql
from pymysql.cursors import DictCursor

from .auth import hash_password
from .config import settings

log = logging.getLogger("adi.db")

DEVICE_STATUS_ENUM = (
    "'NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED', "
    "'UNDER_MAINTENANCE', 'OFFLINE'"
)

class DatabaseNotReady(RuntimeError):
    pass


last_startup_error: str | None = None


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

_POOL_MIN = 2
_POOL_MAX = 10

_pool: queue.Queue[pymysql.connections.Connection] = queue.Queue(maxsize=_POOL_MAX)
_pool_size = 0          # total connections created (in pool + checked out)
_pool_lock = threading.Lock()


def _raw_connect(database: bool = True):
    kwargs = {
        "host": settings.db_host,
        "port": settings.db_port,
        "user": settings.db_user,
        "password": settings.db_password,
        "charset": settings.db_charset,
        "cursorclass": DictCursor,
        "autocommit": True,
    }
    if database:
        kwargs["database"] = settings.db_name
    return pymysql.connect(**kwargs)


def _pool_init() -> None:
    global _pool_size
    with _pool_lock:
        while _pool_size < _POOL_MIN:
            try:
                conn = _raw_connect(database=True)
                _pool.put_nowait(conn)
                _pool_size += 1
            except Exception:
                break


def _pool_get() -> pymysql.connections.Connection:
    global _pool_size
    # Try to grab an existing pooled connection
    try:
        conn = _pool.get_nowait()
        try:
            conn.ping(reconnect=False)
            return conn
        except Exception:
            # Connection is dead — discard it, decrement size
            with _pool_lock:
                _pool_size -= 1
            try:
                conn.close()
            except Exception:
                pass
    except queue.Empty:
        pass

    # No healthy connection available — create a new one if under limit
    with _pool_lock:
        if _pool_size < _POOL_MAX:
            _pool_size += 1
            try:
                return _raw_connect(database=True)
            except Exception:
                _pool_size -= 1
                raise

    # At max capacity — block until one is returned (up to 10s)
    try:
        conn = _pool.get(timeout=10)
        try:
            conn.ping(reconnect=False)
            return conn
        except Exception:
            with _pool_lock:
                _pool_size -= 1
            try:
                conn.close()
            except Exception:
                pass
            # One retry — create a fresh connection instead of recursing
            with _pool_lock:
                if _pool_size < _POOL_MAX:
                    _pool_size += 1
                    try:
                        return _raw_connect(database=True)
                    except Exception:
                        _pool_size -= 1
                        raise
            raise DatabaseNotReady("Connection pool exhausted — all connections dead")
    except queue.Empty:
        raise DatabaseNotReady("Connection pool exhausted — timeout waiting for connection")


def _pool_put(conn: pymysql.connections.Connection) -> None:
    try:
        _pool.put_nowait(conn)
    except queue.Full:
        # Pool is full — just close the excess connection
        global _pool_size
        with _pool_lock:
            _pool_size -= 1
        try:
            conn.close()
        except Exception:
            pass


def _pool_discard(conn: pymysql.connections.Connection) -> None:
    global _pool_size
    with _pool_lock:
        _pool_size -= 1
    try:
        conn.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API (unchanged signatures)
# ---------------------------------------------------------------------------

def connect(database: bool = True):
    if not database:
        return _raw_connect(database=False)
    return _pool_get()


@contextmanager
def connection(database: bool = True):
    if not database:
        conn = _raw_connect(database=False)
        try:
            yield conn
        finally:
            conn.close()
        return

    conn = _pool_get()
    try:
        yield conn
    except pymysql.OperationalError:
        _pool_discard(conn)
        raise
    except Exception:
        _pool_put(conn)
        raise
    else:
        _pool_put(conn)


def fetch_one(sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params or ()))
        return cur.fetchone()


def fetch_all(sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params or ()))
        return list(cur.fetchall())


def execute(sql: str, params: Iterable[Any] | None = None) -> int:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params or ()))
        return cur.lastrowid


def execute_many(sql: str, rows: list[Iterable[Any]]) -> None:
    if not rows:
        return
    with connection() as conn, conn.cursor() as cur:
        cur.executemany(sql, rows)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


# ---------------------------------------------------------------------------
# Schema / migrations
# ---------------------------------------------------------------------------

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS pm_users (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        username VARCHAR(80) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(160) NULL,
        role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_pm_users_username (username),
        KEY idx_pm_users_role (role)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_devices (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_uid VARCHAR(120) NOT NULL,
        machine_code VARCHAR(120) NOT NULL,
        display_name VARCHAR(160) NOT NULL,
        location VARCHAR(160) NULL,
        firmware_version VARCHAR(80) NULL,
        status ENUM('NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED', 'UNDER_MAINTENANCE', 'OFFLINE') NOT NULL DEFAULT 'OFFLINE',
        first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_pm_devices_uid (device_uid),
        KEY idx_pm_devices_machine (machine_code),
        KEY idx_pm_devices_status (status),
        KEY idx_pm_devices_last_seen (last_seen)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_modules (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED NOT NULL,
        module_code VARCHAR(100) NOT NULL,
        module_name VARCHAR(160) NOT NULL,
        module_type VARCHAR(120) NULL,
        telemetry_source VARCHAR(40) NULL,
        source_device_key VARCHAR(160) NULL,
        status ENUM('NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED', 'UNDER_MAINTENANCE', 'OFFLINE') NOT NULL DEFAULT 'OFFLINE',
        thresholds_json JSON NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_pm_modules_device_code (device_id, module_code),
        KEY idx_pm_modules_status (status),
        CONSTRAINT fk_pm_modules_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_sensor_readings (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED NOT NULL,
        module_id BIGINT UNSIGNED NOT NULL,
        recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR(40) NOT NULL DEFAULT 'mqtt',
        temperature_c DOUBLE NULL,
        pressure_kpa DOUBLE NULL,
        current_a DOUBLE NULL,
        accel_x DOUBLE NULL,
        accel_y DOUBLE NULL,
        accel_z DOUBLE NULL,
        vibration DOUBLE NULL,
        gyro_x DOUBLE NULL,
        gyro_y DOUBLE NULL,
        gyro_z DOUBLE NULL,
        raw_payload JSON NULL,
        PRIMARY KEY (id),
        KEY idx_pm_sensor_module_time (module_id, recorded_at),
        KEY idx_pm_sensor_device_time (device_id, recorded_at),
        CONSTRAINT fk_pm_sensor_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_sensor_module
            FOREIGN KEY (module_id) REFERENCES pm_modules(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_sensor_metrics (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        reading_id BIGINT UNSIGNED NOT NULL,
        device_id BIGINT UNSIGNED NOT NULL,
        module_id BIGINT UNSIGNED NOT NULL,
        recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metric_key VARCHAR(160) NOT NULL,
        metric_value DOUBLE NOT NULL,
        unit VARCHAR(40) NULL,
        source_key VARCHAR(220) NULL,
        PRIMARY KEY (id),
        KEY idx_pm_metrics_module_key_time (module_id, metric_key, recorded_at),
        KEY idx_pm_metrics_device_time (device_id, recorded_at),
        KEY idx_pm_metrics_reading (reading_id),
        CONSTRAINT fk_pm_metrics_reading
            FOREIGN KEY (reading_id) REFERENCES pm_sensor_readings(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_metrics_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_metrics_module
            FOREIGN KEY (module_id) REFERENCES pm_modules(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_diagnostic_snapshots (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED NOT NULL,
        module_id BIGINT UNSIGNED NOT NULL,
        recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        source_recorded_at DATETIME(6) NULL,
        sample_count INT NULL,
        health_score INT NULL,
        condition_state ENUM('NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED') NOT NULL DEFAULT 'NORMAL',
        temperature_c DOUBLE NULL,
        temperature_avg_c DOUBLE NULL,
        temperature_trend_c_per_min DOUBLE NULL,
        pressure_kpa DOUBLE NULL,
        pressure_avg_kpa DOUBLE NULL,
        current_a DOUBLE NULL,
        current_avg_a DOUBLE NULL,
        vibration DOUBLE NULL,
        vibration_avg DOUBLE NULL,
        ai_model_version VARCHAR(80) NULL,
        ai_condition VARCHAR(80) NULL,
        ai_confidence DOUBLE NULL,
        ai_notes TEXT NULL,
        PRIMARY KEY (id),
        KEY idx_pm_diag_module_time (module_id, recorded_at),
        KEY idx_pm_diag_time_module (recorded_at, module_id),
        KEY idx_pm_diag_device_time (device_id, recorded_at),
        KEY idx_pm_diag_condition (condition_state),
        CONSTRAINT fk_pm_diag_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_diag_module
            FOREIGN KEY (module_id) REFERENCES pm_modules(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_alerts (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED NOT NULL,
        module_id BIGINT UNSIGNED NOT NULL,
        diagnostic_id BIGINT UNSIGNED NULL,
        issue_key VARCHAR(160) NOT NULL DEFAULT 'diagnostic_alert',
        severity ENUM('info', 'warning', 'critical') NOT NULL DEFAULT 'info',
        title VARCHAR(220) NOT NULL,
        message TEXT NULL,
        acknowledged TINYINT(1) NOT NULL DEFAULT 0,
        acknowledged_by BIGINT UNSIGNED NULL,
        acknowledged_at DATETIME NULL,
        suppressed_until DATETIME NULL,
        recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_pm_alerts_module_time (module_id, recorded_at),
        KEY idx_pm_alerts_issue_time (device_id, module_id, issue_key, recorded_at),
        KEY idx_pm_alerts_suppression (module_id, issue_key, suppressed_until),
        KEY idx_pm_alerts_severity (severity),
        CONSTRAINT fk_pm_alerts_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_alerts_module
            FOREIGN KEY (module_id) REFERENCES pm_modules(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_alerts_diag
            FOREIGN KEY (diagnostic_id) REFERENCES pm_diagnostic_snapshots(id)
            ON DELETE SET NULL,
        CONSTRAINT fk_pm_alerts_ack_user
            FOREIGN KEY (acknowledged_by) REFERENCES pm_users(id)
            ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_work_orders (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED NOT NULL,
        module_id BIGINT UNSIGNED NULL,
        title VARCHAR(220) NOT NULL,
        description TEXT NULL,
        priority ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL DEFAULT 'MEDIUM',
        status ENUM('OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED') NOT NULL DEFAULT 'OPEN',
        assigned_to BIGINT UNSIGNED NULL,
        created_by BIGINT UNSIGNED NULL,
        source_alert_id BIGINT UNSIGNED NULL,
        alert_recorded_at DATETIME NULL,
        report_origin VARCHAR(32) NULL,
        event_started_at DATETIME(6) NULL,
        event_ended_at DATETIME(6) NULL,
        event_timezone VARCHAR(64) NULL,
        event_time_precision VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
        due_at DATETIME NULL,
        completed_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_pm_work_status (status),
        KEY idx_pm_work_assigned (assigned_to),
        UNIQUE KEY uq_pm_work_source_alert (source_alert_id),
        CONSTRAINT fk_pm_work_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_work_module
            FOREIGN KEY (module_id) REFERENCES pm_modules(id)
            ON DELETE SET NULL,
        CONSTRAINT fk_pm_work_assigned
            FOREIGN KEY (assigned_to) REFERENCES pm_users(id)
            ON DELETE SET NULL,
        CONSTRAINT fk_pm_work_created
            FOREIGN KEY (created_by) REFERENCES pm_users(id)
            ON DELETE SET NULL,
        CONSTRAINT fk_pm_work_source_alert
            FOREIGN KEY (source_alert_id) REFERENCES pm_alerts(id)
            ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_maintenance_logs (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        device_id BIGINT UNSIGNED NOT NULL,
        module_id BIGINT UNSIGNED NULL,
        work_order_id BIGINT UNSIGNED NULL,
        technician_id BIGINT UNSIGNED NULL,
        technician_name VARCHAR(160) NOT NULL,
        action_taken TEXT NOT NULL,
        parts_used VARCHAR(220) NULL,
        parts_json JSON NULL,
        incident_context_json JSON NULL,
        other_cost_baht DECIMAL(12,2) NOT NULL DEFAULT 0,
        cost_baht DOUBLE NOT NULL DEFAULT 0,
        recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_pm_logs_recorded (recorded_at),
        KEY idx_pm_logs_device (device_id),
        CONSTRAINT fk_pm_logs_device
            FOREIGN KEY (device_id) REFERENCES pm_devices(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_pm_logs_module
            FOREIGN KEY (module_id) REFERENCES pm_modules(id)
            ON DELETE SET NULL,
        CONSTRAINT fk_pm_logs_work
            FOREIGN KEY (work_order_id) REFERENCES pm_work_orders(id)
            ON DELETE SET NULL,
        CONSTRAINT fk_pm_logs_technician
            FOREIGN KEY (technician_id) REFERENCES pm_users(id)
            ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS pm_deletion_audit (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        entity_type ENUM('MAINTENANCE_LOG','WORK_ORDER') NOT NULL,
        entity_id BIGINT UNSIGNED NOT NULL,
        actor_user_id BIGINT UNSIGNED NOT NULL,
        actor_username VARCHAR(160) NOT NULL,
        snapshot_json JSON NOT NULL,
        deleted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_pm_audit_entity (entity_type, entity_id),
        KEY idx_pm_audit_time (deleted_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


def init_database() -> None:
    global last_startup_error
    try:
        with connection(database=False) as conn, conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

        # Now that the database exists, bootstrap the pool
        _pool_init()

        with connection() as conn, conn.cursor() as cur:
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)
            run_schema_migrations(cur)

        seed_users()
        last_startup_error = None
    except Exception as exc:
        last_startup_error = str(exc)
        raise


def migrate_incident_evidence(cur) -> None:
    """Add nullable occurrence context only; do not rewrite legacy timestamps."""
    columns = (
        ("pm_diagnostic_snapshots", "source_recorded_at", "DATETIME(6) NULL"),
        ("pm_work_orders", "report_origin", "VARCHAR(32) NULL"),
        ("pm_work_orders", "event_started_at", "DATETIME(6) NULL"),
        ("pm_work_orders", "event_ended_at", "DATETIME(6) NULL"),
        ("pm_work_orders", "event_timezone", "VARCHAR(64) NULL"),
        ("pm_work_orders", "event_time_precision", "VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN'"),
        ("pm_maintenance_logs", "incident_context_json", "JSON NULL"),
    )
    for table, column, definition in columns:
        cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
    cur.execute("SHOW INDEX FROM pm_diagnostic_snapshots WHERE Key_name='idx_pm_diag_source_time_module'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE pm_diagnostic_snapshots ADD KEY idx_pm_diag_source_time_module (source_recorded_at, module_id)")


def run_schema_migrations(cur) -> None:
    # Normalize the retired workflow state before narrowing the ENUM.
    cur.execute("UPDATE pm_devices SET status = 'NORMAL' WHERE status = 'MONITORING'")
    cur.execute("SHOW INDEX FROM pm_diagnostic_snapshots WHERE Key_name = 'idx_pm_diag_time_module'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE pm_diagnostic_snapshots ADD KEY idx_pm_diag_time_module (recorded_at, module_id)")
    cur.execute(
        f"""
        ALTER TABLE pm_devices
        MODIFY status ENUM({DEVICE_STATUS_ENUM}) NOT NULL DEFAULT 'OFFLINE'
        """
    )
    for column, definition in (
        ("issue_key", "VARCHAR(160) NOT NULL DEFAULT 'diagnostic_alert'"),
        ("acknowledged_by", "BIGINT UNSIGNED NULL"),
        ("acknowledged_at", "DATETIME NULL"),
        ("suppressed_until", "DATETIME NULL"),
    ):
        cur.execute("SHOW COLUMNS FROM pm_alerts LIKE %s", (column,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE pm_alerts ADD COLUMN `{column}` {definition}")
    for index_name, columns in (
        ("idx_pm_alerts_issue_time", "device_id, module_id, issue_key, recorded_at"),
        ("idx_pm_alerts_suppression", "module_id, issue_key, suppressed_until"),
    ):
        cur.execute("SHOW INDEX FROM pm_alerts WHERE Key_name = %s", (index_name,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE pm_alerts ADD KEY `{index_name}` ({columns})")
    cur.execute(
        """
        SELECT 1
        FROM information_schema.REFERENTIAL_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = 'pm_alerts'
          AND CONSTRAINT_NAME = 'fk_pm_alerts_ack_user'
        """
    )
    if not cur.fetchone():
        cur.execute(
            """
            ALTER TABLE pm_alerts
            ADD CONSTRAINT fk_pm_alerts_ack_user
            FOREIGN KEY (acknowledged_by) REFERENCES pm_users(id)
            ON DELETE SET NULL
            """
        )
    for column, definition in (
        ("telemetry_source", "VARCHAR(40) NULL"),
        ("source_device_key", "VARCHAR(160) NULL"),
    ):
        cur.execute("SHOW COLUMNS FROM pm_modules LIKE %s", (column,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE pm_modules ADD COLUMN `{column}` {definition}")
    cur.execute("UPDATE pm_modules SET status = 'NORMAL' WHERE status = 'MONITORING'")
    cur.execute(
        f"""
        ALTER TABLE pm_modules
        MODIFY status ENUM({DEVICE_STATUS_ENUM}) NOT NULL DEFAULT 'OFFLINE'
        """
    )
    cur.execute("SHOW COLUMNS FROM pm_work_orders LIKE 'source_alert_id'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE pm_work_orders ADD COLUMN source_alert_id BIGINT UNSIGNED NULL")
    cur.execute("SHOW COLUMNS FROM pm_work_orders LIKE 'alert_recorded_at'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE pm_work_orders ADD COLUMN alert_recorded_at DATETIME NULL")
    migrate_incident_evidence(cur)
    cur.execute(
        "UPDATE pm_work_orders wo JOIN pm_alerts a ON a.id = wo.source_alert_id "
        "SET wo.alert_recorded_at = a.recorded_at WHERE wo.alert_recorded_at IS NULL"
    )
    for column, definition in (
        ("parts_json", "JSON NULL"),
        ("other_cost_baht", "DECIMAL(12,2) NOT NULL DEFAULT 0"),
    ):
        cur.execute("SHOW COLUMNS FROM pm_maintenance_logs LIKE %s", (column,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE pm_maintenance_logs ADD COLUMN `{column}` {definition}")
    cur.execute("SHOW INDEX FROM pm_work_orders WHERE Key_name = 'uq_pm_work_source_alert'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE pm_work_orders ADD UNIQUE KEY uq_pm_work_source_alert (source_alert_id)")
    cur.execute(
        "SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'pm_work_orders' "
        "AND CONSTRAINT_NAME = 'fk_pm_work_source_alert'"
    )
    if not cur.fetchone():
        cur.execute(
            "ALTER TABLE pm_work_orders ADD CONSTRAINT fk_pm_work_source_alert "
            "FOREIGN KEY (source_alert_id) REFERENCES pm_alerts(id) ON DELETE SET NULL"
        )


def seed_users() -> None:
    users = [
        (settings.admin_username, hash_password(settings.admin_password), "ADI Administrator", "admin"),
        (settings.user_username, hash_password(settings.user_password), "ADI Maintenance", "user"),
    ]
    execute_many(
        """
        INSERT INTO pm_users (username, password_hash, full_name, role, is_active)
        VALUES (%s, %s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE id = id
        """,
        users,
    )
