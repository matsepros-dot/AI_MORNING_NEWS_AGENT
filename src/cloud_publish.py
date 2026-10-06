"""Publish only generated artifacts on an ephemeral GitHub Actions runner."""
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.publisher import git
from src.logger_setup import setup_logger

GENERATED = ['index.html', 'archive', 'data/history.json', 'data/market.json']


def cloud_publish(root, config, logger, regenerate=None):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Cloud conflict recovery is restricted to ephemeral Actions runners')
    branch = config['publish']['branch']
    if git(root, 'branch', '--show-current') != branch:
        raise RuntimeError('Unexpected publish branch')
    remote = git(root, 'remote', 'get-url', 'origin').removesuffix('.git')
    if remote != config['publish']['remote'].removesuffix('.git'):
        raise RuntimeError('Unexpected publish remote')
    git(root, 'config', 'user.name', 'github-actions[bot]')
    git(root, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    for attempt in range(config.get('cloud_push_attempts', 3)):
        git(root, 'add', '--', *(name for name in GENERATED if (root/name).exists()))
        staged = git(root, 'diff', '--cached', '--name-only')
        if any(not any(name == path or name.startswith(path+'/') for path in GENERATED) for name in staged.splitlines()):
            raise RuntimeError('Unexpected staged paths in cloud runner')
        if staged:
            day = datetime.now(ZoneInfo(config['timezone'])).date().isoformat()
            git(root, 'commit', '-m', 'chore: update morning news '+day)
            logger.info('ACTIONS COMMIT OK')
        else:
            logger.info('ACTIONS NO CHANGES')
        try:
            git(root, 'push', 'origin', branch)
            logger.info('ACTIONS PUSH OK')
            return True
        except RuntimeError as exc:
            logger.warning('ACTIONS PUSH FAILED attempt=%d: %s', attempt+1, exc)
            if attempt+1 >= config.get('cloud_push_attempts', 3):
                raise
            git(root, 'fetch', 'origin', branch)
            # Discard only this ephemeral runner's derived commit/output, then
            # regenerate against the latest published history. Never force-push.
            git(root, 'reset', '--hard', 'origin/'+branch)
            if regenerate:
                regenerate()
            else:
                result = subprocess.run([sys.executable, 'src/main.py', '--no-publish'], cwd=root, timeout=600)
                if result.returncode not in (0, 2):
                    raise RuntimeError('Regeneration failed after push conflict')
    return False


if __name__ == '__main__':
    config = json.loads((ROOT/'config/config.json').read_text(encoding='utf-8'))
    logger = setup_logger(ROOT/'logs/agent.log')
    try:
        raise SystemExit(0 if cloud_publish(ROOT, config, logger) else 1)
    except Exception:
        logger.exception('ACTIONS PUBLISH FAILED')
        raise SystemExit(1)
