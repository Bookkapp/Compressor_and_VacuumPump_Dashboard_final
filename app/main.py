from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .auth import create_token, decode_token, require_admin, token_from_header
from .analytics import correlation, relationship
from .cache import cache
from .config import PUBLIC_DIR, settings
from .history_browser import browse_history
from . import db as db_state
from .db import fetch_all, fetch_one, init_database
from .services import (
    acknowledge_alert,
    authenticate,
    clear_alerts,
    get_numbering_status,
    reset_numbering,
    create_device,
    create_maintenance_log,
    create_module,
    create_work_order,
    delete_maintenance_log,
    delete_work_order,
    delete_device,
    delete_module,
    get_device_detail,
    get_fleet_health_trend,
    get_history,
    get_metric_history,
    get_summary,
    get_user,
    ingest_telemetry,
    list_devices,
    list_maintenance_logs,
    list_users,
    list_work_orders,
    public_user,
    register_external_sample,
    seed_demo_data,
    update_device,
    update_module,
    update_maintenance_log,
    update_work_order,
)
from .telemetry_sources import telemetry_poller, telemetry_sources
from .websocket_manager import manager


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("adi.main")


def _broadcast_current_state() -> None:
    if manager.connection_count == 0:
        return
    try:
        summary = get_summary()
        devices = list_devices()
        alerts_rows = fetch_all(
            """
            SELECT a.*, d.machine_code, d.display_name, m.module_name,
                   u.full_name AS acknowledged_by_name
            FROM pm_alerts a
            INNER JOIN pm_devices d ON d.id = a.device_id
            INNER JOIN pm_modules m ON m.id = a.module_id
            LEFT JOIN pm_users u ON u.id = a.acknowledged_by
            ORDER BY a.recorded_at DESC, a.id DESC
            LIMIT 500
            """,
        )
        manager.broadcast_state(summary, devices, alerts_rows)
    except Exception as exc:
        log.debug("Could not broadcast state: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.set_loop(asyncio.get_running_loop())
    try:
        init_database()
        seed_demo_data()
    except Exception as exc:
        log.error("Database startup failed; refusing to serve an unhealthy application: %s", exc)
        raise

    def register_live_sample(sample) -> None:
        register_external_sample(sample)

    from .operation_pull import operation_pull
    telemetry_poller.start(register_live_sample, on_cycle=_broadcast_current_state)
    operation_pull.start(on_change=_broadcast_current_state)
    yield
    operation_pull.stop()
    telemetry_poller.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


def v1(data: Any, *, source: str = "dashboard") -> dict[str, Any]:
    """Envelope for new API endpoints; legacy endpoints remain compatible."""
    return {"data": data, "meta": {"timestamp": datetime.now().isoformat(), "source": source}}


@app.get("/api/v1/analytics/correlation")
def v1_correlation(
    device_id: int,
    module_id: int,
    signals: str,
    since: str | None = None,
    token: dict[str, Any] = Depends(token_from_header),
):
    selected = [value.strip() for value in signals.split(",") if value.strip()]
    return v1(correlation(device_id, module_id, selected, since), source="mysql-telemetry")


@app.get("/api/v1/analytics/relationship")
def v1_relationship(
    device_id: int,
    module_id: int,
    x_signal: str,
    y_signal: str,
    since: str | None = None,
    token: dict[str, Any] = Depends(token_from_header),
):
    return v1(relationship(device_id, module_id, x_signal, y_signal, since), source="mysql-telemetry")


@app.post("/api/auth/login")
def login(body: dict[str, Any]):
    user = authenticate(str(body.get("username", "")), str(body.get("password", "")))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"token": create_token(user), "user": public_user(user)}


