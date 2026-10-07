from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import TestCase
from unittest.mock import patch
from app import services

class SharedSnapshotTests(TestCase):
    def tearDown(self):services.cache.invalidate('devices','summary')

    def test_expired_snapshot_burst_runs_one_metadata_query(self):
        services.cache.invalidate('devices');entered=Event();release=Event()
        def query():
            entered.set();assert release.wait(2);return []
        with patch.object(services,'latest_module_rows',side_effect=query) as sql:
            with ThreadPoolExecutor(max_workers=10) as pool:
                jobs=[pool.submit(services.list_devices) for _ in range(10)]
                self.assertTrue(entered.wait(1));release.set()
                self.assertEqual([j.result(timeout=2) for j in jobs],[[]]*10)
            self.assertEqual(sql.call_count,1)

    def test_failed_snapshot_releases_lock_and_can_retry(self):
        services.cache.invalidate('devices')
        with patch.object(services,'latest_module_rows',side_effect=[RuntimeError('QA'),[]]) as sql:
            with self.assertRaises(RuntimeError):services.list_devices()
            self.assertEqual(services.list_devices(),[])
            self.assertEqual(sql.call_count,2)
