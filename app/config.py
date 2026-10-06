from __future__ import annotations

import os
import re
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def require_safe_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"{label} must contain only letters, numbers, and underscores")
    return value


def resolve_secret_key(raw_key: str | None, app_env: str) -> str:
    key = (raw_key or "").strip()
    if len(key) >= 32 and key != "change-this-secret-before-production":
        return key
    if app_env.lower() == "production":
        raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters")
    # Local development must never sign authentication tokens with a known key.
    # This key is process-local; tokens intentionally expire when the app restarts.
    return secrets.token_urlsafe(48)


def validate_production_passwords(app_env: str, admin_password: str, user_password: str) -> None:
    if app_env.lower() != "production":
        return
    if (
        len(admin_password) < 12
        or len(user_password) < 12
        or admin_password in {"ADIIOT", user_password}
        or user_password == "ADIMNT"
    ):
        raise ValueError("Production requires distinct, non-default ADMIN_PASSWORD and USER_PASSWORD of at least 12 characters")


class Settings:
    app_name = os.getenv("APP_NAME", "ADI HT9046 Predictive Maintenance")
    app_host = os.getenv("APP_HOST", "0.0.0.0")
    app_port = int(os.getenv("PORT", os.getenv("APP_PORT", "5001")))
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    secret_key = resolve_secret_key(os.getenv("SECRET_KEY"), app_env)

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "3306"))
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = require_safe_identifier(os.getenv("DB_NAME", "predictive_maintenance"), "DB_NAME")
    db_charset = os.getenv("DB_CHARSET", "utf8mb4")

    # The production dashboard reads ESP32 telemetry from MySQL. MQTT remains
    # opt-in only for an isolated legacy/demo environment.
    mqtt_enabled = env_bool("MQTT_ENABLED", False)
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME", "")
    mqtt_password = os.getenv("MQTT_PASSWORD", "")
    mqtt_topic = os.getenv("MQTT_TOPIC", "adi/#")
    mqtt_legacy_topic = os.getenv("MQTT_LEGACY_TOPIC", "esp32/#")
    mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "adi-fastapi-ingestor")

    admin_username = os.getenv("ADMIN_USERNAME", "ADIadmin")
    admin_password = os.getenv("ADMIN_PASSWORD", "ADIIOT")
    user_username = os.getenv("USER_USERNAME", "ADImaintenance")
    user_password = os.getenv("USER_PASSWORD", "ADIMNT")

    # Dashboard metadata still uses DB_* above. TELEMETRY_DB_* is intentionally
    # separate and must be a read-only account on the source server.
    telemetry_enabled = env_bool("TELEMETRY_ENABLED", True)
    telemetry_db_host = os.getenv("TELEMETRY_DB_HOST", "10.195.17.73")
    telemetry_db_port = int(os.getenv("TELEMETRY_DB_PORT", "3306"))
    # Keep separate read-only accounts because each source schema can have its
    # own least-privilege database user. TELEMETRY_DB_* remains a backward-
    # compatible shared fallback for installations that use one account.
    telemetry_db_user = os.getenv("TELEMETRY_DB_USER", "")
    telemetry_db_password = os.getenv("TELEMETRY_DB_PASSWORD", "")
    vacuum_db_user = os.getenv("VACUUM_DB_USER", telemetry_db_user)
    vacuum_db_password = os.getenv("VACUUM_DB_PASSWORD", telemetry_db_password)
    compressor_db_user = os.getenv("COMPRESSOR_DB_USER", telemetry_db_user)
    compressor_db_password = os.getenv("COMPRESSOR_DB_PASSWORD", telemetry_db_password)
    telemetry_db_charset = os.getenv("TELEMETRY_DB_CHARSET", "utf8mb4")
    telemetry_poll_interval_seconds = max(2, int(os.getenv("TELEMETRY_POLL_INTERVAL_SECONDS", "5")))
    telemetry_connect_timeout_seconds = max(1, int(os.getenv("TELEMETRY_CONNECT_TIMEOUT_SECONDS", "10")))
    telemetry_read_timeout_seconds = max(1, int(os.getenv("TELEMETRY_READ_TIMEOUT_SECONDS", "30")))

    vacuum_schema = require_safe_identifier(os.getenv("VACUUM_SCHEMA", "vacuum_pump_db"), "VACUUM_SCHEMA")
    vacuum_table = require_safe_identifier(os.getenv("VACUUM_TABLE", "vacuum_pump_readings"), "VACUUM_TABLE")
    vacuum_device_column = require_safe_identifier(
        os.getenv("VACUUM_DEVICE_COLUMN", "devices_id"), "VACUUM_DEVICE_COLUMN"
    )
    compressor_schema = require_safe_identifier(os.getenv("COMPRESSOR_SCHEMA", "ht9046mx_iot"), "COMPRESSOR_SCHEMA")
    compressor_table = require_safe_identifier(os.getenv("COMPRESSOR_TABLE", "ht9046mx_readings"), "COMPRESSOR_TABLE")
    compressor_machine_column = require_safe_identifier(
        os.getenv("COMPRESSOR_MACHINE_COLUMN", "machine_number"), "COMPRESSOR_MACHINE_COLUMN"
    )
    compressor_timestamp_column = require_safe_identifier(
        os.getenv("COMPRESSOR_TIMESTAMP_COLUMN", "recorded_at"), "COMPRESSOR_TIMESTAMP_COLUMN"
    )
    compressor_sensor_scale = os.getenv("COMPRESSOR_SENSOR_SCALE", "1").strip().lower()
    if compressor_sensor_scale not in {"1", "0.1"}:
        raise ValueError("COMPRESSOR_SENSOR_SCALE must be an explicit 1 or 0.1")

    # Optional read-only output contract for the Compressor ML service.  The
    # dashboard never writes this table and shows Awaiting ML Score until the
    # producer/table is enabled by the operator.
    compressor_health_enabled = env_bool("COMPRESSOR_HEALTH_ENABLED", False)
    compressor_health_schema = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_SCHEMA", compressor_schema), "COMPRESSOR_HEALTH_SCHEMA"
    )
    compressor_health_table = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_TABLE", "compressor_health_scores"), "COMPRESSOR_HEALTH_TABLE"
    )
    compressor_health_machine_column = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_MACHINE_COLUMN", "machine_number"), "COMPRESSOR_HEALTH_MACHINE_COLUMN"
    )
    compressor_health_module_column = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_MODULE_COLUMN", "module_id"), "COMPRESSOR_HEALTH_MODULE_COLUMN"
    )
    compressor_health_timestamp_column = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_TIMESTAMP_COLUMN", "recorded_at"), "COMPRESSOR_HEALTH_TIMESTAMP_COLUMN"
    )
    compressor_health_score_column = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_SCORE_COLUMN", "health_score"), "COMPRESSOR_HEALTH_SCORE_COLUMN"
    )
    compressor_health_condition_column = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_CONDITION_COLUMN", "condition"), "COMPRESSOR_HEALTH_CONDITION_COLUMN"
    )
    compressor_health_model_column = require_safe_identifier(
        os.getenv("COMPRESSOR_HEALTH_MODEL_COLUMN", "model_version"), "COMPRESSOR_HEALTH_MODEL_COLUMN"
    )

    app_timezone = os.getenv("APP_TIMEZONE", "Asia/Bangkok")

    seed_demo_data = env_bool("SEED_DEMO_DATA", False)

    @property
    def allowed_origins(self) -> list[str]:
        raw = os.getenv("ALLOWED_ORIGINS", "").strip()
        if raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return ["http://localhost:5001", "http://127.0.0.1:5001"]


settings = Settings()
validate_production_passwords(settings.app_env, settings.admin_password, settings.user_password)

import logging
_config_log = logging.getLogger("adi.config")
if not os.getenv("SECRET_KEY", "").strip() or len(os.getenv("SECRET_KEY", "").strip()) < 32 or os.getenv("SECRET_KEY", "").strip() == "change-this-secret-before-production":
    _config_log.warning(
        "SECRET_KEY is unset or weak; using an ephemeral development key. "
        "Set a unique 32+ character SECRET_KEY and APP_ENV=production before deployment."
    )
