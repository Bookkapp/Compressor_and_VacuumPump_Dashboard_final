from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from app.cache import cache
from app.services import get_fleet_health_trend


class FleetHealthTrendTests(TestCase):
    def setUp(self) -> None:
        cache.invalidate("fleet_health_trend:7d")
        self.now = datetime(2026, 9, 23, 12, 0)

    def tearDown(self) -> None:
        cache.invalidate("fleet_health_trend:7d")

    def test_daily_counts_observed_modules_and_preserves_gaps(self) -> None:
        rows = [
            {"day": self.now.date(), "module_id": 1, "condition_state": "NORMAL"},
            {"day": self.now.date(), "module_id": 2, "condition_state": "WATCH"},
            {"day": self.now.date(), "module_id": 3, "condition_state": "WARNING"},
            {"day": self.now.date(), "module_id": 4, "condition_state": "MAINTENANCE_REQUIRED"},
            {"day": self.now.date(), "module_id": 5, "condition_state": None},
        ]
        with patch("app.services.fetch_one", return_value={"db_now": self.now}), patch("app.services.fetch_all", return_value=rows) as fetch:
            result = get_fleet_health_trend("7d")
            again = get_fleet_health_trend("7d")
        self.assertEqual(len(result["points"]), 7)
        self.assertEqual(result["points"][-1], {"at": self.now.date().isoformat(), "good": 1, "warning": 2, "repair_now": 1, "observed": 4})
        self.assertIsNone(result["points"][0]["good"])
        self.assertEqual(result["points"][0]["observed"], 0)
        self.assertEqual(result, again)
        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.args[1], (self.now.date() - timedelta(days=6), self.now.date() + timedelta(days=1)))
        self.assertIn('MAX(source_recorded_at)',fetch.call_args.args[0])
        self.assertIn('ds.source_recorded_at',fetch.call_args.args[0])
        self.assertIn('legacy NULL excluded',result['time_basis'])

    def test_rejects_other_ranges(self) -> None:
        with self.assertRaises(HTTPException) as error:
            get_fleet_health_trend("1m")
        self.assertEqual(error.exception.status_code, 422)
