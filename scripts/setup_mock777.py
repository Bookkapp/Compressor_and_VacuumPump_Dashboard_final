"""Create isolated local-only HT9046MX-777 integration fixtures.

Never writes to the configured telemetry source or production schemas. Run once;
existing mock schemas are left untouched for inspection instead of overwritten.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pymysql

from app.config import settings


SOURCE_SCHEMA = "ht_mock777_source"
ANALYTICS_SCHEMA = "ht_mock777_analytics"
DASHBOARD_SCHEMA = "pm_mock777_dashboard"
MOCK_SCHEMAS = (SOURCE_SCHEMA, ANALYTICS_SCHEMA, DASHBOARD_SCHEMA)


def main() -> None:
    if settings.db_host not in {"localhost", "127.0.0.1"} or settings.telemetry_db_host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Mock setup is permitted only with local MySQL hosts")
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME IN (%s,%s,%s)",
                MOCK_SCHEMAS,
            )
            existing = [row[0] for row in cur.fetchall()]
            if existing:
                raise RuntimeError(f"Refusing to overwrite existing mock schemas: {existing}")
            for schema in MOCK_SCHEMAS:
                cur.execute(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur.execute(
                f"CREATE TABLE `{SOURCE_SCHEMA}`.`ht9046mx_readings` LIKE "
                f"`{settings.compressor_schema}`.`{settings.compressor_table}`"
            )
            cur.execute(
                f"CREATE TABLE `{SOURCE_SCHEMA}`.`compressor_health_scores` LIKE "
                f"`{settings.compressor_health_schema}`.`{settings.compressor_health_table}`"
            )
            cur.execute(
                f"CREATE TABLE `{SOURCE_SCHEMA}`.`vacuum_pump_readings` LIKE "
                f"`{settings.vacuum_schema}`.`{settings.vacuum_table}`"
            )
            cur.execute("SHOW TABLES FROM `ht9046mx_analytics`")
            analytics_tables = [row[0] for row in cur.fetchall()]
            if not analytics_tables:
                raise RuntimeError("Local analytics schema has no tables to clone")
            for table in analytics_tables:
                cur.execute(f"CREATE TABLE `{ANALYTICS_SCHEMA}`.`{table}` LIKE `ht9046mx_analytics`.`{table}`")

            latest = datetime.now(ZoneInfo("Asia/Bangkok")).replace(tzinfo=None, second=0, microsecond=0)
            rows = []
            for day in range(12):
                for minute in range(240):
                    recorded_at = latest - timedelta(days=11 - day, minutes=239 - minute)
                    phase = (day * 240 + minute) / 31.0
                    drift = math.sin(phase) * 0.7
                    rows.append((
                        "777", recorded_at, "Run",
                        152.0 + drift, 31.0 + drift * 0.2, 210.0 + drift, 39.0 + drift * 0.2,
                        46.0 + drift * 0.1, 76.0 + drift * 0.2, -24.0 + drift * 0.2, "On", "0", "Off",
                        158.0 + drift, 33.0 + drift * 0.2, 216.0 + drift, 41.0 + drift * 0.2,
                        48.0 + drift * 0.1, 78.0 + drift * 0.2, -22.0 + drift * 0.2, "On", "0", "Off",
                    ))
            columns = ["machine_number", "recorded_at", "Status"]
            for module in (1, 2):
                columns.extend(f"{name}_{module}" for name in
                               ("Hp_1st", "Lp_1st", "Hp_2nd", "Lp_2nd", "Valve", "TempHi", "TempLo", "Status", "Busy", "SV"))
            quoted = ", ".join(f"`{column}`" for column in columns)
            placeholders = ", ".join("%s" for _ in columns)
            cur.executemany(
                f"INSERT INTO `{SOURCE_SCHEMA}`.`ht9046mx_readings` ({quoted}) VALUES ({placeholders})",
                rows,
            )
        conn.commit()
        print({"mock_machine": "HT9046MX-777", "schemas": MOCK_SCHEMAS,
               "source_rows": len(rows), "first_at": str(rows[0][1]), "last_at": str(rows[-1][1]),
               "modules": ["M1", "M2"], "synthetic_only": True})
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
