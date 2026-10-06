"""Import real Compressor parquet data and matching Vacuum Pump mock data.

Reads latest parquet files from HT9046MX folders on Desktop,
takes the latest rows, and seeds both Compressor (ht9046mx_iot)
and Vacuum Pump (vacuum_pump_db) so handlers have both modules.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timedelta
import random

import pymysql
from pymysql.cursors import DictCursor

try:
    import pyarrow.parquet as pq
    import pandas as pd
except ImportError:
    print("pip install pyarrow pandas")
    sys.exit(1)

PARQUET_ROOT_VALUE = os.environ.get("IMPORT_PARQUET_ROOT", "")
PARQUET_ROOT = Path(PARQUET_ROOT_VALUE) if PARQUET_ROOT_VALUE else Path("__NOT_CONFIGURED__")

DB_HOST = os.environ.get("IMPORT_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("IMPORT_DB_PORT", "3306"))
DB_USER = os.environ.get("IMPORT_DB_USER", "")
DB_PASSWORD = os.environ.get("IMPORT_DB_PASSWORD", "")

SENSOR_COLS = [
    "machine_number", "recorded_at", "Status",
]
for m in range(1, 9):
    SENSOR_COLS.extend([
        f"Hp_1st_{m}", f"Lp_1st_{m}", f"Hp_2nd_{m}", f"Lp_2nd_{m}",
        f"Valve_{m}", f"TempHi_{m}", f"TempLo_{m}",
        f"Status_{m}", f"Busy_{m}", f"SV_{m}",
    ])

ROWS_PER_MACHINE = 100


def decimal_to_float(val):
    if isinstance(val, Decimal):
        return float(val)
    return val


def import_compressors(cursor, machine_dirs):
    total = 0
    for md in machine_dirs:
        machine_num = md.name.split("=")[1]  # e.g. "017"
        parquet_files = sorted(md.rglob("*.parquet"))
        if not parquet_files:
            continue

        # Only read the latest 1 or 2 files to be lightning fast
        selected_files = parquet_files[-2:]
        frames = []
        for pf in selected_files:
            try:
                t = pq.read_table(pf)
                frames.append(t.to_pandas())
            except Exception as e:
                print(f"  Skipping {pf}: {e}")
        if not frames:
            continue

        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values("recorded_at", ascending=False).head(ROWS_PER_MACHINE)

        cursor.execute("USE ht9046mx_iot;")
        cursor.execute("DELETE FROM ht9046mx_readings WHERE machine_number = %s", (machine_num,))

        for _, row in df.iterrows():
            values = {}
            for col in SENSOR_COLS:
                val = row.get(col)
                if pd.isna(val) if isinstance(val, float) else val is None:
                    values[col] = None
                else:
                    values[col] = decimal_to_float(val)
            values["machine_number"] = str(machine_num)

            cols = list(values.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            col_names = ", ".join([f"`{c}`" for c in cols])
            cursor.execute(
                f"INSERT INTO ht9046mx_readings ({col_names}) VALUES ({placeholders})",
                tuple(values[c] for c in cols),
            )
            total += 1
        print(f"  Compressor machine {machine_num}: {len(df)} rows")
    return total


def seed_vacuum_pumps(cursor, machine_numbers):
    """Seed Vacuum Pump readings for matching machines (e.g. 017, 022, 024, etc.)."""
    cursor.execute("USE vacuum_pump_db;")
    cursor.execute("TRUNCATE TABLE vacuum_pump_readings;")
    now = datetime.now()
    count = 0
    # Seed matching vacuum pumps for machines
    for m in machine_numbers:
        device_id = f"VP{m}"  # e.g. VP017, VP022, VP001
        for i in range(60):
            stamp = now - timedelta(minutes=59 - i)
            temp = round(42.0 + random.random() * 8, 2)
            vib = round(0.3 + random.random() * 0.4, 4)
            current = round(2.5 + random.random() * 1.5, 3)
            ax = round(0.02 + random.random() * 0.08, 4)
            ay = round(0.01 + random.random() * 0.06, 4)
            az = round(9.75 + random.random() * 0.15, 4)
            cursor.execute(
                """
                INSERT INTO vacuum_pump_readings
                (devices_id, recorded_at, temperature, accel_x, accel_y, accel_z, vibration, current_amp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (device_id, stamp, temp, ax, ay, az, vib, current),
            )
            count += 1
    print(f"  Vacuum pump seeded: {len(machine_numbers)} machines, {count} total rows")


def main():
    if not PARQUET_ROOT_VALUE or not DB_USER or not DB_PASSWORD:
        raise RuntimeError(
            "Set IMPORT_PARQUET_ROOT, IMPORT_DB_USER and IMPORT_DB_PASSWORD "
            "in the local environment before running this import helper."
        )
    if not PARQUET_ROOT.exists():
        print(f"Parquet root not found: {PARQUET_ROOT}")
        sys.exit(1)

    machine_dirs = sorted([
        d for d in PARQUET_ROOT.iterdir()
        if d.is_dir() and d.name.startswith("machine=")
    ])
    print(f"Found {len(machine_dirs)} compressor machines")

    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        charset="utf8mb4", cursorclass=DictCursor, autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            comp_count = import_compressors(cur, machine_dirs)
            machine_nums = [d.name.split("=")[1] for d in machine_dirs]
            seed_vacuum_pumps(cur, machine_nums)
            conn.commit()
        print(f"\nSuccessfully imported {comp_count} compressor rows & synchronized vacuum pumps!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
