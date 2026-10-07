import json
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.check_schedule import assess, planned_slots

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/config.json').read_text(encoding='utf-8'))
VN = ZoneInfo('Asia/Ho_Chi_Minh')


class ScheduleDiagnosticTests(unittest.TestCase):
    def test_full_trial_and_next_day_normal_slots(self):
        slots = planned_slots(CONFIG, datetime(2026, 10, 7, 10, tzinfo=VN))
        self.assertEqual(len(slots), 20)
        self.assertEqual(slots[-1].strftime('%H:%M'), '17:30')
        self.assertEqual([x.strftime('%H:%M') for x in planned_slots(CONFIG, datetime(2026, 10, 8, tzinfo=VN))], ['08:00','13:30'])

    def test_missing_events_fail_but_future_slots_pending(self):
        result = assess(CONFIG, datetime(2026, 10, 7, 9, 11, tzinfo=VN), [], None)
        self.assertEqual(result['boundary'], 'NO_SCHEDULE_EVENT_OBSERVED')
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['slots'][3]['status'], 'PENDING')

    def test_manual_run_never_counts_as_schedule(self):
        run = dict(id=1, event='workflow_dispatch', created_at='2026-10-07T02:00:00Z', conclusion='success')
        result = assess(CONFIG, datetime(2026, 10, 7, 9, 11, tzinfo=VN), [run], '2026-10-07T09:01:00+07:00')
        self.assertEqual(result['scheduled_runs_today'], 0)
        self.assertEqual(result['status'], 'FAIL')

    def test_triggered_failure_distinct_from_missing_event(self):
        run = dict(id=1, event='schedule', created_at='2026-10-07T02:00:00Z', conclusion='failure')
        result = assess(CONFIG, datetime(2026, 10, 7, 9, 11, tzinfo=VN), [run], None)
        self.assertEqual(result['boundary'], 'SCHEDULED_RUN_FAILED')

    def test_page_older_than_success_detected(self):
        run = dict(id=1, event='schedule', created_at='2026-10-07T02:00:00Z', conclusion='success')
        result = assess(CONFIG, datetime(2026, 10, 7, 9, 11, tzinfo=VN), [run], '2026-10-07T08:50:00+07:00')
        self.assertEqual(result['boundary'], 'PUBLIC_PAGE_OLDER_THAN_SUCCESSFUL_RUN')

    def test_candidate_timestamp_does_not_prove_pass(self):
        run = dict(id=1, event='schedule', created_at='2026-10-07T02:00:00Z', conclusion='success')
        result = assess(CONFIG, datetime(2026, 10, 7, 9, 11, tzinfo=VN), [run], '2026-10-07T09:01:00+07:00')
        self.assertEqual(result['slots'][2]['run_ids'], [1])
        self.assertEqual(result['status'], 'PARTIAL')

    def test_disabled_workflow_reported_as_configuration(self):
        result = assess(CONFIG, datetime(2026, 10, 7, 9, 11, tzinfo=VN), [], None, 'disabled_manually')
        self.assertEqual(result['boundary'], 'WORKFLOW_CONFIGURATION')


if __name__ == '__main__':
    unittest.main()
