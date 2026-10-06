"""Fast synchronous import of parquet files for all 19 machines."""
import os
import sys
import glob
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timedelta
import random

import pymysql
import pyarrow.parquet as pq
import pandas as pd

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


def main():
    if not PARQUET_ROOT_VALUE or not DB_USER or not DB_PASSWORD:
        raise RuntimeError(
            "Set IMPORT_PARQUET_ROOT, IMPORT_DB_USER and IMPORT_DB_PASSWORD "
            "in the local environment before running this import helper."
        )
    machine_dirs = sorted([
        d for d in PARQUET_ROOT.iterdir()
        if d.is_dir() and d.name.startswith("machine=")
    ])
    print(f"Found {len(machine_dirs)} machines", flush=True)

    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        charset="utf8mb4", autocommit=True,
    )
    with conn.cursor() as cur:
        cur.execute("USE ht9046mx_iot;")
        cur.execute("TRUNCATE TABLE ht9046mx_readings;")

        imported_machines = []
        for md in machine_dirs:
            machine_num = md.name.split("=")[1]
            # Look for month=09/day=01/part-00000.parquet or any first parquet file
            pfiles = list(md.glob("year=*/month=*/day=*/part-*.parquet"))
            if not pfiles:
                pfiles = list(md.glob("**/*.parquet"))
            if not pfiles:
                print(f"No parquet file for {machine_num}", flush=True)
                continue

            # Take the newest file (last in sorted)
            pf = sorted(pfiles)[-1]
            try:
                table = pq.read_table(pf)
                df = table.to_pandas().sort_values("recorded_at", ascending=False).head(60)
            except Exception as e:
                print(f"Error reading {pf}: {e}", flush=True)
                continue

            rows = []
            for _, r in df.iterrows():
                row_vals = []
                for col in SENSOR_COLS:
                    val = r.get(col)
                    if pd.isna(val) if isinstance(val, float) else val is None:
                        row_vals.append(None)
                    elif isinstance(val, Decimal):
                        row_vals.append(float(val))
                    else:
                        row_vals.append(str(val) if "Status" in col or "Busy" in col or "SV" in col else val)
                row_vals[0] = str(machine_num)
                rows.append(tuple(row_vals))

            if rows:
                col_names = ", ".join([f"`{c}`" for c in SENSOR_COLS])
                placeholders = ", ".join(["%s"] * len(SENSOR_COLS))
                sql = f"INSERT INTO ht9046mx_readings ({col_names}) VALUES ({placeholders})"
                cur.executemany(sql, rows)
                imported_machines.append(machine_num)
                print(f"Machine {machine_num}: {len(rows)} rows inserted", flush=True)

        # Seed Vacuum pumps
        cur.execute("USE vacuum_pump_db;")
        cur.execute("TRUNCATE TABLE vacuum_pump_readings;")
        now = datetime.now()
        v_rows = []
        for m in imported_machines:
            device_id = f"VP{m}"
            for i in range(60):
                stamp = now - timedelta(minutes=59 - i)
                temp = round(42.0 + random.random() * 8, 2)
                ax = round(0.02 + random.random() * 0.08, 4)
                ay = round(0.01 + random.random() * 0.06, 4)
                az = round(9.75 + random.random() * 0.15, 4)
                vib = round(0.3 + random.random() * 0.4, 4)
                current = round(2.5 + random.random() * 1.5, 3)
                v_rows.append((device_id, stamp, temp, ax, ay, az, vib, current))

        cur.executemany(
            """
            INSERT INTO vacuum_pump_readings
            (devices_id, recorded_at, temperature, accel_x, accel_y, accel_z, vibration, current_amp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            v_rows
        )
        print(f"Vacuum pumps seeded: {len(imported_machines)} machines, {len(v_rows)} rows", flush=True)

    conn.close()
    print("ALL DONE!", flush=True)

if __name__ == "__main__":
    main()
