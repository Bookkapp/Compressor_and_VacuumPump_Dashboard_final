"""Bounded, read-only local multi-tab API simulation.

Example: python -m scripts.mock_multi_tab_read --tabs 8 --rounds 2
Never targets a non-loopback server and never writes application data.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import json
from statistics import mean
from time import perf_counter
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.config import settings


PATHS = (
    "/api/db/status", "/api/summary", "/api/devices",
    "/api/work-orders", "/api/maintenance-logs", "/api/alerts?limit=500",
)


def request(base, path, token=None, body=None, accept_gzip=False):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if accept_gzip:
        headers["Accept-Encoding"] = "gzip"
    if body is not None:
        headers["Content-Type"] = "application/json"
    started = perf_counter()
    req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urlopen(req, timeout=15) as response:
        wire = response.read()
        payload = gzip.decompress(wire) if response.headers.get("Content-Encoding") == "gzip" else wire
        return path, response.status, (perf_counter() - started) * 1000, len(wire), payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5001")
    parser.add_argument("--tabs", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--charts", action="store_true", help="Include one machine/module history and metrics pair per tab")
    parser.add_argument("--gzip", action="store_true", help="Request gzip like a browser")
    args = parser.parse_args()
    host = urlparse(args.url).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("Only loopback URLs are allowed")
    if not 1 <= args.tabs <= 20 or not 1 <= args.rounds <= 10:
        parser.error("tabs must be 1–20 and rounds 1–10")
    base = args.url.rstrip("/")
    _, _, _, _, login = request(base, "/api/auth/login", body={
        "username": settings.admin_username, "password": settings.admin_password,
    }, accept_gzip=args.gzip)
    token = json.loads(login)["token"]
    paths = list(PATHS)
    if args.charts:
        _, _, _, _, devices_json = request(base, "/api/devices", token, accept_gzip=args.gzip)
        devices = json.loads(devices_json)
        candidates = [(device["id"], module["id"], module.get("telemetry_source"))
                      for device in devices for module in device.get("modules", [])]
        choice = next(((device_id, module_id) for device_id, module_id, source in candidates if source == "compressor"), None)
        choice = choice or next(((device_id, module_id) for device_id, module_id, _ in candidates), None)
        if not choice:
            parser.error("No machine/module exists for chart simulation")
        device_id, module_id = choice
        paths.extend((
            f"/api/devices/{device_id}/history?module_id={module_id}&limit=2000",
            f"/api/devices/{device_id}/metrics?module_id={module_id}&limit=3000",
        ))
    samples = []
    errors = []
    with ThreadPoolExecutor(max_workers=min(args.tabs * len(paths), 40)) as pool:
        for _ in range(args.rounds):
            futures = [pool.submit(request, base, path, token, accept_gzip=args.gzip) for _tab in range(args.tabs) for path in paths]
            for future in as_completed(futures):
                try:
                    path, status, millis, size, _ = future.result()
                    samples.append((path, millis, size))
                    if status != 200:
                        errors.append(f"{path}: HTTP {status}")
                except Exception as exc:
                    errors.append(type(exc).__name__)
    latencies = sorted(item[1] for item in samples)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * .95))] if latencies else None
    chart_samples = [item for item in samples if "/history?" in item[0] or "/metrics?" in item[0]]
    print(json.dumps({
        "simulated_tabs": args.tabs, "rounds": args.rounds,
        "charts": args.charts,
        "gzip": args.gzip,
        "read_requests": len(samples), "errors": len(errors),
        "mean_ms": round(mean(latencies), 1) if latencies else None,
        "p95_ms": round(p95, 1) if p95 is not None else None,
        "max_ms": round(max(latencies), 1) if latencies else None,
        "mean_kb": round(mean(item[2] for item in samples) / 1024, 1) if samples else None,
        "chart_mean_kb": round(mean(item[2] for item in chart_samples) / 1024, 1) if chart_samples else None,
        "chart_max_ms": round(max(item[1] for item in chart_samples), 1) if chart_samples else None,
    }, ensure_ascii=False))
    if errors:
        print("Error types:", sorted(set(errors)))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
