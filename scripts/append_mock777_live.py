"""Append fresh synthetic M1/M2 readings to the isolated local mock source."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pymysql

from app.config import settings


def main() -> None:
    if settings.db_host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Mock publisher requires local MySQL")
    conn = pymysql.connect(host=settings.db_host, port=settings.db_port,
                           user=settings.db_user, password=settings.db_password,
                           database="ht_mock777_source", autocommit=False)
    try:
        now = datetime.now(ZoneInfo("Asia/Bangkok")).replace(tzinfo=None, second=0, microsecond=0)
        columns = ["machine_number", "recorded_at", "Status"]
        for module in (1, 2):
            columns.extend(f"{name}_{module}" for name in
                           ("Hp_1st", "Lp_1st", "Hp_2nd", "Lp_2nd", "Valve", "TempHi", "TempLo", "Status", "Busy", "SV"))
        quoted = ", ".join(f"`{column}`" for column in columns)
        placeholders = ", ".join("%s" for _ in columns)
        inserted = 0
        with conn.cursor() as cur:
            for minute in range(20):
                recorded_at = now - timedelta(minutes=19 - minute)
                cur.execute("SELECT 1 FROM ht9046mx_readings WHERE machine_number = %s AND recorded_at = %s LIMIT 1",
                            ("777", recorded_at))
                if cur.fetchone():
                    continue
                drift = math.sin((minute + 2880) / 31.0) * 0.7
                row = (
                    "777", recorded_at, "Run",
                    152.0 + drift, 31.0 + drift * 0.2, 210.0 + drift, 39.0 + drift * 0.2,
                    46.0 + drift * 0.1, 76.0 + drift * 0.2, -24.0 + drift * 0.2, "On", "0", "Off",
                    158.0 + drift, 33.0 + drift * 0.2, 216.0 + drift, 41.0 + drift * 0.2,
                    48.0 + drift * 0.1, 78.0 + drift * 0.2, -22.0 + drift * 0.2, "On", "0", "Off",
                )
                cur.execute(f"INSERT INTO ht9046mx_readings ({quoted}) VALUES ({placeholders})", row)
                inserted += 1
        conn.commit()
        print({"machine": "HT9046MX-777", "new_rows": inserted, "latest_at": str(now), "mock_only": True})
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
