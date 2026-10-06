"""Use the existing Git Credential Manager session for this repository only.

No credential files are read, and credentials are never printed or persisted.
Cloud execution uses the workflow's GITHUB_TOKEN instead of this local helper.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
from src.runtime import git_executable

REPOSITORY = 'matsepros-dot/AI_MORNING_NEWS_AGENT'


def authenticated_session():
    result = subprocess.run([git_executable(ROOT), 'credential', 'fill'],
                            input='protocol=https\nhost=github.com\npath='+REPOSITORY+'.git\n\n',
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Git Credential Manager authentication unavailable; use GitHub Actions UI')
    credential = dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if not credential.get('password'):
        raise RuntimeError('Git Credential Manager did not provide GitHub authentication')
    session = requests.Session()
    session.headers.update({'Authorization':'Bearer '+credential['password'], 'Accept':'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28'})
    return session


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['status','dispatch','pages-status'])
    args=parser.parse_args()
    session=authenticated_session()
    base='https://api.github.com/repos/'+REPOSITORY
    if args.action=='dispatch':
        response=session.post(base+'/actions/workflows/morning-news.yml/dispatches',json={'ref':'main'},timeout=30)
        print('workflow_dispatch HTTP',response.status_code)
    elif args.action=='pages-status':
        response=session.get(base+'/pages',timeout=30)
        print('Pages HTTP',response.status_code)
        if response.ok:
            payload=response.json();print(json.dumps({k:payload.get(k) for k in ['status','build_type','source','html_url']},ensure_ascii=False))
    else:
        response=session.get(base+'/actions/workflows/morning-news.yml/runs',params={'per_page':3},timeout=30)
        print('Actions HTTP',response.status_code)
        if response.ok:
            print(json.dumps([{k:run.get(k) for k in ['id','event','status','conclusion','head_sha','html_url']} for run in response.json().get('workflow_runs',[])],indent=2))
    if not response.ok:
        # Print only the API error message; never request/headers/credentials.
        print('GitHub:',response.json().get('message','Request failed'))
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
