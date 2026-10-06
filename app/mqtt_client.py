from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from .config import settings
from .services import ingest_telemetry
from .websocket_manager import WebSocketManager


log = logging.getLogger("adi.mqtt")


class MqttIngestor:
    def __init__(self) -> None:
        self.client: Any = None
        self.connected = False
        self.last_error: str | None = None
        self.last_message_at: datetime | None = None
        self.last_message_topic: str | None = None
        self.last_message_device_id: int | None = None
        self.last_message_module_id: int | None = None
        self.message_count = 0

    def start(self, ws_manager: WebSocketManager) -> None:
        if not settings.mqtt_enabled:
            log.info("MQTT disabled by MQTT_ENABLED=false")
            return

        try:
            import paho.mqtt.client as mqtt
        except Exception as exc:
            self.last_error = f"paho-mqtt is not installed: {exc}"
            log.warning(self.last_error)
            return

        try:
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.mqtt_client_id)
            except Exception:
                self.client = mqtt.Client(client_id=settings.mqtt_client_id)

            if settings.mqtt_username:
                self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password or None)

            def on_connect(client, userdata, flags, rc, *extra):
                ok = int(rc) == 0 if isinstance(rc, int) else str(rc).lower() in {"success", "0"}
                self.connected = ok
                if ok:
                    self.last_error = None
                    client.subscribe(settings.mqtt_topic)
                    client.subscribe(settings.mqtt_legacy_topic)
                    log.info("MQTT connected to %s:%s", settings.mqtt_host, settings.mqtt_port)
                else:
                    self.last_error = f"MQTT connect failed: {rc}"
                    log.warning(self.last_error)

            def on_disconnect(client, userdata, rc, *extra):
                self.connected = False
                if rc:
                    self.last_error = f"MQTT disconnected: {rc}"
                    log.warning(self.last_error)

            def on_message(client, userdata, message):
                topic = message.topic
                try:
                    payload = json.loads(message.payload.decode("utf-8"))
                    event = ingest_telemetry(payload, source="mqtt", topic=topic)
                    self.message_count += 1
                    self.last_message_at = datetime.now()
                    self.last_message_topic = topic
                    self.last_message_device_id = event.get("device_id")
                    self.last_message_module_id = event.get("module_id")
                    ws_manager.broadcast_threadsafe({"event": "telemetry", "data": event})
                except Exception as exc:
                    self.last_error = f"MQTT ingest failed on {topic}: {exc}"
                    log.exception(self.last_error)

            self.client.on_connect = on_connect
            self.client.on_disconnect = on_disconnect
            self.client.on_message = on_message
            self.client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=60)
            self.client.loop_start()
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("MQTT startup failed: %s", exc)


mqtt_ingestor = MqttIngestor()
