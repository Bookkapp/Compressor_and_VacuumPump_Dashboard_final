"""Copy only synthetic MX777 fixture rows into the localhost rehearsal source.

The project owner explicitly requested the normal local schemas/ports for this
integration test. This script refuses remote MySQL, other machine numbers, and
schema drift. It is append-only and never deletes or updates telemetry.
"""

from __future__ import annotations

import json

import pymysql

from app.config import settings


def main() -> None:
    if settings.db_host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Refusing to copy mock telemetry to a non-local MySQL host")
    if settings.telemetry_db_host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Configured telemetry host is not local")
    if settings.compressor_schema != "ht9046mx_iot" or settings.compressor_table != "ht9046mx_readings":
        raise RuntimeError("Unexpected rehearsal source schema/table")
    conn = pymysql.connect(host=settings.db_host, port=settings.db_port,
                           user=settings.db_user, password=settings.db_password,
                           database=settings.db_name, autocommit=False,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT history_start, history_end, stream_step FROM ht_mock777_month_source.mock777_manifest WHERE fixture_key='month_v1'")
            manifest = cur.fetchone()
            if not manifest:
                raise RuntimeError("The synthetic fixture manifest is missing")
            columns = {}
            cur.execute("""SELECT TABLE_SCHEMA,COLUMN_NAME FROM information_schema.COLUMNS
                           WHERE TABLE_NAME='ht9046mx_readings'
                             AND TABLE_SCHEMA IN ('ht_mock777_month_source','ht9046mx_iot')
                           ORDER BY ORDINAL_POSITION""")
            for row in cur.fetchall():
                columns.setdefault(row["TABLE_SCHEMA"], []).append(row["COLUMN_NAME"])
            source_cols = [column for column in columns.get("ht_mock777_month_source", []) if column != "id"]
            destination_cols = [column for column in columns.get("ht9046mx_iot", []) if column != "id"]
            if not source_cols or source_cols != destination_cols:
                raise RuntimeError("Source and destination columns do not match")
            quoted = ", ".join(f"`{column}`" for column in source_cols)
            cur.execute(f"""INSERT INTO ht9046mx_iot.ht9046mx_readings ({quoted})
                            SELECT {', '.join('s.`' + column + '`' for column in source_cols)}
                            FROM ht_mock777_month_source.ht9046mx_readings s
                            WHERE s.machine_number='777' AND NOT EXISTS (
                                SELECT 1 FROM ht9046mx_iot.ht9046mx_readings d
                                WHERE d.machine_number=s.machine_number AND d.recorded_at=s.recorded_at
                            ) ORDER BY s.recorded_at""")
            copied = cur.rowcount
            cur.execute("SELECT COUNT(*) AS n, MAX(recorded_at) AS latest FROM ht9046mx_iot.ht9046mx_readings WHERE machine_number='777'")
            after = cur.fetchone()
        conn.commit()
        print(json.dumps({"local_only": True, "machine_number": "777", "copied": copied,
                          "total_in_rehearsal_source": after["n"], "latest": str(after["latest"]),
                          "fixture_stream_step": manifest["stream_step"]}))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
