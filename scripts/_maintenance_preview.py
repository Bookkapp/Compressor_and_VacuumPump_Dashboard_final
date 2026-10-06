"""Local visual preview with synthetic work orders; no database access."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from urllib.parse import urlparse


PUBLIC = Path(__file__).resolve().parents[1] / "public"
USER = {"id": 1, "username": "Preview", "full_name": "Preview User", "role": "admin"}
DEVICES = [{
    "id": 1, "device_uid": "preview:HT9046MX-001", "machine_code": "HT9046MX-001",
    "display_name": "HT9046MX-001 · Preview data", "status": "WARNING", "modules": [
        {"id": 11, "module_name": "Vacuum Pump", "module_code": "vacuum-pump", "status": "WARNING", "vibration": 2.8},
        {"id": 12, "module_name": "Compressor M1", "module_code": "compressor-m1", "status": "NORMAL", "health_score": 94},
    ],
}]
for index, status in enumerate(("MAINTENANCE_REQUIRED", "WARNING", "NORMAL", "NORMAL", "NORMAL"), start=2):
    DEVICES.append({
        "id": index, "device_uid": f"preview:HT9046MX-{index:03d}",
        "machine_code": f"HT9046MX-{index:03d}", "display_name": f"HT9046MX-{index:03d} · Preview data",
        "status": status, "connection_state": "ONLINE", "last_seen": datetime.now().isoformat(),
        "modules": [
            {"id": index * 10 + 1, "module_name": "Vacuum Pump", "module_code": "vacuum-pump", "status": status, "vibration": 3.2 if status == "WARNING" else 1.4},
            {"id": index * 10 + 2, "module_name": "Compressor M1", "module_code": "compressor-m1", "status": status, "health_score": 35 if status == "MAINTENANCE_REQUIRED" else 85},
        ],
    })
ORDERS = [
    {"id": 1042, "device_id": 1, "source_alert_id": 2042, "display_name": "HT9046MX-001 · Preview data", "module_name": "Vacuum Pump",
     "assigned_full_name": "Maintenance Team A", "title": "Inspect vacuum pump vibration",
     "description": "Review vibration trend and inspect the pump mounting before the next shift.",
     "priority": "HIGH", "status": "OPEN"},
    {"id": 1041, "device_id": 1, "display_name": "HT9046MX-001 · Preview data", "module_name": "Compressor M1",
     "assigned_full_name": "Maintenance Team B", "title": "Check compressor stage pressure",
     "description": "Compare HP and LP stage readings during normal operation.",
     "priority": "MEDIUM", "status": "IN_PROGRESS"},
]
LOGS = [{
    "id": 301, "device_id": 1, "display_name": "HT9046MX-001 · Preview data",
    "module_name": "Compressor M1", "technician_name": "Maintenance Team B",
    "action_taken": "Inspected stage pressure and valve response.",
    "cost_baht": 250, "recorded_at": "2026-09-23T09:00:00",
}]
ALERTS = [{
    "id": 2042, "device_id": 1, "module_id": 11, "display_name": "HT9046MX-001 · Preview data",
    "module_name": "Vacuum Pump", "severity": "warning", "title": "Estimated vacuum pressure warning",
    "message": "Estimated pressure is -65 kPa.", "acknowledged": True,
    "recorded_at": "2026-09-23T08:30:00", "suppressed_until": "2026-09-30T08:30:00",
}]


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, value):
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.send_json({"token": "local-preview", "user": USER})

    def do_GET(self):
        path = urlparse(self.path).path
        responses = {
            "/api/db/status": {"connected": True, "database": "synthetic_preview"},
            "/api/auth/me": USER,
            "/api/summary": {"total_devices": 6, "counts": {"WARNING": 2, "MAINTENANCE_REQUIRED": 1, "NORMAL": 3}, "connection_counts": {"ONLINE": 6}, "open_work_orders": 2},
            "/api/devices": DEVICES,
            "/api/work-orders": ORDERS,
            "/api/maintenance-logs": LOGS,
            "/api/alerts": ALERTS,
            "/api/users": [USER],
            "/api/overview/health-trend": {
                "range": "1m" if "range=1m" in self.path else "24h",
                "source": "synthetic_preview_only",
                "points": [
                    {"at": (datetime.now().replace(minute=0, second=0, microsecond=0) - (timedelta(days=offset) if "range=1m" in self.path else timedelta(hours=offset))).isoformat(),
                     "good": 6 + offset % 3, "warning": 1 + offset % 2, "repair_now": offset % 3 == 0 and 1 or 0, "observed": 10}
                    for offset in range(29 if "range=1m" in self.path else 23, -1, -1)
                ],
            },
        }
        if path in responses:
            self.send_json(responses[path])
        else:
            super().do_GET()

    def translate_path(self, path):
        requested = urlparse(path).path.lstrip("/") or "index.html"
        target = (PUBLIC / requested).resolve()
        if not target.is_relative_to(PUBLIC.resolve()) or not target.exists():
            target = PUBLIC / "index.html"
        return str(target)

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5098
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
