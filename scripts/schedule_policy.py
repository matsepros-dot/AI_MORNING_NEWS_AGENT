"""Date-bounded trial policy; uses only the Python standard library."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIETNAM = timezone(timedelta(hours=7))
NORMAL_CRONS = {'0 1 * * *', '30 6 * * *'}
TRIAL_CRONS = {'0 2-10 7 10 *', '30 10 7 10 *'}


def eligibility(config, now, event, cron=''):
    now = now.astimezone(VIETNAM)
    trial = config['schedule_trial']
    trial_day = now.date().isoformat() == trial['date']
    if event == 'schedule' and cron not in NORMAL_CRONS | TRIAL_CRONS:
        return False, 'Unknown schedule rejected'
    if event == 'schedule' and cron in TRIAL_CRONS and not trial_day:
        return False, 'Trial expired; no fetch or publish'
    if trial_day:
        # The whole 17:30 minute is eligible; from 17:31 onward reject.
        clock = now.strftime('%H:%M')
        if not trial['start'] <= clock <= trial['end']:
            return False, 'Outside trial window; no fetch or publish'
        if event == 'schedule' and cron == '30 6 * * *':
            return False, '13:30 normal run suppressed during hourly trial'
        return True, 'One-day trial window (manual runs are not schedule evidence)'
    return True, 'Normal schedule or authorized manual run'


def main():
    config = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    payload = json.loads(Path(event_path).read_text(encoding='utf-8')) if event_path else {}
    event = os.environ.get('GITHUB_EVENT_NAME', 'workflow_dispatch')
    now = datetime.now(VIETNAM)
    cron = payload.get('schedule', '')
    allowed, reason = eligibility(config, now, event, cron)
    result = dict(allowed=allowed, reason=reason, event=event, cron=cron, actual_time=now.isoformat())
    print(json.dumps(result, ensure_ascii=True))
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as stream:
            stream.write('allowed=' + str(allowed).lower() + '\n')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f'### Schedule policy\n\nEvent: `{event}`; cron: `{cron}`\n\n'
                         f'Actual check (Vietnam): `{now.isoformat()}`\n\n'
                         f'Allowed: **{allowed}** — {reason}\n\n')


if __name__ == '__main__':
    main()
