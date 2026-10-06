from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.maintenance_evidence import event_context, incident_snapshot
from app.services import create_work_order, list_maintenance_logs


def test_unknown_onset_is_not_creation_time():
    context = event_context({}, default_timezone="Asia/Bangkok")
    assert context["event_started_at"] is None
    assert context["event_time_precision"] == "UNKNOWN"


@pytest.mark.parametrize("data", [
    {"event_ended_at": "2026-09-07T13:00"},
    {"event_started_at": "2026-09-07T13:00", "event_ended_at": "2026-09-07T12:00"},
    {"event_started_at": "bad"}, {"event_started_at": "2026-09-07"},
    {"event_timezone": "not/a/zone"}, {"event_time_precision": "CERTAIN"},
])
def test_invalid_context_is_rejected(data):
    with pytest.raises(HTTPException) as raised:
        event_context(data, default_timezone="Asia/Bangkok")
    assert raised.value.status_code == 400


def test_timezone_and_edit_preserve_instant():
    result = event_context({"event_started_at": "2026-09-07T05:00:00Z"}, default_timezone="Asia/Bangkok")
    assert result["event_started_at"] == datetime(2026,9,7,12)
    moved = event_context({"event_timezone": "UTC"}, default_timezone="Asia/Bangkok", existing=result)
    assert moved["event_started_at"] == datetime(2026,9,7,5)


def test_admin_work_origin_cannot_be_forged_and_is_not_a_fault_label():
    with patch("app.services.execute", return_value=42) as execute, patch("app.services.fetch_one", return_value={"id":42}):
        create_work_order({"device_id":3, "title":"Inspect", "description":"Saw vibration",
                           "report_origin":"DETECTOR", "source_alert_id":99,
                           "event_started_at":"2026-09-07T12:00"}, 1)
    args = execute.call_args.args[1]
    assert args[8] == "ADMIN_WORK_ORDER"
    assert args[9] == datetime(2026,9,7,12)
    assert "source_alert_id" not in execute.call_args.args[0]


def test_wrong_machine_module_is_rejected_before_insert():
    with patch("app.services.fetch_one", return_value=None), patch("app.services.execute") as execute:
        with pytest.raises(HTTPException):
            create_work_order({"device_id":3, "module_id":99, "title":"Inspect"}, 1)
    execute.assert_not_called()


def test_service_snapshot_has_context_but_unknown_cause_and_label():
    order = {"id":42, "created_by":34, "description":"Hp2 changed", "event_started_at":datetime(2026,9,7,12),
             "report_origin":"ADMIN_WORK_ORDER"}
    snapshot = incident_snapshot(order)
    order["description"] = "Edited later"
    assert snapshot["description"] == "Hp2 changed"
    assert snapshot["created_by"] == 34
    assert snapshot["label_status"] == "UNREVIEWED"
    assert snapshot["cause_status"] == "UNKNOWN"


def test_logs_expose_snapshot_without_promoting_note_to_label():
    import json
    with patch("app.services.fetch_all", return_value=[{"id":63, "incident_context_json":json.dumps({
        "report_origin":"ADMIN_WORK_ORDER", "label_status":"UNREVIEWED"})}]):
        row = list_maintenance_logs()[0]
    assert row["incident_context"]["label_status"] == "UNREVIEWED"
