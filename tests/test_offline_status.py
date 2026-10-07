from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from app.cache import cache
from app.services import get_summary, list_devices


class OfflineStatusTests(TestCase):
    def setUp(self):
        cache.invalidate('devices', 'summary')

    def tearDown(self):
        cache.invalidate('devices', 'summary')

    def test_summary_status_and_connectivity_have_consistent_offline_counts(self):
        now = datetime.now()
        rows = [
            {'device_uid': 'compressor:001', 'status': 'NORMAL', 'last_seen': now-timedelta(minutes=31)},
            {'device_uid': 'vacuum:002', 'status': 'WARNING', 'last_seen': now-timedelta(minutes=31)},
            {'device_uid': 'compressor:003', 'status': 'NORMAL', 'last_seen': now-timedelta(minutes=25)},
            {'device_uid': 'vacuum:004', 'status': 'MONITORING', 'last_seen': now-timedelta(seconds=5)},
        ]
        with patch('app.services.fetch_all', return_value=rows) as query, patch('app.services.fetch_one', return_value={}):
            result = get_summary()
        self.assertEqual(result['total_devices'], 4)
        self.assertEqual(result['counts']['OFFLINE'], 2)
        self.assertEqual(result['counts']['NORMAL'], 2)
        self.assertEqual(result['counts']['WARNING'], 0)
        self.assertEqual(result['connection_counts'], {'ONLINE': 2, 'STALE': 0, 'NO_SIGNAL': 0, 'OFFLINE': 2})
        query.assert_called_once()

    def test_device_and_modules_go_offline_preserving_historical_condition(self):
        row = dict.fromkeys(('location', 'thresholds_json', 'health_score_24h_baseline', 'temperature_c', 'pressure_kpa', 'current_a', 'vibration', 'ai_model_version', 'ai_condition', 'ai_confidence', 'ai_notes', 'diagnostic_at'))
        row.update(device_id=1, device_uid='vacuum:001', machine_code='001', display_name='001', device_status='NORMAL',
            last_seen=datetime.now()-timedelta(minutes=31), seconds_since_seen=1860, module_id=11, module_code='vacuum-pump', module_name='Vacuum Pump',
            module_type='Vacuum Pump', telemetry_source='vacuum', source_device_key='001', module_status='NORMAL', condition_state='NORMAL', health_score=99)
        with patch('app.services.latest_module_rows', return_value=[row]), patch('app.services.telemetry_sources.latest_for', return_value=None):
            device = list_devices()[0]
        self.assertEqual(device['status'], 'OFFLINE')
        self.assertEqual(device['connection_state'], 'OFFLINE')
        self.assertEqual(device['modules'][0]['status'], 'OFFLINE')
        self.assertEqual(device['modules'][0]['condition_state'], 'NORMAL')
        self.assertEqual(device['modules'][0]['health_score'], 99)
        self.assertEqual(row['module_status'], 'NORMAL')

    def test_reconnected_compressor_without_operation_result_is_not_good_or_offline(self):
        row = dict.fromkeys(('location', 'thresholds_json', 'health_score_24h_baseline', 'temperature_c', 'pressure_kpa', 'current_a', 'vibration', 'ai_model_version', 'ai_condition', 'ai_confidence', 'ai_notes', 'diagnostic_at'))
        row.update(device_id=1,device_uid='compressor:001',machine_code='001',display_name='001',device_status='OFFLINE',
            last_seen=datetime.now(),module_id=11,module_code='compressor-m1',module_name='M1',module_type='Compressor',
            telemetry_source='compressor',source_device_key='001',module_status='OFFLINE',condition_state='NORMAL',health_score=99)
        with patch('app.services.latest_module_rows',return_value=[row]), patch('app.services.fetch_all',return_value=[]), \
            patch('app.services.telemetry_sources.latest_for',return_value=None), patch('app.services.telemetry_sources.health_for',return_value=None), \
            patch.dict('app.operation_pull.operation_pull.status',{'enabled':True}):
            device=list_devices()[0]
        self.assertEqual(device['status'],'NOT_EVALUATED')
        self.assertEqual(device['connection_state'],'ONLINE')
        self.assertEqual(device['modules'][0]['status'],'NOT_EVALUATED')
        self.assertIsNone(device['modules'][0]['health_score'])
        self.assertTrue(device['modules'][0]['operation_pull_enabled'])
        self.assertFalse(device['modules'][0]['operation_result_fresh'])
