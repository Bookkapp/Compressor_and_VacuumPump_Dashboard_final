"""Read-only source/service load probe; records timings, never sensor values or secrets."""
import argparse
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.encoders import jsonable_encoder
from app.db import fetch_all
from app.services import get_history, get_metric_history
from app.analytics import correlation, relationship

parser = argparse.ArgumentParser()
parser.add_argument("--tabs", type=int, default=6)
parser.add_argument("--case", choices=["analytics", "detail"], default="analytics")
parser.add_argument("--output", type=Path)
parser.add_argument("--machines", default="")
parser.add_argument("--compact", action="store_true")
args = parser.parse_args()
modules = fetch_all("SELECT m.id, m.device_id, d.machine_code FROM pm_modules m JOIN pm_devices d ON d.id=m.device_id WHERE m.telemetry_source = 'compressor' ORDER BY m.device_id, m.id")
if args.machines:
    selected = set(args.machines.split(","))
    modules = [row for row in modules if row["machine_code"] in selected]
devices = list(dict.fromkeys(row["device_id"] for row in modules))[:args.tabs]
tasks = []
for tab, device in enumerate(devices):
    for module in [row for row in modules if row["device_id"] == device][:(4 if args.case == "analytics" else 1)]:
        tasks.append((tab, "history", device, module["id"]))
        if args.case == "detail":
            tasks.extend((tab, endpoint, device, module["id"]) for endpoint in ["metrics", "correlation", "relationship"])
started = time.perf_counter()

def probe(task):
    tab, endpoint, device, module = task
    start = time.perf_counter()
    try:
        if endpoint == "history":
            if args.compact:
                from app.main import devices_history
                data = devices_history(device, module, 2000, signals="hp_1st,lp_1st,hp_2nd,lp_2nd", token={})
            else:
                data = get_history(device, module, 2000)
        elif endpoint == "metrics":
            data = get_metric_history(device, module, 3000)
        elif endpoint == "correlation":
            data = correlation(device, module, ["hp_1st", "lp_1st", "hp_2nd", "lp_2nd", "temperature_hi", "temperature_lo", "valve"])
        else:
            data = relationship(device, module, "valve", "lp_2nd")
        ready = time.perf_counter()
        body = json.dumps(jsonable_encoder(data), separators=(",", ":"))
        return {"tab": tab+1, "endpoint": endpoint, "ms": round((ready-start)*1000), "encode_ms": round((time.perf_counter()-ready)*1000), "rows": len(data) if isinstance(data, list) else data["samples"], "bytes": len(body), "ok": True}
    except Exception as exc:
        return {"tab": tab+1, "endpoint": endpoint, "ms": round((time.perf_counter()-start)*1000), "ok": False, "error": type(exc).__name__}

with ThreadPoolExecutor(max_workers=min(32, len(tasks))) as pool:
    results = list(pool.map(probe, tasks))
values = sorted(row["ms"] for row in results)
report = {"case": args.case, "tabs": len(devices), "requests": len(tasks), "wall_ms": round((time.perf_counter()-started)*1000), "median_ms": round(statistics.median(values)), "p95_ms": values[math.ceil(len(values)*.95)-1], "max_ms": max(values), "errors": sum(not row["ok"] for row in results), "results": results}
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "results"}))
