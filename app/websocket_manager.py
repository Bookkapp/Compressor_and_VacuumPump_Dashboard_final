from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class WebSocketManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.broadcast_count = 0
        self.last_broadcast_at: datetime | None = None
        self.last_error: str | None = None

    @property
    def connection_count(self) -> int:
        return len(self.active)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def connect(self, websocket: WebSocket, subprotocol: str | None = None) -> None:
        await websocket.accept(subprotocol=subprotocol)
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        encoded = jsonable_encoder(payload)
        async def send_one(websocket: WebSocket) -> WebSocket | None:
            try:
                await asyncio.wait_for(websocket.send_json(encoded), timeout=2)
                return None
            except Exception:
                self.last_error = "WebSocket broadcast failed"
                return websocket

        dead = await asyncio.gather(*(send_one(websocket) for websocket in list(self.active)))
        for websocket in dead:
            if websocket is not None:
                self.disconnect(websocket)
        self.broadcast_count += 1
        self.last_broadcast_at = datetime.now()

    def broadcast_threadsafe(self, payload: dict[str, Any]) -> None:
        if not self.loop or self.loop.is_closed():
            self.last_error = "WebSocket loop is not ready"
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(payload), self.loop)

    def broadcast_state(self, summary: dict[str, Any] | None, devices: list[dict[str, Any]] | None, alerts: list[dict[str, Any]] | None) -> None:
        payload: dict[str, Any] = {"event": "state_update"}
        if summary is not None:
            payload["summary"] = summary
        if devices is not None:
            payload["devices"] = devices
        if alerts is not None:
            payload["alerts"] = alerts
        self.broadcast_threadsafe(payload)


manager = WebSocketManager()
