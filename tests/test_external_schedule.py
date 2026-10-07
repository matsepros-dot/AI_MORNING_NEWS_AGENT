import copy
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from scripts.external_schedule_policy import eligibility
from scripts.schedule_policy import eligibility as github_eligibility

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
VN = ZoneInfo('Asia/Ho_Chi_Minh')


class ExternalScheduleTests(unittest.TestCase):
    def setUp(self):
        self.config = copy.deepcopy(CONFIG)
        self.config['scheduler_provider'] = 'cron-job.org'
        self.slot = datetime(2026, 10, 7, 14, 30, tzinfo=VN)
        self.inputs = {'source':'cron-job.org','requested_at':str(int(self.slot.timestamp()))}

    def test_standby_never_runs(self):
        self.assertFalse(eligibility(CONFIG,self.slot,'workflow_dispatch',self.inputs)[0])

    def test_external_activation_blocks_old_cron(self):
        self.assertFalse(github_eligibility(self.config,self.slot,'schedule','30 1-5,7-10 7 10 *')[0])

    def test_agreed_slot_and_short_queue_delay(self):
        self.assertTrue(eligibility(self.config,self.slot,'workflow_dispatch',self.inputs)[0])
        self.assertTrue(eligibility(self.config,self.slot+timedelta(minutes=3),'workflow_dispatch',self.inputs)[0])

    def test_wrong_time_date_and_excessive_delay(self):
        for delta in (timedelta(seconds=-1),timedelta(minutes=16),timedelta(days=1)):
            self.assertFalse(eligibility(self.config,self.slot+delta,'workflow_dispatch',self.inputs)[0])
        inputs = dict(self.inputs,requested_at=str(int((self.slot+timedelta(minutes=5)).timestamp())))
        self.assertFalse(eligibility(self.config,self.slot+timedelta(minutes=5),'workflow_dispatch',inputs)[0])

    def test_missing_invalid_source_and_rerun(self):
        for inputs in ({},dict(self.inputs,requested_at='invalid'),dict(self.inputs,source='manual')):
            self.assertFalse(eligibility(self.config,self.slot,'workflow_dispatch',inputs)[0])
        self.assertFalse(eligibility(self.config,self.slot,'workflow_dispatch',self.inputs,attempt=2)[0])

    def test_last_slot_cannot_publish_outside_window(self):
        slot = self.slot.replace(hour=17,minute=30)
        inputs = dict(self.inputs,requested_at=str(int(slot.timestamp())))
        self.assertTrue(eligibility(self.config,slot,'workflow_dispatch',inputs)[0])
        self.assertFalse(eligibility(self.config,slot+timedelta(minutes=1),'workflow_dispatch',inputs)[0])

    def test_tomorrow_only_two_slots(self):
        for hour,minute,allowed in ((8,0,True),(13,30,True),(10,30,False)):
            slot = datetime(2026,10,8,hour,minute,tzinfo=VN)
            inputs = dict(self.inputs,requested_at=str(int(slot.timestamp())))
            self.assertEqual(eligibility(self.config,slot,'workflow_dispatch',inputs)[0],allowed)

    def test_external_workflow_shares_lock_and_has_no_cron(self):
        workflow = yaml.safe_load((ROOT/'.github/workflows/external-news.yml').read_text())
        events = workflow.get('on',workflow.get(True))
        self.assertEqual(set(events),{'workflow_dispatch'})
        self.assertEqual(workflow['concurrency']['group'],'morning-news-production')
        self.assertEqual(workflow['permissions'],{'contents':'write'})


if __name__ == '__main__':
    unittest.main()
