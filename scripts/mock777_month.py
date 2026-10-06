"""Isolated, reproducible eight-module Compressor integration fixture.

This script never writes to the configured source schemas.  ``prepare`` creates
three new local-only schemas and a 30-day synthetic MX777 history. ``stream``
appends one of twelve five-minute samples, without sleeping or backdating the
wall clock. All timestamps are Asia/Bangkok naive DATETIME, matching the local
test contract. Nothing here is an approved calibration or real fault label.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pymysql

from app.config import settings


SOURCE = "ht_mock777_month_source"
ANALYTICS = "ht_mock777_month_analytics"
DASHBOARD = "pm_mock777_month_dashboard"
SCHEMAS = (SOURCE, ANALYTICS, DASHBOARD)
FEATURES = ("Hp_1st", "Lp_1st", "Hp_2nd", "Lp_2nd", "Valve", "TempHi", "TempLo")
CONTROL = ("Status", "Busy", "SV")
SCALE = {"Hp_1st": 1.3, "Lp_1st": 0.7, "Hp_2nd": 1.5, "Lp_2nd": 0.7,
         "Valve": 1.2, "TempHi": 0.8, "TempLo": 0.7}


def connect(database: str | None = None):
    if settings.db_host not in {"localhost", "127.0.0.1"} or settings.telemetry_db_host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("MX777 fixture is restricted to localhost MySQL")
    return pymysql.connect(
        host=settings.db_host, port=settings.db_port, user=settings.db_user,
        password=settings.db_password, database=database, charset="utf8mb4",
        autocommit=False, cursorclass=pymysql.cursors.DictCursor,
    )


def reference_medians(cur) -> dict[int, dict[str, float]]:
    # Read only a qualified reference slice. MX057 M6 retains a realistic
    # ~190 psi CP2 baseline, which lets the injected high-side episode resemble
    # the observed MX080 pattern without copying incident rows.
    cur.execute(
        f"SELECT * FROM `{settings.compressor_schema}`.`{settings.compressor_table}` "
        "WHERE machine_number='057' AND Status='Run' AND Status_1='On' "
        "AND Busy_1='0' AND SV_1='Off' ORDER BY recorded_at LIMIT 500"
    )
    rows = cur.fetchall()
    if len(rows) < 200:
        raise RuntimeError("Qualified MX057 reference slice is too small")
    return {
        module: {
            feature: statistics.median(float(row[f"{feature}_{module}"])
                                       for row in rows if row[f"{feature}_{module}"] is not None)
            for feature in FEATURES
        }
        for module in range(1, 9)
    }


def make_row(at: datetime, minute_number: int, ref: dict[int, dict[str, float]],
             *, scenario: str = "history") -> tuple:
    rng = random.Random(777_000_000 + minute_number)
    values: list[object] = ["777", at, "Run"]
    day_index = minute_number // 1440
    minute_of_day = minute_number % 1440
    clock_minute = at.hour * 60 + at.minute
    for module in range(1, 9):
        current = {}
        for feature in FEATURES:
            base = ref[module][feature]
            daily = math.sin(2 * math.pi * minute_of_day / 1440 + module * 0.33)
            slow = math.sin(2 * math.pi * day_index / 7 + module * 0.41)
            noise = rng.gauss(0, 0.26)
            value = base + SCALE[feature] * (0.55 * daily + 0.40 * slow + noise)
            current[feature] = max(0.0, value) if feature == "Valve" else value

        # Historical scenarios are deliberately sparse enough not to dominate
        # the baseline and are outside the final three-day shadow holdout.
        if scenario == "history" and day_index < 27:
            if module == 2 and day_index == 7 and 10 <= clock_minute < 12:
                current["Hp_2nd"] += 42  # isolated spike
            if module == 3 and day_index == 12 and clock_minute < 90:
                current["Hp_1st"] += 5 * math.sin(clock_minute / 2.5)  # wave
            if module == 4 and day_index == 17 and clock_minute < 70:
                current["TempHi"] += 7  # step-like thermal excursion
            if module == 5 and day_index == 15 and clock_minute < 90:
                current["Valve"] += 24 + 10 * math.sin(clock_minute / 3)  # hunting
            if module == 6 and day_index == 20 and clock_minute < 90:
                current["Hp_2nd"] += 145  # MX080-like sustained high-side episode
                current["Lp_2nd"] += 3
            if module == 7 and day_index == 21 and clock_minute < 45:
                current["Lp_1st"] -= 8
            if module == 8 and day_index == 23 and clock_minute < 6:
                current["TempLo"] += 18  # short spike
        elif scenario == "stream":
            step = minute_number
            if module == 6 and step >= 4:
                current["Hp_2nd"] += 80 + 7 * min(step - 4, 7)
                current["TempHi"] += 3
            if module == 2 and step in (2, 3):
                current["Hp_2nd"] += 45
            if module == 5 and step >= 7:
                current["Valve"] += 20 + 7 * math.sin(step * 1.4)
            if module == 8 and step in (9, 10):
                current["TempLo"] += 13
        values.extend(round(current[feature], 3) for feature in FEATURES)
        values.extend(("On", "0", "Off"))
    return tuple(values)


def insert_rows(cur, rows: list[tuple]) -> None:
    columns = ["machine_number", "recorded_at", "Status"]
    for module in range(1, 9):
        columns.extend(f"{name}_{module}" for name in (*FEATURES, *CONTROL))
    quoted = ", ".join(f"`{name}`" for name in columns)
    placeholders = ", ".join("%s" for _ in columns)
    cur.executemany(
        f"INSERT INTO `{SOURCE}`.`ht9046mx_readings` ({quoted}) VALUES ({placeholders})",
        rows,
    )


def prepare() -> None:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME IN (%s,%s,%s)", SCHEMAS)
            existing = [row["SCHEMA_NAME"] for row in cur.fetchall()]
            if existing:
                raise RuntimeError(f"Refusing to replace existing fixture schemas: {existing}")
            for schema in SCHEMAS:
                cur.execute(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            for table in ("ht9046mx_readings", "compressor_health_scores"):
                cur.execute(f"CREATE TABLE `{SOURCE}`.`{table}` LIKE `{settings.compressor_schema}`.`{table}`")
            # Keep the Dashboard's configured Vacuum connector healthy, while
            # deliberately providing no Vacuum samples in this Compressor test.
            cur.execute(f"CREATE TABLE `{SOURCE}`.`vacuum_pump_readings` LIKE `{settings.vacuum_schema}`.`{settings.vacuum_table}`")
            cur.execute("SHOW TABLES FROM `ht9046mx_analytics`")
            for row in cur.fetchall():
                table = next(iter(row.values()))
                cur.execute(f"CREATE TABLE `{ANALYTICS}`.`{table}` LIKE `ht9046mx_analytics`.`{table}`")
            ref = reference_medians(cur)
            end = datetime.now(ZoneInfo("Asia/Bangkok")).replace(second=0, microsecond=0) - timedelta(minutes=60)
            start = end - timedelta(days=30) + timedelta(minutes=1)
            rows: list[tuple] = []
            inserted = 0
            for index in range(30 * 1440):
                at = start + timedelta(minutes=index)
                if at < end - timedelta(days=3) and not (at.hour < 2 or at.hour >= 22):
                    continue
                rows.append(make_row(at, index, ref))
                if len(rows) >= 300:
                    insert_rows(cur, rows)
                    inserted += len(rows)
                    rows.clear()
            if rows:
                insert_rows(cur, rows)
                inserted += len(rows)
            cur.execute(f"CREATE TABLE `{SOURCE}`.`mock777_manifest` (fixture_key VARCHAR(32) PRIMARY KEY, history_start DATETIME NOT NULL, history_end DATETIME NOT NULL, stream_start DATETIME NULL, stream_step INT NOT NULL, reference_note VARCHAR(255) NOT NULL)")
            cur.execute(f"INSERT INTO `{SOURCE}`.`mock777_manifest` (fixture_key,history_start,history_end,stream_step,reference_note) VALUES ('month_v1',%s,%s,0,%s)",
                        (start, end, "Synthetic MX777; qualified MX057 medians; 8 modules; 30-day span; no real fault labels"))
        conn.commit()
        print(json.dumps({"schemas": SCHEMAS, "machine": "777", "history_rows": inserted,
                          "history_start": start.isoformat(), "history_end": end.isoformat(),
                          "synthetic_only": True}, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def stream() -> None:
    conn = connect(SOURCE)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT history_end,stream_start,stream_step FROM mock777_manifest WHERE fixture_key='month_v1' FOR UPDATE")
            manifest = cur.fetchone()
            if not manifest:
                raise RuntimeError("Run prepare first")
            step = int(manifest["stream_step"])
            if step >= 12:
                raise RuntimeError("All twelve simulated five-minute arrivals have been inserted")
            anchor = manifest["stream_start"]
            if anchor is None:
                now = datetime.now(ZoneInfo("Asia/Bangkok")).replace(tzinfo=None, second=0, microsecond=0)
                anchor = max(manifest["history_end"], now - timedelta(minutes=60))
                cur.execute("UPDATE mock777_manifest SET stream_start=%s WHERE fixture_key='month_v1'", (anchor,))
            at = anchor + timedelta(minutes=5 * (step + 1))
            # The 60-minute stream ends near wall-clock now; future timestamps
            # must remain test-only and are never sent to the live source.
            ref = reference_medians(cur)
            insert_rows(cur, [make_row(at, step, ref, scenario="stream")])
            cur.execute("UPDATE mock777_manifest SET stream_step=%s WHERE fixture_key='month_v1'", (step + 1,))
        conn.commit()
        print(json.dumps({"step": step + 1, "recorded_at": at.isoformat(), "scenario": "stream", "synthetic_only": True}))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fill_history() -> None:
    """Append the missing daytime minutes in the first 27 days.

    The first fixture deliberately had sparse historical coverage. This
    correction makes calibration and shadow use comparable 24-hour coverage
    without changing or deleting the original synthetic rows.
    """
    conn = connect(SOURCE)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT history_start,history_end FROM mock777_manifest WHERE fixture_key='month_v1'")
            manifest = cur.fetchone()
            if not manifest:
                raise RuntimeError("Run prepare first")
            start, end = manifest["history_start"], manifest["history_end"]
            ref = reference_medians(cur)
            rows: list[tuple] = []
            inserted = 0
            for index in range(30 * 1440):
                at = start + timedelta(minutes=index)
                if at >= end - timedelta(days=3) or at.hour < 2 or at.hour >= 22:
                    continue
                rows.append(make_row(at, index, ref))
                if len(rows) >= 300:
                    insert_rows(cur, rows)
                    inserted += len(rows)
                    rows.clear()
            if rows:
                insert_rows(cur, rows)
                inserted += len(rows)
            cur.execute("UPDATE mock777_manifest SET reference_note=%s WHERE fixture_key='month_v1'",
                        ("Synthetic MX777; qualified MX057 medians; 8 modules; full minute coverage over 30 days; no real fault labels",))
        conn.commit()
        print(json.dumps({"filled_rows": inserted, "synthetic_only": True}))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "fill_history", "stream"))
    arguments = parser.parse_args()
    {"prepare": prepare, "fill_history": fill_history, "stream": stream}[arguments.action]()