@app.get("/api/auth/me")
def me(token: dict[str, Any] = Depends(token_from_header)):
    user = get_user(int(token["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User is no longer active")
    return public_user(user)


@app.get("/api/db/status")
def db_status():
    try:
        row = fetch_one("SELECT DATABASE() AS database_name, NOW() AS server_time")
        return {
            "connected": True,
            "database_name": row["database_name"],
            "server_time": row["server_time"],
            "db_host": settings.db_host,
            "db_port": settings.db_port,
            "telemetry": telemetry_sources.status(),
            "operation_pull": __import__("app.operation_pull", fromlist=["operation_pull"]).operation_pull.status,
        }
    except Exception as exc:
        return {
            "connected": False,
            "error": str(exc),
            "startup_error": db_state.last_startup_error,
            "db_host": settings.db_host,
            "db_port": settings.db_port,
            "telemetry": telemetry_sources.status(),
        }


@app.get("/api/production/status")
def production_status(admin: dict[str, Any] = Depends(require_admin)):
    database: dict[str, Any]
    latest = None
    try:
        row = fetch_one("SELECT DATABASE() AS database_name, NOW() AS server_time")
        latest = fetch_one(
            """
            SELECT ds.recorded_at, d.machine_code, d.display_name, m.module_name
            FROM pm_diagnostic_snapshots ds
            INNER JOIN pm_devices d ON d.id = ds.device_id
            INNER JOIN pm_modules m ON m.id = ds.module_id
            ORDER BY ds.recorded_at DESC, ds.id DESC
            LIMIT 1
            """
        )
        database = {
            "connected": True,
            "database_name": row["database_name"],
            "server_time": row["server_time"],
            "host": settings.db_host,
            "port": settings.db_port,
        }
    except Exception as exc:
        database = {
            "connected": False,
            "error": str(exc),
            "startup_error": db_state.last_startup_error,
            "host": settings.db_host,
            "port": settings.db_port,
        }

    source_status = telemetry_sources.status()
    return {
        "database": database,
        "telemetry": source_status,
        "ingestion": {
            "live_source_samples": source_status["last_sample_count"],
            "poll_count": source_status["poll_count"],
            "last_poll_at": source_status["last_poll_at"],
            "latest_record": latest,
        },
        "websocket": {
            "active_connections": manager.connection_count,
            "loop_active": bool(manager.loop and not manager.loop.is_closed()),
            "broadcast_count": manager.broadcast_count,
            "last_broadcast_at": manager.last_broadcast_at,
            "last_error": manager.last_error,
        },
    }


@app.get("/api/summary")
def summary(token: dict[str, Any] = Depends(token_from_header)):
    return get_summary()


@app.get("/api/overview/health-trend")
def overview_health_trend(range: str = "7d", token: dict[str, Any] = Depends(token_from_header)):
    return get_fleet_health_trend(range)


@app.get("/api/users")
def users(admin: dict[str, Any] = Depends(require_admin)):
    return list_users()


@app.get("/api/devices")
def devices(token: dict[str, Any] = Depends(token_from_header)):
    return list_devices()


@app.post("/api/devices")
def devices_create(body: dict[str, Any], admin: dict[str, Any] = Depends(require_admin)):
    device = create_device(body)
    _broadcast_current_state()
    return device


@app.get("/api/devices/{device_id}")
def devices_detail(device_id: int, token: dict[str, Any] = Depends(token_from_header)):
    return get_device_detail(device_id)


@app.patch("/api/devices/{device_id}")
def devices_update(device_id: int, body: dict[str, Any], admin: dict[str, Any] = Depends(require_admin)):
    device = update_device(device_id, body)
    _broadcast_current_state()
    return device


@app.delete("/api/devices/{device_id}")
def devices_delete(device_id: int, admin: dict[str, Any] = Depends(require_admin)):
    result = delete_device(device_id)
    _broadcast_current_state()
    return result


@app.get("/api/devices/{device_id}/history")
def devices_history(
    device_id: int,
    module_id: int | None = None,
    limit: int = 240,
    since: str | None = None,
    signals: str | None = None,
    token: dict[str, Any] = Depends(token_from_header),
):
    if signals is None:
        return get_history(device_id, module_id=module_id, limit=limit, since=since)
    allowed = {"hp_1st", "lp_1st", "hp_2nd", "lp_2nd", "temperature_hi", "temperature_lo", "valve", "busy", "sv", "temperature_c", "pressure_kpa", "current_a", "vibration", "accel_x", "accel_y", "accel_z"}
    selected = list(dict.fromkeys(signals.split(",")))
    if not module_id or not selected or any(key not in allowed for key in selected):
        raise HTTPException(status_code=422, detail="Select one module and valid sensor signals")
    rows = get_history(device_id, module_id=module_id, limit=limit, since=since)
    # Chart responses omit repeated machine names/IDs/status/null legacy columns.
    return [{"recorded_at": row["recorded_at"], **{key: row.get(key) for key in selected}} for row in rows]


@app.get("/api/devices/{device_id}/history-batch")
def devices_history_batch(
    device_id: int,
    module_ids: str,
    signals: str,
    limit: int = 2000,
    since: str | None = None,
    token: dict[str, Any] = Depends(token_from_header),
):
    try:
        selected = list(dict.fromkeys(int(value) for value in module_ids.split(",")))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid module selection")
    if not 1 <= len(selected) <= 12 or any(value < 1 for value in selected):
        raise HTTPException(status_code=422, detail="Select up to 12 modules")
    return {str(module): devices_history(device_id, module, limit, since, signals, token) for module in selected}


@app.get("/api/devices/{device_id}/history-page")
def devices_history_page(
    device_id: int, module_id: int, start: str | None = None, end: str | None = None,
    limit: int = 250, offset: int = 0, token: dict[str, Any] = Depends(token_from_header),
):
    return browse_history(device_id, module_id, start, end, limit, offset)


@app.get("/api/devices/{device_id}/history-chart")
def devices_history_chart(
    device_id: int, module_id: int, start: str | None = None, end: str | None = None,
    limit: int = 1200, signals: str | None = None, token: dict[str, Any] = Depends(token_from_header),
):
    return browse_history(device_id, module_id, start, end, limit, chart=True, signals=signals)


@app.get("/api/devices/{device_id}/metrics")
def devices_metrics(
    device_id: int,
    module_id: int | None = None,
    limit: int = 600,
    since: str | None = None,
    token: dict[str, Any] = Depends(token_from_header),
):
    return get_metric_history(device_id, module_id=module_id, limit=limit, since=since)


@app.post("/api/devices/{device_id}/modules")
def modules_create(device_id: int, body: dict[str, Any], admin: dict[str, Any] = Depends(require_admin)):
    module = create_module(device_id, body)
    _broadcast_current_state()
    return module


@app.patch("/api/modules/{module_id}")
def modules_update(module_id: int, body: dict[str, Any], admin: dict[str, Any] = Depends(require_admin)):
    module = update_module(module_id, body)
    _broadcast_current_state()
    return module


@app.delete("/api/modules/{module_id}")
def modules_delete(module_id: int, admin: dict[str, Any] = Depends(require_admin)):
    result = delete_module(module_id)
    _broadcast_current_state()
    return result


@app.post("/api/telemetry")
def telemetry(body: dict[str, Any]):
    raise HTTPException(
        status_code=410,
        detail="Direct ESP32/MQTT ingestion is disabled. Insert telemetry into the configured MySQL source.",
    )


@app.post("/api/data")
def legacy_telemetry(body: dict[str, Any]):
    return telemetry(body)


@app.get("/api/work-orders")
def work_orders(limit: int = 100, token: dict[str, Any] = Depends(token_from_header)):
    assigned_to = None if token.get("role") == "admin" else int(token["sub"])
    return list_work_orders(limit=limit, assigned_to=assigned_to)


@app.post("/api/work-orders")
def work_orders_create(body: dict[str, Any], admin: dict[str, Any] = Depends(require_admin)):
    row = create_work_order(body, created_by=int(admin["sub"]))
    _broadcast_current_state()
    return row


@app.patch("/api/work-orders/{work_order_id}")
def work_orders_update(work_order_id: int, body: dict[str, Any], token: dict[str, Any] = Depends(token_from_header)):
    row = update_work_order(work_order_id, body, token)
    _broadcast_current_state()
    return row


@app.delete("/api/work-orders/{work_order_id}")
def work_orders_delete(work_order_id: int, admin: dict[str, Any] = Depends(require_admin)):
    result = delete_work_order(work_order_id, admin)
    _broadcast_current_state()
    return result


@app.get("/api/maintenance-logs")
def maintenance_logs(limit: int = 100, offset: int = 0, device_id: int | None = None, token: dict[str, Any] = Depends(token_from_header)):
    return list_maintenance_logs(device_id=device_id, limit=limit, offset=offset)


@app.post("/api/maintenance-logs")
def maintenance_logs_create(body: dict[str, Any], token: dict[str, Any] = Depends(token_from_header)):
    row = create_maintenance_log(body, token)
    _broadcast_current_state()
    return row


@app.delete("/api/maintenance-logs/{log_id}")
def maintenance_logs_delete(log_id: int, admin: dict[str, Any] = Depends(require_admin)):
    result = delete_maintenance_log(log_id, admin)
    _broadcast_current_state()
    return result


@app.patch("/api/maintenance-logs/{log_id}")
def maintenance_logs_update(log_id: int, body: dict[str, Any], admin: dict[str, Any] = Depends(require_admin)):
    row = update_maintenance_log(log_id, body)
    _broadcast_current_state()
    return row


@app.get("/api/alerts")
def alerts(limit: int = 50, offset: int = 0, token: dict[str, Any] = Depends(token_from_header)):
    return fetch_all(
        """
        SELECT
            a.*,
            d.machine_code,
            d.display_name,
            m.module_name,
            u.full_name AS acknowledged_by_name
        FROM pm_alerts a
        INNER JOIN pm_devices d ON d.id = a.device_id
        INNER JOIN pm_modules m ON m.id = a.module_id
        LEFT JOIN pm_users u ON u.id = a.acknowledged_by
        ORDER BY a.recorded_at DESC, a.id DESC
        LIMIT %s OFFSET %s
        """,
        (min(limit, 500), max(offset, 0)),
    )


@app.get("/api/alerts/recent")
def recent_alerts(limit: int = 100, token: dict[str, Any] = Depends(token_from_header)):
    return alerts(limit=limit, offset=0, token=token)


@app.patch("/api/alerts/{alert_id}/acknowledge")
def alerts_acknowledge(alert_id: int, token: dict[str, Any] = Depends(token_from_header)):
    row = acknowledge_alert(alert_id, int(token["sub"]))
    _broadcast_current_state()
    return row


@app.delete("/api/alerts")
def alerts_clear(admin: dict[str, Any] = Depends(require_admin)):
    result = clear_alerts()
    _broadcast_current_state()
    return result


@app.get("/api/admin/numbering")
def admin_numbering_status(admin: dict[str, Any] = Depends(require_admin)):
    return get_numbering_status()


@app.post("/api/admin/numbering/reset")
def admin_numbering_reset(
    payload: dict[str, Any] | None = None,
    admin: dict[str, Any] = Depends(require_admin),
):
    target = (payload or {}).get("target", "all")
    result = reset_numbering(target, admin)
    _broadcast_current_state()
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    protocols = websocket.scope.get("subprotocols", [])
    if len(protocols) != 2 or protocols[0] != "adi-v1":
        await websocket.close(code=4401)
        return
    try:
        decode_token(protocols[1])
    except HTTPException:
        await websocket.close(code=4401)
        return
    await manager.connect(websocket, subprotocol="adi-v1")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/dashboard")
def dashboard_redirect():
    return RedirectResponse("/")


app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
