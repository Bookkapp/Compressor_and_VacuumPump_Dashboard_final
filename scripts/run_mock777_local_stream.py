"""Accelerated 12 × five-minute MX777 source-to-Dashboard rehearsal.

Requires the normal local APIs on 8000 and 5001 and the owner-authorized
synthetic MX777 rows in the normal local MySQL schemas. Never contacts a remote
host. The stream is accelerated; it is not a real 60-minute soak test.
"""

from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.config import settings
from scripts.copy_mock777_to_local_source import main as copy_pending
from scripts.mock777_month import stream


OPERATION = "http://127.0.0.1:8000"
DASHBOARD = "http://127.0.0.1:5001"


def dashboard_token() -> str:
    response = requests.post(
        DASHBOARD + "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
        timeout=12,
    )
    response.raise_for_status()
    return str(response.json()["token"])


def machine_from_api(headers: dict[str, str]) -> dict:
    response = requests.get(DASHBOARD + "/api/devices", headers=headers, timeout=20)
    response.raise_for_status()
    matching = [item for item in response.json() if item.get("machine_code") == "HT9046MX-777"]
    if len(matching) != 1:
        raise RuntimeError(f"Expected one Dashboard machine 777, found {len(matching)}")
    return matching[0]


def api_get(path: str, headers: dict[str, str]) -> tuple[int, float, int]:
    started = time.perf_counter()
    response = requests.get(DASHBOARD + path, headers=headers, timeout=30)
    return response.status_code, time.perf_counter() - started, len(response.content)


def main() -> None:
    if settings.db_host not in {"localhost", "127.0.0.1"} or settings.telemetry_db_host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("The stream rehearsal is localhost-only")
    token = dashboard_token()
    headers = {"Authorization": "Bearer " + token}
    initial = machine_from_api(headers)
    module_ids = [int(item["id"]) for item in initial["modules"] if str(item.get("module_code", "")).startswith("compressor-m")]
    if len(module_ids) != 8:
        raise RuntimeError(f"Expected 8 Dashboard compressor modules, found {len(module_ids)}")
    steps = []
    for step in range(1, 13):
        started = time.perf_counter()
        stream()
        copy_pending()
        inserted_at = None
        # The fixture manifest is the source of the accelerated event time.
        import pymysql
        conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                               password=settings.db_password, database="ht_mock777_month_source",
                               cursorclass=pymysql.cursors.DictCursor)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT stream_start,stream_step FROM mock777_manifest WHERE fixture_key='month_v1'")
                manifest = cur.fetchone()
                if manifest["stream_step"] != step:
                    raise RuntimeError("The fixture stream step is out of sequence")
                from datetime import timedelta
                inserted_at = manifest["stream_start"] + timedelta(minutes=5 * step)
        finally:
            conn.close()
        score_started = time.perf_counter()
        score_response = requests.post(
            OPERATION + "/api/v1/inference/run",
            params={"machine_number": "777", "limit": 12, "sync_to_pm": "true"},
            timeout=90,
        )
        score_latency = time.perf_counter() - score_started
        score_response.raise_for_status()
        scoring = score_response.json()
        deadline = time.perf_counter() + 12
        propagated = False
        machine = {}
        while time.perf_counter() < deadline:
            machine = machine_from_api(headers)
            stamps = [item.get("health_score_at") for item in machine["modules"]
                      if str(item.get("module_code", "")).startswith("compressor-m")]
            if len(stamps) == 8 and all(stamp and stamp >= inserted_at.isoformat() for stamp in stamps):
                propagated = True
                break
            time.sleep(0.5)
        modules = machine.get("modules", [])
        step_record = {
            "step": step,
            "event_time": inserted_at.isoformat(),
            "scored_windows": scoring.get("scored_windows"),
            "raw_flags": scoring.get("raw_flags"),
            "persistent_alerts": scoring.get("persistent_alerts"),
            "dashboard_propagated": propagated,
            "m6_health": next((item.get("health_score") for item in modules if item.get("module_code") == "compressor-m6"), None),
            "m6_status": next((item.get("status") for item in modules if item.get("module_code") == "compressor-m6"), None),
            "score_latency_s": round(score_latency, 3),
            "end_to_end_s": round(time.perf_counter() - started, 3),
        }
        steps.append(step_record)
        print(json.dumps(step_record, default=str), flush=True)

    # Ten independent HTTP clients approximate the requests of ten tabs. This
    # checks API concurrency; visual rendering is a separate browser test.
    paths = ["/api/summary", "/api/devices", "/api/overview/health-trend?range=24h",
             "/api/overview/health-trend?range=1m"]
    paths += [f"/api/devices/{initial['id']}/history?module_id={module_id}&limit=600" for module_id in module_ids]
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(api_get, paths[index % len(paths)], headers) for index in range(40)]
        for future in as_completed(futures):
            results.append(future.result())
    latencies = sorted(item[1] for item in results)
    p95 = latencies[int(0.95 * (len(latencies) - 1))]
    print("SUMMARY", json.dumps({
        "steps": len(steps), "dashboard_propagated": sum(row["dashboard_propagated"] for row in steps),
        "scored_windows": sum(int(row["scored_windows"] or 0) for row in steps),
        "max_score_latency_s": max(row["score_latency_s"] for row in steps),
        "median_end_to_end_s": round(statistics.median(row["end_to_end_s"] for row in steps), 3),
        "parallel_requests": len(results), "parallel_http_errors": sum(item[0] != 200 for item in results),
        "parallel_p95_s": round(p95, 3), "parallel_max_s": round(max(latencies), 3),
    }, default=str), flush=True)


if __name__ == "__main__":
    main()
