"""Read-only schedule diagnostics. Never dispatch, retry, fetch news or publish."""
import base64
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
import yaml
from bs4 import BeautifulSoup
from scripts.github_control import authenticated_session, REPOSITORY
from src.history import atomic_write


def planned_slots(config, now):
    now = now.astimezone(ZoneInfo(config['timezone']))
    trial = config.get('schedule_trial', {})
    if now.date().isoformat() == trial.get('date'):
        start = datetime.fromisoformat(trial['date'] + 'T' + trial['start']).replace(tzinfo=now.tzinfo)
        end = datetime.fromisoformat(trial['date'] + 'T' + trial['end']).replace(tzinfo=now.tzinfo)
        slots = []
        while start <= end:
            slots.append(start)
            start += timedelta(minutes=30)
        return slots
    return [datetime.combine(now.date(), datetime.strptime(t, '%H:%M').time(), now.tzinfo)
            for t in config['scheduler_times']]


def assess(config, now, runs, page_time, workflow_state='active', config_matches=True):
    slots = planned_slots(config, now)
    due = [x for x in slots if now >= x + timedelta(minutes=1)]
    scheduled = [r for r in runs if r['event'] == 'schedule'
                 and datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')).astimezone(now.tzinfo).date() == now.date()]
    matches = []
    for slot in slots:
        # Timestamp matches are candidates, not proof of the originating cron;
        # a much-delayed earlier event might arrive in a later slot's minute.
        candidate = [r['id'] for r in scheduled if slot <= datetime.fromisoformat(
            r['created_at'].replace('Z', '+00:00')) < slot + timedelta(minutes=1)]
        matches.append(dict(planned=slot.isoformat(), status='TIMESTAMP_CANDIDATE' if candidate
                            else 'NO_ON_TIME_RUN_OBSERVED' if slot in due else 'PENDING', run_ids=candidate))
    status, boundary = 'PARTIAL', 'SCHEDULE_TIMING_UNCONFIRMED'
    if workflow_state != 'active' or not config_matches:
        status, boundary = 'FAIL', 'WORKFLOW_CONFIGURATION'
    elif due and not scheduled:
        status, boundary = 'FAIL', 'NO_SCHEDULE_EVENT_OBSERVED'
    elif any(r.get('conclusion') in ('failure', 'cancelled', 'timed_out') for r in scheduled):
        status, boundary = 'FAIL', 'SCHEDULED_RUN_FAILED'
    elif page_time:
        successes = [r for r in scheduled if r.get('conclusion') == 'success']
        if successes and max(datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')) for r in successes) > datetime.fromisoformat(page_time):
            status, boundary = 'FAIL', 'PUBLIC_PAGE_OLDER_THAN_SUCCESSFUL_RUN'
    return dict(status=status, boundary=boundary, checked_at=now.isoformat(), public_update=page_time,
                scheduled_runs_today=len(scheduled), slots=matches,
                limitation='Run creation timestamps alone cannot prove the originating cron. GitHub internal dispatch logs are unavailable.')


def get_json(session, url, **kwargs):
    response = session.get(url, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def main():
    config = json.loads((ROOT / 'config/config.json').read_text(encoding='utf-8'))
    now = datetime.now(ZoneInfo(config['timezone']))
    try:
        session = authenticated_session()
        base = 'https://api.github.com/repos/' + REPOSITORY
        repo = get_json(session, base)
        workflow = get_json(session, base + '/actions/workflows/morning-news.yml')
        permissions = get_json(session, base + '/actions/permissions')
        content = get_json(session, base + '/contents/.github/workflows/morning-news.yml', params={'ref': repo['default_branch']})
        remote = yaml.safe_load(base64.b64decode(content['content']).decode('utf-8'))
        local = yaml.safe_load((ROOT / '.github/workflows/morning-news.yml').read_text(encoding='utf-8'))
        matches = remote == local and permissions['enabled'] and not repo['archived'] and not repo.get('disabled', False)
        runs = []
        for page in range(1, 11):
            batch = get_json(session, base + '/actions/workflows/morning-news.yml/runs',
                             params={'event': 'schedule', 'per_page': 100, 'page': page})['workflow_runs']
            runs.extend(batch)
            if len(batch) < 100 or datetime.fromisoformat(batch[-1]['created_at'].replace('Z', '+00:00')).astimezone(now.tzinfo).date() < now.date():
                break
        pages = get_json(session, base + '/pages/builds/latest')
        website = requests.get('https://matsepros-dot.github.io/AI_MORNING_NEWS_AGENT/',
                               params={'schedule_check': now.isoformat()}, timeout=30)
        website.raise_for_status()
        time = BeautifulSoup(website.text, 'html.parser').select_one('.edition time[datetime]')
        report = assess(config, now, runs, time['datetime'] if time else None, workflow['state'], matches)
        report['evidence'] = dict(default_branch=repo['default_branch'], workflow_state=workflow['state'],
                                  actions_enabled=permissions['enabled'], remote_matches=remote == local,
                                  pages_status=pages['status'], pages_commit=pages['commit'],
                                  runs=[{k:r.get(k) for k in ('id','event','status','conclusion','created_at','run_started_at','html_url')} for r in runs])
    except Exception as exc:
        # Never dump authenticated requests/headers/credential output.
        report = dict(status='PARTIAL', boundary='DIAGNOSTIC_UNAVAILABLE', checked_at=now.isoformat(),
                      error_type=type(exc).__name__, explanation='Check network/authentication; absence of evidence is not proof of a schedule failure.')
    atomic_write(ROOT / 'reports/schedule_diagnostic.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = [f"Result: {report['status']}", f"Boundary: {report['boundary']}", f"Checked: {report['checked_at']}",
             f"Public update: {report.get('public_update', 'unavailable')}", '',
             'Planned time | Observation | Candidate run IDs', '--- | --- | ---']
    lines += [f"{s['planned']} | {s['status']} | {s['run_ids']}" for s in report.get('slots', [])]
    atomic_write(ROOT / 'reports/schedule_diagnostic.md', '\n'.join(lines) + '\n')
    print(json.dumps({k:report.get(k) for k in ('status','boundary','checked_at','public_update','scheduled_runs_today')}, ensure_ascii=True))
    return {'PASS':0, 'PARTIAL':2, 'FAIL':1}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
