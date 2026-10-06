from __future__ import annotations

import json
import math
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MOCK_MQTT_TOPIC", "adi/telemetry")
RATE_SECONDS = float(os.getenv("MOCK_RATE_SECONDS", "2.0"))

DEVICES = [
    ("ESP32-HT9046-31", "HT9046-31", 0.15),
    ("ESP32-HT9046-35", "HT9046-35", 0.55),
    ("ESP32-HT9046-39", "HT9046-39", 0.9),
]

MODULES = [
    ("vacuum-pump", "Vacuum Pump"),
    ("drive-motor", "Drive Motor"),
    ("power-unit", "Power Unit"),
]


def payload(device_id: str, machine_code: str, module_code: str, module_name: str, fault: float, tick: int) -> dict:
    t = tick / 12.0
    module_factor = 1.0 if module_code == "vacuum-pump" else 0.45
    rising_fault = fault * module_factor * max(0, tick % 160 - 70) / 90
    ax = 0.04 * math.sin(t) + random.uniform(-0.03, 0.03)
    ay = 0.04 * math.cos(t / 1.7) + random.uniform(-0.03, 0.03)
    az = 1.0 + 0.05 * math.sin(t / 2.1) + random.uniform(-0.025, 0.025)
    vibration = math.sqrt(ax * ax + ay * ay + az * az) + 0.45 * fault * module_factor + rising_fault
    return {
        "device_id": device_id,
        "machine_code": machine_code,
        "display_name": machine_code,
        "module_code": module_code,
        "module_name": module_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 43 + 5 * fault * module_factor + 18 * rising_fault + random.uniform(-0.25, 0.25),
        "pressure": -78 + 12 * fault * module_factor + random.uniform(-1.2, 1.2),
        "current": 6.2 + 2.8 * fault * module_factor + 4.0 * rising_fault + random.uniform(-0.18, 0.18),
        "ax": ax,
        "ay": ay,
        "az": az,
        "vibration": vibration,
    }


def main() -> None:
    client = mqtt.Client(client_id=f"adi-mock-publisher-{int(time.time())}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    print(f"Publishing mock HT9046 telemetry to mqtt://{MQTT_HOST}:{MQTT_PORT} topic {MQTT_TOPIC}")
    tick = 0
    try:
        while True:
            for device_id, machine_code, fault in DEVICES:
                for module_code, module_name in MODULES:
                    body = payload(device_id, machine_code, module_code, module_name, fault, tick)
                    client.publish(MQTT_TOPIC, json.dumps(body), qos=0, retain=False)
            tick += 1
            time.sleep(RATE_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
