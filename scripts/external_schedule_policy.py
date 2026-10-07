"""Guard for authenticated workflow_dispatch from the external scheduler.

The source input is a label, not authentication. GitHub API authorization
must use a dedicated token limited to this repository and Actions:write.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def eligibility(config, now, event, inputs, attempt=1):
    if config.get('scheduler_provider', 'github') != 'cron-job.org':
        return False, 'External scheduler is in standby'
    if event != 'workflow_dispatch' or attempt != 1:
        return False, 'Unexpected event or rerun rejected'
    if inputs.get('source') != 'cron-job.org':
        return False, 'Unexpected source label'
    zone = ZoneInfo(config['timezone'])
    now = now.astimezone(zone)
    try:
        requested = datetime.fromtimestamp(int(inputs['requested_at']), zone)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return False, 'Missing or invalid request timestamp'
    slot = requested.replace(second=0, microsecond=0)
    if requested.date() != now.date():
        return False, 'Request from another date rejected'
    trial = config.get('schedule_trial', {})
    if slot.date().isoformat() == trial.get('date'):
        if not trial['start'] <= now.strftime('%H:%M') <= trial['end']:
            return False, 'Outside trial window'
        planned = trial['start'] <= slot.strftime('%H:%M') <= trial['end'] and slot.minute in (0, 30)
    else:
        planned = slot.strftime('%H:%M') in config['scheduler_times']
    if not planned:
        return False, 'Request does not match an agreed slot'
    delay = (now - slot).total_seconds()
    if not 0 <= delay <= 15 * 60:
        return False, 'Early or over-15-minute delayed request rejected'
    return True, 'External slot accepted; verify cron-job execution history for actual origin'


def main():
    config = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
    path = os.environ.get('GITHUB_EVENT_PATH')
    payload = json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
    now = datetime.now(ZoneInfo(config['timezone']))
    allowed, reason = eligibility(config, now, os.environ.get('GITHUB_EVENT_NAME', ''),
                                  payload.get('inputs', {}), int(os.environ.get('GITHUB_RUN_ATTEMPT', '1')))
    record = dict(allowed=allowed, reason=reason, actual_time=now.isoformat(),
                  requested_at=payload.get('inputs', {}).get('requested_at'))
    print(json.dumps(record, ensure_ascii=True))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            stream.write('allowed=' + str(allowed).lower() + '\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write('### External scheduler policy\n\n' + json.dumps(record, ensure_ascii=True) + '\n')


if __name__ == '__main__':
    main()
