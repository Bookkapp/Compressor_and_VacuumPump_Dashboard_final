from contextlib import contextmanager
from datetime import datetime
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.diagnostics import compute_diagnostics, threshold_pair
from app.services import (
    acknowledge_alert, alert_work_order_spec, create_maintenance_log,
    delete_maintenance_log, delete_work_order, update_device_status, update_module, update_work_order,
    _maintenance_costs,
)


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.lastrowid = 42
        self.next_row = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split())
        if "SELECT * FROM pm_alerts" in normalized and "FOR UPDATE" in normalized:
            self.next_row = dict(self.state["alert"])
        elif "SELECT id FROM pm_work_orders" in normalized:
            self.next_row = {"id": 42} if self.state["order_exists"] else None
        elif "SELECT id FROM pm_users" in normalized:
            self.next_row = {"id": 7}
        elif "INSERT INTO pm_work_orders" in normalized:
            self.state["order_exists"] = True
            self.state["inserts"].append(params)
        elif "UPDATE pm_alerts" in normalized:
            self.state["alert"]["acknowledged"] = 1
            self.state["updates"] += 1
        elif "SELECT * FROM pm_alerts" in normalized:
            self.next_row = dict(self.state["alert"])
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.next_row


class FakeConnection:
    def __init__(self, state):
        self.state = state
        self.cursor_instance = FakeCursor(state)

    def cursor(self):
        return self.cursor_instance

    def begin(self):
        self.state["begins"] += 1

    def commit(self):
        self.state["commits"] += 1

    def rollback(self):
        self.state["rollbacks"] += 1


