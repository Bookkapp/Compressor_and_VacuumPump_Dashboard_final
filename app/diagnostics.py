from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from statistics import mean
from typing import Any


VACUUM_VIBRATION_SLOPE = -0.0439
VACUUM_VIBRATION_INTERCEPT = -2.2098
VACUUM_PRESSURE_NORMAL_LOW_KPA = -90.0
VACUUM_PRESSURE_WARNING_KPA = -70.0
VACUUM_PRESSURE_CRITICAL_KPA = -60.0


def n(value: Any, fallback: float | None = 0.0) -> float | None:
    if value is None or value == "":
        return fallback
    try:
        parsed = float(value)
        if math.isfinite(parsed):
            return parsed
    except (TypeError, ValueError):
        pass
    return fallback


def roundn(value: float | None, digits: int = 3) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def estimate_vacuum_pressure_kpa(vibration_mm_s: Any) -> float | None:
    """Estimate vacuum pressure from the approved field calibration curve.

    Existing empirical relation V = -0.0439 * pressure (kPa) - 2.2098.
    Coefficients and input numbers are unchanged by the owner's G rms display
    correction. The legacy argument name is retained for compatibility; it is
    not proof of a physical velocity-to-acceleration conversion. The deployed
    producer's RMS calculation and calibration input units must be verified.
    """
    vibration = n(vibration_mm_s, None)
    if vibration is None:
        return None
    return roundn((vibration - VACUUM_VIBRATION_INTERCEPT) / VACUUM_VIBRATION_SLOPE, 3)


def vacuum_pressure_condition(pressure_kpa: Any) -> tuple[str, str | None]:
    pressure = n(pressure_kpa, None)
    if pressure is None:
        return "OFFLINE", "vacuum_pressure_missing"
    if pressure > VACUUM_PRESSURE_CRITICAL_KPA:
        return "MAINTENANCE_REQUIRED", "vacuum_pressure_critical"
    if pressure > VACUUM_PRESSURE_WARNING_KPA:
        return "WARNING", "vacuum_pressure_warning"
    if pressure < VACUUM_PRESSURE_NORMAL_LOW_KPA:
        return "WARNING", "vacuum_pressure_outside_calibration"
    return "NORMAL", None


def extract_machine_code(value: str) -> str | None:
    compact = value.replace(" ", "").replace("_", "-").replace("/", "-")
    match = re.search(r"(HT9046-\w+)", compact, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def parse_topic(topic: str | None) -> dict[str, str | None]:
    if not topic:
        return {"device_uid": None, "module_code": None}

    parts = [p for p in topic.split("/") if p]
    if len(parts) >= 4 and parts[0] == "adi" and parts[-1] == "telemetry":
        return {"device_uid": parts[1], "module_code": parts[2]}
    if parts and parts[0] == "esp32" and parts[-1] == "telemetry":
        return {"device_uid": "/".join(parts[1:-1]) or None, "module_code": None}
    return {"device_uid": None, "module_code": None}


def normalize_telemetry(payload: dict[str, Any], topic: str | None = None, source: str = "http") -> dict[str, Any]:
    topic_data = parse_topic(topic)
    accel = payload.get("accel") or {}
    gyro = payload.get("gyro") or {}

    device_uid = str(
        payload.get("device_uid")
        or payload.get("deviceId")
        or payload.get("device_id")
        or payload.get("mac")
        or topic_data["device_uid"]
        or "ESP32-DEMO-001"
    ).strip()

    machine_code = str(
        payload.get("machine_code")
        or payload.get("machine_name")
        or extract_machine_code(device_uid)
        or "HT9046-UNASSIGNED"
    ).strip()

    module_code = str(
        payload.get("module_code")
        or payload.get("module")
        or payload.get("module_name")
        or topic_data["module_code"]
        or "vacuum-pump"
    ).strip()

    module_name = str(payload.get("module_name") or payload.get("module") or "Vacuum Pump").strip()

    ax = n(payload.get("ax", payload.get("accel_x", accel.get("x"))), 0.0) or 0.0
    ay = n(payload.get("ay", payload.get("accel_y", accel.get("y"))), 0.0) or 0.0
    az = n(payload.get("az", payload.get("accel_z", accel.get("z"))), 0.0) or 0.0
    vibration = n(payload.get("vibration", payload.get("vibration_g")), None)
    if vibration is None:
        vibration = math.sqrt(ax * ax + ay * ay + az * az)

    timestamp = payload.get("timestamp") or payload.get("recorded_at")
    recorded_at = datetime.now(timezone.utc)
    if timestamp:
        try:
            recorded_at = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            recorded_at = datetime.now(timezone.utc)

    return {
        "source": source,
        "topic": topic,
        "device_uid": device_uid,
        "machine_code": machine_code,
        "display_name": str(payload.get("display_name") or machine_code).strip(),
        "module_code": module_code.lower().replace(" ", "-"),
        "module_name": module_name,
        "recorded_at": recorded_at.replace(tzinfo=None),
        "temperature_c": n(payload.get("temperature_c", payload.get("temperature")), None),
        "pressure_kpa": n(payload.get("pressure_kpa", payload.get("pressure")), None),
        "current_a": n(payload.get("current_a", payload.get("current")), None),
        "accel_x": ax,
        "accel_y": ay,
        "accel_z": az,
        "vibration": vibration,
        "gyro_x": n(payload.get("gx", payload.get("gyro_x", gyro.get("x"))), None),
        "gyro_y": n(payload.get("gy", payload.get("gyro_y", gyro.get("y"))), None),
        "gyro_z": n(payload.get("gz", payload.get("gyro_z", gyro.get("z"))), None),
        "firmware_version": payload.get("firmware_version"),
        "raw_payload": payload,
    }


def slope_per_minute(rows: list[dict[str, Any]], key: str) -> float:
    points = [(r["recorded_at"].timestamp() / 60.0, n(r.get(key), None)) for r in rows if r.get(key) is not None]
    points = [(t, v) for t, v in points if v is not None]
    if len(points) < 3:
        return 0.0
    t0 = points[0][0]
    xs = [t - t0 for t, _ in points]
    ys = [v for _, v in points]
    xbar = mean(xs)
    ybar = mean(ys)
    denom = sum((x - xbar) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - xbar) * (ys[i] - ybar) for i, x in enumerate(xs)) / denom


