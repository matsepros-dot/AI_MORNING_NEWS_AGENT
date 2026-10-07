import copy
import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.schedule_policy import eligibility

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/config.json').read_text(encoding='utf-8'))
VN = timezone(timedelta(hours=7))


class SchedulePolicyTests(unittest.TestCase):
    def check(self, day, hour, minute, event='schedule', cron='0 2-10 7 10 *'):
        now = datetime(2026, 10, day, hour, minute, 59, tzinfo=VN)
        return eligibility(CONFIG, now, event, cron)[0]

    def test_all_trial_slots_and_final_minute(self):
        self.assertTrue(self.check(7, 8, 0, cron='0 1 * * *'))
        for hour in range(9, 18):
            self.assertTrue(self.check(7, hour, 0))
        self.assertTrue(self.check(7, 17, 30, cron='30 10 7 10 *'))

    def test_boundaries_and_delayed_publish_rejected(self):
        for hour, minute in [(7, 59), (17, 31), (18, 0)]:
            self.assertFalse(self.check(7, hour, minute))
            self.assertFalse(self.check(7, hour, minute, event='workflow_dispatch'))

    def test_normal_afternoon_suppressed_only_today(self):
        self.assertFalse(self.check(7, 13, 30, cron='30 6 * * *'))
        for day in (8, 9):
            self.assertTrue(self.check(day, 13, 30, cron='30 6 * * *'))
            self.assertTrue(self.check(day, 8, 0, cron='0 1 * * *'))

    def test_trial_expiration_and_year_are_checked(self):
        for day in (6, 8):
            self.assertFalse(self.check(day, 9, 0))
        self.assertFalse(eligibility(CONFIG, datetime(2027, 10, 7, 9, tzinfo=VN), 'schedule', '0 2-10 7 10 *')[0])

    def test_utc_conversion_and_unknown_schedule(self):
        self.assertTrue(eligibility(CONFIG, datetime(2026, 10, 7, 1, tzinfo=timezone.utc), 'schedule', '0 1 * * *')[0])
        self.assertFalse(eligibility(CONFIG, datetime(2026, 10, 7, 0, 59, tzinfo=timezone.utc), 'schedule', '0 1 * * *')[0])
        self.assertFalse(self.check(7, 9, 0, cron='* * * * *'))


if __name__ == '__main__':
    unittest.main()