class MaintenanceWorkflowTests(unittest.TestCase):
    def test_acknowledge_creates_one_assigned_work_order(self):
        state = {
            "alert": {"id": 19, "device_id": 3, "module_id": 5, "severity": "critical",
                      "title": "Estimated vacuum pressure critical", "message": "Check pump",
                      "issue_key": "vacuum_pressure_high", "acknowledged": 0},
            "order_exists": False, "inserts": [], "updates": 0,
            "begins": 0, "commits": 0, "rollbacks": 0,
        }

        @contextmanager
        def fake_connection():
            yield FakeConnection(state)

        with patch("app.services.connection", fake_connection):
            first = acknowledge_alert(19, 2, now=datetime(2026, 9, 23, 10))
            second = acknowledge_alert(19, 2, now=datetime(2026, 9, 23, 11))

        self.assertEqual(first["work_order_id"], 42)
        self.assertEqual(second["work_order_id"], 42)
        self.assertEqual(len(state["inserts"]), 1)
        self.assertEqual(state["inserts"][0][6], "CRITICAL")
        self.assertEqual(state["inserts"][0][7], 7)
        self.assertEqual(state["updates"], 1)
        self.assertEqual(state["commits"], 2)
        self.assertEqual(state["rollbacks"], 0)

    def test_alert_priority_mapping(self):
        self.assertEqual(alert_work_order_spec({"id": 1, "severity": "warning", "title": "Check"})[2], "HIGH")
        self.assertEqual(alert_work_order_spec({"id": 1, "severity": "info", "title": "Check"})[2], "MEDIUM")

    def test_warning_acknowledge_does_not_create_work_order(self):
        state = {"alert": {"id": 20, "device_id": 3, "module_id": 5, "severity": "warning", "title": "Watch",
                           "message": "Check later", "issue_key": "watch", "acknowledged": 0},
                 "order_exists": False, "inserts": [], "updates": 0, "begins": 0, "commits": 0, "rollbacks": 0}
        @contextmanager
        def fake_connection(): yield FakeConnection(state)
        with patch("app.services.connection", fake_connection):
            result = acknowledge_alert(20, 2, now=datetime(2026, 9, 23, 10))
        self.assertIsNone(result["work_order_id"])
        self.assertEqual(state["inserts"], [])
        self.assertEqual(state["updates"], 1)

    def test_delete_log_not_found(self):
        state = {"begins": 0, "commits": 0, "rollbacks": 0}
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, *_): pass
            def fetchone(self): return None
        class Connection:
            def cursor(self): return Cursor()
            def begin(self): state["begins"] += 1
            def commit(self): state["commits"] += 1
            def rollback(self): state["rollbacks"] += 1
        @contextmanager
        def fake_connection(): yield Connection()
        with patch("app.services.connection", fake_connection):
            with self.assertRaises(HTTPException) as raised:
                delete_maintenance_log(999, {"sub": 1, "username": "admin"})
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(state["rollbacks"], 1)

    def test_delete_last_linked_log_keeps_completed_order_closed_and_audits(self):
        state = {"sql": [], "commits": 0}
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql, *_): state["sql"].append(" ".join(sql.split()))
            def fetchone(self):
                sql = state["sql"][-1]
                if "FROM pm_maintenance_logs WHERE id" in sql: return {"id": 9, "work_order_id": 42}
                if "FROM pm_work_orders" in sql: return {"id": 42, "status": "DONE"}
                return {"count": 0}
        class Connection:
            def cursor(self): return Cursor()
            def begin(self): pass
            def commit(self): state["commits"] += 1
            def rollback(self): raise AssertionError("Unexpected rollback")
        @contextmanager
        def fake_connection(): yield Connection()
        with patch("app.services.connection", fake_connection):
            result = delete_maintenance_log(9, {"sub": 1, "username": "admin"})
        self.assertEqual(result["deleted_id"], 9)
        self.assertEqual(state["commits"], 1)
        self.assertTrue(any("INSERT INTO pm_deletion_audit" in sql for sql in state["sql"]))
        self.assertFalse(any("UPDATE pm_work_orders" in sql for sql in state["sql"]))

    def test_part_costs_are_computed_from_line_items(self):
        parts, _, other, total, summary = _maintenance_costs({"parts": [
            {"name": "Bearing", "quantity": 2, "unit_cost_baht": 125.50},
            {"name": "Seal", "quantity": 1, "unit_cost_baht": 40},
        ], "other_cost_baht": 75})
        self.assertEqual(len(parts), 2)
        self.assertEqual((other, total, summary), (75, 366, "Bearing, Seal"))

    def test_delete_active_work_order_restores_latest_diagnostic_and_audits(self):
        state = {"sql": [], "commits": 0}
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql, *_): state["sql"].append(" ".join(sql.split()))
            def fetchone(self):
                sql = state["sql"][-1]
                if "SELECT * FROM pm_work_orders" in sql: return {"id": 42, "device_id": 3, "module_id": 5, "status": "IN_PROGRESS"}
                if "FROM pm_maintenance_logs" in sql or "AND status = 'IN_PROGRESS'" in sql: return {"n": 0}
                if "FROM pm_diagnostic_snapshots" in sql: return {"condition_state": "MAINTENANCE_REQUIRED"}
                return None
            def fetchall(self):
                return [{"id": 5}] if "SELECT id FROM pm_modules" in state["sql"][-1] else [{"status": "MAINTENANCE_REQUIRED"}]
        class Connection:
            def cursor(self): return Cursor()
            def begin(self): pass
            def commit(self): state["commits"] += 1
            def rollback(self): raise AssertionError("Unexpected rollback")
        @contextmanager
        def fake_connection(): yield Connection()
        with patch("app.services.connection", fake_connection), patch("app.services.cache.invalidate"):
            result = delete_work_order(42, {"sub": 1, "username": "admin"})
        self.assertEqual(result["deleted_id"], 42)
        self.assertEqual(state["commits"], 1)
        self.assertTrue(any("INSERT INTO pm_deletion_audit" in sql for sql in state["sql"]))
        self.assertTrue(any("UPDATE pm_modules SET status = %s" in sql for sql in state["sql"]))
        self.assertTrue(any("UPDATE pm_devices SET status = %s" in sql for sql in state["sql"]))

    def test_compressor_threshold_update_is_rejected(self):
        with patch("app.services.fetch_one", return_value={"module_code": "compressor-m1", "telemetry_source": "compressor"}):
            with self.assertRaises(HTTPException) as raised:
                update_module(5, {"thresholds": {"enabled": True}})
        self.assertEqual(raised.exception.status_code, 400)

    def test_disabled_advanced_threshold_uses_default_limits(self):
        row = {"recorded_at": datetime(2026, 9, 23, 10), "temperature_c": 55,
               "current_a": 5, "vibration": 1.0, "pressure_kpa": -80}
        custom = {"enabled": True, "temperature_c": {"warning": 50, "critical": 60}}
        enabled = compute_diagnostics([dict(row)], custom, source="vacuum")
        disabled = compute_diagnostics([dict(row)], {**custom, "enabled": False}, source="vacuum")
        self.assertTrue(any(issue["issue_key"] == "temperature" for issue in enabled["alerts"]))
        self.assertFalse(any(issue["issue_key"] == "temperature" for issue in disabled["alerts"]))

    def test_zero_warning_threshold_is_not_replaced_by_default(self):
        self.assertEqual(threshold_pair({"current_a": {"warning": 0, "critical": 1}}, "current_a", 10, 15), (0, 1))

    def test_direct_work_order_completion_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            update_work_order(42, {"status": "DONE"}, {"sub": 7, "role": "admin"})
        self.assertEqual(raised.exception.status_code, 400)

    def test_linked_log_and_completion_share_one_transaction(self):
        state = {"begins": 0, "commits": 0, "rollbacks": 0, "sql": []}
        class LogCursor:
            lastrowid = 63
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql, params=()):
                state["sql"].append(" ".join(sql.split()))
            def fetchone(self):
                sql = state["sql"][-1]
                if "pm_work_orders" in sql:
                    return {"id": 42, "device_id": 3, "module_id": 5, "assigned_to": 7, "status": "IN_PROGRESS"}
                return {"id": 63, "work_order_id": 42}
            def fetchall(self): return [{"status": "NORMAL"}]
        class LogConnection:
            def begin(self): state["begins"] += 1
            def commit(self): state["commits"] += 1
            def rollback(self): state["rollbacks"] += 1
            def cursor(self): return LogCursor()
        @contextmanager
        def fake_connection(): yield LogConnection()
        token = {"sub": 7, "role": "user", "username": "tech"}
        with patch("app.services.connection", fake_connection), patch("app.services.get_user", return_value=None):
            row = create_maintenance_log({"device_id": 3, "module_id": 5, "work_order_id": 42,
                                          "action_taken": "Inspected pump"}, token)
        self.assertEqual(row["id"], 63)
        self.assertEqual((state["begins"], state["commits"], state["rollbacks"]), (1, 1, 0))
        self.assertTrue(any("INSERT INTO pm_maintenance_logs" in sql for sql in state["sql"]))
        self.assertTrue(any("UPDATE pm_work_orders SET status = 'DONE'" in sql for sql in state["sql"]))
        self.assertTrue(any("UPDATE pm_modules SET status = 'NORMAL'" in sql for sql in state["sql"]))
        self.assertTrue(any("UPDATE pm_devices SET status" in sql for sql in state["sql"]))

    def test_legacy_monitoring_is_not_exposed_as_device_status(self):
        with patch("app.services.fetch_all", return_value=[{"status": "MONITORING"}]), \
             patch("app.services.execute") as execute:
            self.assertEqual(update_device_status(3), "NORMAL")
        execute.assert_called_once_with("UPDATE pm_devices SET status = %s WHERE id = %s", ("NORMAL", 3))

    def test_admin_cannot_set_removed_monitoring_status(self):
        with self.assertRaises(HTTPException) as raised:
            update_module(5, {"status": "MONITORING"})
        self.assertEqual(raised.exception.status_code, 400)

    def test_manual_log_does_not_clear_live_module_fault(self):
        token = {"sub": 7, "role": "user", "username": "tech"}
        with patch("app.services.get_user", return_value=None), patch("app.services.execute", return_value=63), \
             patch("app.services.fetch_one", return_value={"id": 63}) as fetch_one, \
             patch("app.services.update_module") as update_module:
            row = create_maintenance_log({"device_id": 3, "module_id": 5,
                                          "action_taken": "Inspected pump"}, token)
        self.assertEqual(row["id"], 63)
        fetch_one.assert_called_once()
        update_module.assert_not_called()


if __name__ == "__main__":
    unittest.main()
