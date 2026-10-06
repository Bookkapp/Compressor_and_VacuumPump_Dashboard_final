import unittest
from unittest.mock import patch

from app.analytics import correlation, relationship


ROWS = [
    {"recorded_at": "2026-09-07T10:00:00", "metric_key": "valve", "metric_value": 10},
    {"recorded_at": "2026-09-07T10:00:00", "metric_key": "lp_2nd", "metric_value": 2},
    {"recorded_at": "2026-09-07T10:05:00", "metric_key": "valve", "metric_value": 20},
    {"recorded_at": "2026-09-07T10:05:00", "metric_key": "lp_2nd", "metric_value": 4},
    {"recorded_at": "2026-09-07T10:10:00", "metric_key": "valve", "metric_value": 30},
    {"recorded_at": "2026-09-07T10:10:00", "metric_key": "lp_2nd", "metric_value": 6},
]


class AnalyticsTests(unittest.TestCase):
    @patch("app.analytics.get_metric_history", return_value=ROWS)
    def test_correlation_uses_only_paired_samples(self, _history):
        result = correlation(1, 2, ["valve", "lp_2nd"], "2026-09-07T09:00:00")
        self.assertEqual(result["samples"], 3)
        self.assertEqual(result["matrix"][0][1], 1.0)

    @patch("app.analytics.get_metric_history", return_value=ROWS)
    def test_relationship_returns_time_stamped_scatter_points(self, _history):
        result = relationship(1, 2, "valve", "lp_2nd")
        self.assertEqual(result["samples"], 3)
        self.assertEqual(result["points"][1], {"recorded_at": "2026-09-07T10:05:00", "x": 20.0, "y": 4.0})


if __name__ == "__main__":
    unittest.main()
