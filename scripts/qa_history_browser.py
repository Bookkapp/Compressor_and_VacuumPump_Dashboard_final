"""Authenticated localhost read-only contract and short concurrent-load QA.

No record creation, ACK, maintenance mutations, or source writes. Timings
include HTTP, metadata lookup, mapping and serialization (not browser paint).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import statistics
from time import perf_counter
from urllib.request import Request, urlopen
from urllib.parse import urlencode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5001")
    parser.add_argument("--output", default="artifacts/history-browser-qa/load.json")
    args = parser.parse_args()

    def read(path, token=None, body=None):
        request = Request(args.base + path, data=json.dumps(body).encode() if body else None,
                          headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    # Existing development account; never persist its session token.
    token = read("/api/auth/login", body={"username": "ADIadmin", "password": "ADIIOT"})["token"]
    devices = read("/api/devices", token)
    cases = []
    for machine in ("HT9046MX-777", "HT9046MX-017", "HT9046MX-080"):
        device = next(item for item in devices if item["machine_code"] == machine)
        for module in device["modules"]:
            if module["module_code"] in ("compressor-m1", "compressor-m5", "vacuum-pump"):
                cases.append((device, module))
    results = []
    start, end = "2026-09-01T00:00:00+07:00", "2026-10-01T00:00:00+07:00"

    def run(case):
        device, module = case
        params = urlencode({"module_id": module["id"], "start": start, "end": end, "limit": 1200})
        stamp = perf_counter()
        result = read(f"/api/devices/{device['id']}/history-chart?{params}", token)
        elapsed = (perf_counter() - stamp) * 1000
        expected = module["telemetry_source"]
        assert result["source"] == expected and result["module_id"] == module["id"]
        assert len(result["rows"]) <= 1200
        times = [datetime.fromisoformat(row["recorded_at"]) for row in result["rows"]]
        assert times == sorted(times)
        assert all(datetime.fromisoformat(start) <= time < datetime.fromisoformat(end) for time in times)
        assert all(("hp_1st" in row) == (expected == "compressor") and ("accel_x" in row) == (expected == "vacuum") for row in result["rows"])
        if times:
            # Actual endpoints, even if the requested range exceeds chart cap.
            assert times[0].replace(tzinfo=None) == datetime.fromisoformat(result["first_at"])
            assert times[-1].replace(tzinfo=None) == datetime.fromisoformat(result["last_at"])
        return {"machine": device["machine_code"], "module": module["module_code"], "ms": round(elapsed, 2), "total": result["total"], "points": len(times), "sampled": result["sampled"]}

    cold = [run(case) for case in cases]
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(run, cases * 4))
    device, module = cases[0]
    page_params = {"module_id": module["id"], "start": start, "end": end, "limit": 100}
    pages = [read(f"/api/devices/{device['id']}/history-page?{urlencode({**page_params, 'offset': offset})}", token) for offset in (0, 100)]
    assert not ({row["id"] for row in pages[0]["rows"]} & {row["id"] for row in pages[1]["rows"]})
    assert all(page["sampled"] is False for page in pages)
    short = read(f"/api/devices/{device['id']}/history-chart?{urlencode({'module_id':module['id'],'start':'2026-09-02T00:00:00+07:00','end':'2026-09-02T01:00:00+07:00'})}", token)
    assert len(short["rows"]) > 0, "An old hour must be available beyond newest N samples"
    times = sorted(result["ms"] for result in results)
    report = {"requests": len(results), "workers": 12, "cold": cold, "concurrent": results,
              "median_ms": round(statistics.median(times), 2), "p95_ms": times[min(len(times)-1, int(.95 * len(times)))],
              "max_ms": max(times), "old_hour_points": len(short["rows"]), "page_overlap": False}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "concurrent"}, indent=2))


if __name__ == "__main__":
    main()
