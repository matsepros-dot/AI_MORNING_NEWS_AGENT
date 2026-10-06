import subprocess

# Explicit allowlist: never stage arbitrary local files such as KEY.txt.
TRACKED_PATHS = ['.gitignore', '.nojekyll', 'requirements.txt', 'INSTALL.cmd', 'RUN_AGENT.cmd',
                 'README.md', 'config', 'src', 'templates', 'static', 'index.html',
                 'archive', 'data/history.json', 'tests', 'scheduler/install_task.ps1', 'reports']


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if result.returncode:
        raise RuntimeError(f'git {args[0]} failed: {(result.stderr or result.stdout).strip()}')
    return result.stdout.strip()


def publish(root, logger, config):
    try:
        if git(root, 'branch', '--show-current') != config['publish']['branch']:
            raise RuntimeError('Refusing publish from unexpected branch')
        if git(root, 'remote', 'get-url', 'origin') != config['publish']['remote']:
            raise RuntimeError('Refusing publish to unexpected remote')
        git(root, 'add', '--', *(path for path in TRACKED_PATHS if (root / path).exists()))
        staged = git(root, 'diff', '--cached', '--name-only')
        allowed = lambda path: any(path == value or path.startswith(value + '/') for value in TRACKED_PATHS)
        if any(not allowed(path) for path in staged.splitlines()):
            raise RuntimeError('Unexpected staged paths; refusing commit')
        if staged:
            git(root, 'commit', '-m', 'Update morning news and agent')
            logger.info('GIT COMMIT OK')
        else:
            logger.info('GIT NO CHANGES')
        # Always push: an earlier failed push may have left an unpushed commit.
        git(root, 'push', 'origin', config['publish']['branch'])
        logger.info('GIT PUSH OK')
        return True
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        logger.error('GIT PUBLISH ERROR %s', exc)
        return False
