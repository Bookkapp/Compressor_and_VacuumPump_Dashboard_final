from contextlib import contextmanager
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import require_admin
from app.main import app
from app.services import get_numbering_status, reset_numbering, reset_work_orders


class NumberingResetTests(unittest.TestCase):
    def test_get_numbering_status(self) -> None:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        mock_cur.fetchall.return_value = [
            {"name": "pm_alerts", "next_id": 55},
            {"name": "pm_work_orders", "next_id": 28},
        ]
        mock_cur.fetchone.side_effect = [
            {"count": 54, "max_id": 54},
            {"count": 27, "max_id": 27, "active": 2},
            {"count": 10},
        ]

        with patch("app.services.connection", return_value=mock_conn):
            status = get_numbering_status()

        self.assertEqual(status["alerts"]["count"], 54)
        self.assertEqual(status["alerts"]["max_id"], 54)
        self.assertEqual(status["alerts"]["next_id"], 55)
        self.assertEqual(status["work_orders"]["count"], 27)
        self.assertEqual(status["work_orders"]["active"], 2)
        self.assertEqual(status["work_orders"]["next_id"], 28)

    def test_reset_numbering_invalid_target_raises_400(self) -> None:
        actor = {"sub": 1, "username": "admin", "role": "admin"}
        with self.assertRaises(HTTPException) as ctx:
            reset_numbering("invalid_target", actor)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_reset_numbering_all_triggers_both(self) -> None:
        actor = {"sub": 1, "username": "admin", "role": "admin"}
        with patch("app.services.clear_alerts", return_value={"ok": True, "deleted": 5}) as mock_alerts, \
             patch("app.services.reset_work_orders", return_value={"ok": True, "deleted": 3}) as mock_work, \
             patch("app.services.get_numbering_status", return_value={"alerts": {}, "work_orders": {}}):
            res = reset_numbering("all", actor)

        self.assertTrue(res["ok"])
        mock_alerts.assert_called_once()
        mock_work.assert_called_once_with(actor)

    def test_api_numbering_endpoints_require_admin(self) -> None:
        client = TestClient(app)

        # Without admin token -> 401
        res = client.get("/api/admin/numbering")
        self.assertIn(res.status_code, (401, 403))

        res = client.post("/api/admin/numbering/reset", json={"target": "alerts"})
        self.assertIn(res.status_code, (401, 403))

    def test_api_numbering_endpoints_with_admin(self) -> None:
        client = TestClient(app)
        admin_payload = {"sub": 1, "username": "ADIadmin", "role": "admin"}
        app.dependency_overrides[require_admin] = lambda: admin_payload

        try:
            with patch("app.main.get_numbering_status", return_value={"alerts": {"count": 0, "next_id": 1}, "work_orders": {"count": 0, "next_id": 1}}), \
                 patch("app.main.reset_numbering", return_value={"ok": True, "target": "all"}), \
                 patch("app.main._broadcast_current_state"):
                res = client.get("/api/admin/numbering")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json()["alerts"]["next_id"], 1)

                res = client.post("/api/admin/numbering/reset", json={"target": "all"})
                self.assertEqual(res.status_code, 200)
                self.assertTrue(res.json()["ok"])
        finally:
            app.dependency_overrides.pop(require_admin, None)


if __name__ == "__main__":
    unittest.main()