def threshold_pair(thresholds: dict[str, Any], key: str, warning_default: float, critical_default: float) -> tuple[float, float]:
    config = thresholds.get(key) if isinstance(thresholds, dict) else None
    if not isinstance(config, dict):
        return warning_default, critical_default
    warning = n(config.get("warning"), warning_default)
    critical = n(config.get("critical"), critical_default)
    return warning, critical


def compute_diagnostics(
    history: list[dict[str, Any]],
    thresholds: dict[str, Any] | None = None,
    *,
    source: str | None = None,
) -> dict[str, Any]:
    if not history:
        return {}

    thresholds = thresholds if isinstance(thresholds, dict) else {}
    # The approved vacuum pressure bands always apply. Advanced temperature,
    # current and vibration overrides can be disabled per module.
    if source == "vacuum" and thresholds.get("enabled") is False:
        thresholds = {}
    recent = history[-256:]
    last = recent[-1]
    temperatures = [n(r.get("temperature_c"), None) for r in recent if r.get("temperature_c") is not None]
    currents = [n(r.get("current_a"), None) for r in recent if r.get("current_a") is not None]
    vibrations = [n(r.get("vibration"), None) for r in recent if r.get("vibration") is not None]
    if source == "vacuum":
        for row in recent:
            if row.get("pressure_kpa") is None:
                row["pressure_kpa"] = estimate_vacuum_pressure_kpa(row.get("vibration"))
    pressures = [n(r.get("pressure_kpa"), None) for r in recent if r.get("pressure_kpa") is not None]

    temp = n(last.get("temperature_c"), None)
    current = n(last.get("current_a"), None)
    vibration = n(last.get("vibration"), None)
    pressure = n(last.get("pressure_kpa"), None)
    temp_trend = slope_per_minute(recent, "temperature_c")

    issues: list[dict[str, str]] = []
    score = 100.0
    temp_warning, temp_critical = threshold_pair(thresholds, "temperature_c", 65, 80)
    current_warning, current_critical = threshold_pair(thresholds, "current_a", 10, 15)
    vibration_warning, vibration_critical = threshold_pair(thresholds, "vibration", 1.8, 2.8)
    pressure_config = thresholds.get("pressure_kpa") if isinstance(thresholds.get("pressure_kpa"), dict) else {}
    pressure_low = n(pressure_config.get("low"), -95) if pressure_config else -95
    pressure_high = n(pressure_config.get("high"), -60) if pressure_config else -60

    if temp is not None:
        if temp >= temp_critical:
            issues.append({"severity": "critical", "issue_key": "temperature", "title": "Temperature critical", "message": f"Temperature is {temp:.1f} C."})
            score -= 30
        elif temp >= temp_warning:
            issues.append({"severity": "warning", "issue_key": "temperature", "title": "Temperature elevated", "message": f"Temperature is {temp:.1f} C."})
            score -= 14
        score -= max(0.0, min(16.0, (temp - 45.0) * 0.45))

    if temp_trend > 1.5:
        issues.append({"severity": "warning", "issue_key": "temperature_trend", "title": "Rapid thermal rise", "message": f"Temperature trend is +{temp_trend:.2f} C/min."})
        score -= 12

    if current is not None:
        if current >= current_critical:
            issues.append({"severity": "critical", "issue_key": "current", "title": "Current critical", "message": f"Current is {current:.2f} A."})
            score -= 25
        elif current >= current_warning:
            issues.append({"severity": "warning", "issue_key": "current", "title": "Current elevated", "message": f"Current is {current:.2f} A."})
            score -= 12
        score -= max(0.0, min(14.0, (current - 6.5) * 1.4))

    if vibration is not None and source != "vacuum":
        if vibration >= vibration_critical:
            issues.append({"severity": "critical", "issue_key": "vibration", "title": "Vibration critical", "message": f"Vibration is {vibration:.2f}."})
            score -= 28
        elif vibration >= vibration_warning:
            issues.append({"severity": "warning", "issue_key": "vibration", "title": "Vibration elevated", "message": f"Vibration is {vibration:.2f}."})
            score -= 13
        score -= max(0.0, min(16.0, (vibration - 1.1) * 8.0))

    if pressure is not None and source == "vacuum":
        pressure_state, pressure_issue = vacuum_pressure_condition(pressure)
        if pressure_issue == "vacuum_pressure_critical":
            issues.append({
                "severity": "critical",
                "issue_key": "vacuum_pressure_high",
                "title": "Estimated vacuum pressure critical",
                "message": f"Estimated pressure is {pressure:.1f} kPa (> -60 kPa).",
            })
            score -= 45
        elif pressure_issue == "vacuum_pressure_warning":
            issues.append({
                "severity": "warning",
                "issue_key": "vacuum_pressure_high",
                "title": "Estimated vacuum pressure warning",
                "message": f"Estimated pressure is {pressure:.1f} kPa (warning band -70 to -60 kPa).",
            })
            score -= 25
        elif pressure_issue == "vacuum_pressure_outside_calibration":
            issues.append({
                "severity": "warning",
                "issue_key": "vacuum_pressure_low_outside_calibration",
                "title": "Estimated pressure outside calibration",
                "message": f"Estimated pressure is {pressure:.1f} kPa (< -90 kPa).",
            })
            score -= 15
    elif pressure is not None:
        if pressure > pressure_high or pressure < pressure_low:
            issues.append({"severity": "warning", "issue_key": "pressure", "title": "Pressure outside operating band", "message": f"Pressure is {pressure:.1f} kPa."})
            score -= 10

    critical_count = sum(1 for issue in issues if issue["severity"] == "critical")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    health_score = max(0, min(100, int(round(score))))

    if critical_count >= 1 or warning_count >= 2 or health_score < 55:
        condition = "MAINTENANCE_REQUIRED"
    elif warning_count == 1 or health_score < 75:
        condition = "WARNING"
    elif health_score < 88:
        condition = "WATCH"
    else:
        condition = "NORMAL"

    return {
        "sample_count": len(recent),
        "health_score": health_score,
        "condition_state": condition,
        "temperature_c": roundn(temp, 3),
        "temperature_avg_c": roundn(mean(temperatures), 3) if temperatures else None,
        "temperature_trend_c_per_min": roundn(temp_trend, 5),
        "pressure_kpa": roundn(pressure, 3),
        "pressure_avg_kpa": roundn(mean(pressures), 3) if pressures else None,
        "current_a": roundn(current, 4),
        "current_avg_a": roundn(mean(currents), 4) if currents else None,
        "vibration": roundn(vibration, 4),
        "vibration_avg": roundn(mean(vibrations), 4) if vibrations else None,
        "ai_model_version": "vacuum-rule-v1" if source == "vacuum" else "ai-placeholder-v0",
        "ai_condition": "RULE_BASED" if source == "vacuum" else "MODEL_PENDING",
        "ai_confidence": None,
        "ai_notes": (
            "Pressure is estimated from vibration using the approved field calibration; no pressure sensor is installed."
            if source == "vacuum"
            else "AI model hook is reserved; no rule-based score is presented as a Compressor ML score."
        ),
        "alerts": issues,
    }
