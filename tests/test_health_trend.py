from datetime import datetime,timedelta
from unittest import TestCase
from unittest.mock import patch
from fastapi import HTTPException
from app.cache import cache
from app.services import get_fleet_health_trend
from app.health_history import hourly_trend,bucket_status
class FleetHealthTrendTests(TestCase):
    def setUp(self):cache.invalidate('fleet_health_trend:7d')
    def test_hourly_168_points_and_missing_are_not_good(self):
        now=datetime(2026,10,7,12,23)
        row=dict(hour_end=now.replace(minute=0),good=2,warning=1,repair_now=0,offline=3,not_evaluated=4,no_signal=0,maintenance=0,total_modules=10)
        with patch('app.health_history.fetch_all',return_value=[row]) as fetch:result=hourly_trend(now)
        self.assertEqual(len(result['points']),168)
        self.assertIsNone(result['points'][0]['good'])
        self.assertEqual(result['points'][-1]['not_evaluated'],4)
        self.assertTrue(result['points'][-1]['at'].endswith('+07:00'))
        self.assertIn('pm_fleet_health_hourly',fetch.call_args.args[0])
    def test_shared_cache_and_reject_other_ranges(self):
        with patch('app.health_history.hourly_trend',return_value={'points':[]}) as read:
            self.assertEqual(get_fleet_health_trend(),get_fleet_health_trend())
            read.assert_called_once()
        with self.assertRaises(HTTPException):get_fleet_health_trend('1m')
    def test_hour_end_connectivity_boundary_and_unsupported(self):
        end=datetime(2026,10,7,13)
        row=dict(signal_at=end-timedelta(minutes=30),status='NOT_EVALUATED')
        self.assertEqual(bucket_status(row,end,'compressor'),('NOT_EVALUATED','ONLINE'))
        row['signal_at']-=timedelta(seconds=1)
        self.assertEqual(bucket_status(row,end,'compressor'),('OFFLINE','OFFLINE'))
        self.assertEqual(bucket_status(None,end,'compressor'),('NOT_EVALUATED','UNKNOWN'))
