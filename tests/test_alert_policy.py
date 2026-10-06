from datetime import datetime
import unittest
from unittest.mock import patch

from app.services import alert_should_insert


class AlertPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 16, 10, 30)
        cleared_at = patch("app.services._get_alerts_cleared_at", return_value=None)
        cleared_at.start()
        self.addCleanup(cleared_at.stop)

    def test_same_issue_and_severity_is_limited_to_once_per_day(self) -> None:
        with patch("app.services.fetch_one", side_effect=[{"severity": "warning"}, None]):
            allowed = alert_should_insert(10, 20, "vacuum_pressure_high", "warning", now=self.now)
        self.assertFalse(allowed)

    def test_severity_escalation_bypasses_daily_dedupe(self) -> None:
        with patch("app.services.fetch_one", side_effect=[{"severity": "warning"}, None]):
            allowed = alert_should_insert(10, 20, "vacuum_pressure_high", "critical", now=self.now)
        self.assertTrue(allowed)

    def test_acknowledgement_suppresses_same_issue_for_seven_day_window(self) -> None:
        with patch("app.services.fetch_one", side_effect=[None, {"severity": "warning"}]):
            allowed = alert_should_insert(10, 20, "vacuum_pressure_high", "warning", now=self.now)
        self.assertFalse(allowed)

    def test_different_issue_is_not_suppressed(self) -> None:
        with patch("app.services.fetch_one", side_effect=[None, None]):
            allowed = alert_should_insert(10, 20, "temperature", "warning", now=self.now)
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
