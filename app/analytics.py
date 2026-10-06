"""Small, dependency-free analytics for the engineering visualizations.

The API returns evidence (paired samples and correlation), never a definitive
fault diagnosis.  It deliberately lives outside the HTTP router so the same
logic can later be used by scheduled baseline/ML jobs.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from .services import get_metric_history


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(x) != len(y):
        return None
    mx, my = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return None if denominator == 0 else round(numerator / denominator, 4)


def _timeline(device_id: int, module_id: int, since: str | None, signals: list[str]) -> list[dict[str, Any]]:
    rows = get_metric_history(device_id, module_id=module_id, limit=3000, since=since)
    values: dict[str, dict[str, Any]] = defaultdict(dict)
    selected = set(signals)
    for row in rows:
        key = row.get("metric_key")
        value = _number(row.get("metric_value"))
        stamp = row.get("recorded_at")
        if key in selected and value is not None and stamp:
            values[str(stamp)][key] = value
    return [{"recorded_at": stamp, **point} for stamp, point in sorted(values.items())]


def correlation(device_id: int, module_id: int, signals: list[str], since: str | None = None) -> dict[str, Any]:
    if len(signals) < 2:
        raise HTTPException(status_code=422, detail="Select at least two signals")
    if len(signals) > 12:
        raise HTTPException(status_code=422, detail="A maximum of 12 signals is supported")
    points = _timeline(device_id, module_id, since, signals)
    matrix: list[list[float | None]] = []
    for first in signals:
        row: list[float | None] = []
        for second in signals:
            paired = [(point[first], point[second]) for point in points if first in point and second in point]
            row.append(_pearson([pair[0] for pair in paired], [pair[1] for pair in paired]))
        matrix.append(row)
    return {
        "signals": signals,
        "matrix": matrix,
        "samples": len(points),
        "analysis_window": {"from": since, "to": datetime.now().isoformat()},
        "method": "pearson",
    }


def relationship(device_id: int, module_id: int, x_signal: str, y_signal: str, since: str | None = None) -> dict[str, Any]:
    points = _timeline(device_id, module_id, since, [x_signal, y_signal])
    paired = [point for point in points if x_signal in point and y_signal in point]
    # A bounded response keeps the browser responsive while retaining the time axis for inspection.
    if len(paired) > 1200:
        step = math.ceil(len(paired) / 1200)
        paired = paired[::step]
    x_values, y_values = [point[x_signal] for point in paired], [point[y_signal] for point in paired]
    return {
        "x_signal": x_signal,
        "y_signal": y_signal,
        "points": [{"recorded_at": point["recorded_at"], "x": point[x_signal], "y": point[y_signal]} for point in paired],
        "correlation": _pearson(x_values, y_values),
        "samples": len(paired),
        "analysis_window": {"from": since, "to": datetime.now().isoformat()},
        "method": "pearson",
    }
