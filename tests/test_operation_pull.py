import json
from unittest import TestCase
from app.operation_pull import validate_message,source_time

class OperationPullContractTests(TestCase):
    def row(self):
        p=dict(module=1,status='NORMAL',mode='DETECTOR_LIVE',approved=True,profile_id='frozen',category='WITHIN_PROPOSED_STEADY')
        return dict(kind='STATUS',occurred_at='2026-10-07T10:00:00',payload_json=json.dumps(p))
    def test_shadow_cannot_certify_good(self):
        row=self.row();p=json.loads(row['payload_json']);p['mode']='DETECTOR_SHADOW';row['payload_json']=json.dumps(p)
        self.assertEqual(validate_message(row)['status'],'NOT_EVALUATED')
    def test_active_supported_and_invalid_contract(self):
        self.assertEqual(validate_message(self.row())['status'],'NORMAL')
        row=self.row();p=json.loads(row['payload_json']);p['module']=9;row['payload_json']=json.dumps(p)
        with self.assertRaises(ValueError):validate_message(row)
    def test_source_timezone_conversion(self):
        self.assertEqual(source_time('2026-10-07T03:00:00+00:00').hour,10)

    def test_unsupported_state_and_wrong_module_never_vote_good(self):
        row=self.row();p=json.loads(row['payload_json']);p['category']='STATE_GATE_EXCLUDED';row['payload_json']=json.dumps(p)
        self.assertEqual(validate_message(row)['status'],'NOT_EVALUATED')
        row['module']=2
        with self.assertRaises(ValueError):validate_message(row)
