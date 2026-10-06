from datetime import datetime, timedelta, timezone
import unittest

from app.connectivity import connection_state, operational_status


class ConnectionStateTests(unittest.TestCase):
    now = datetime(2026, 10, 6, 14, 0)

    def state(self, seconds, device='compressor:115'):
        return connection_state(self.now - timedelta(seconds=seconds), device, now=self.now)[0]

    def test_compressor_no_signal_window_precedes_offline(self):
        self.assertEqual(self.state(20*60), 'ONLINE')
        self.assertEqual(self.state(20*60+1), 'NO_SIGNAL')
        self.assertEqual(self.state(30*60), 'NO_SIGNAL')
        self.assertEqual(self.state(30*60+.1), 'OFFLINE')

    def test_vacuum_stale_window_then_no_signal_then_offline(self):
        for seconds, expected in [(15, 'ONLINE'), (30, 'STALE'), (90, 'STALE'), (91, 'NO_SIGNAL'), (1800, 'NO_SIGNAL'), (1801, 'OFFLINE')]:
            with self.subTest(seconds=seconds):
                self.assertEqual(self.state(seconds, 'vacuum:VP-07'), expected)

    def test_disconnected_condition_never_looks_good_and_recovers_without_write(self):
        for condition in ('NORMAL', 'WARNING', 'MAINTENANCE_REQUIRED', 'UNDER_MAINTENANCE'):
            with self.subTest(condition=condition):
                self.assertEqual(operational_status(condition, self.state(1801)), 'OFFLINE')
                self.assertEqual(operational_status(condition, self.state(5)), condition)
        self.assertEqual(operational_status('MONITORING', 'ONLINE'), 'NORMAL')
        self.assertEqual(operational_status('WARNING', 'NO_SIGNAL'), 'WARNING')

    def test_missing_or_invalid_timestamp_is_offline(self):
        for value in (None, '', 'invalid'):
            self.assertEqual(connection_state(value, now=self.now), ('OFFLINE', None))

    def test_utc_timestamp_and_bangkok_clock_use_elapsed_time(self):
        current = self.now.replace(tzinfo=timezone(timedelta(hours=7)))
        at = (current - timedelta(seconds=1801)).astimezone(timezone.utc).isoformat()
        self.assertEqual(connection_state(at, 'compressor:115', now=current), ('OFFLINE', 1801))

    def test_future_timestamp_never_has_negative_age(self):
        self.assertEqual(connection_state(self.now+timedelta(seconds=2), 'compressor:115', now=self.now), ('ONLINE', 0))


if __name__ == "__main__":
    unittest.main()
