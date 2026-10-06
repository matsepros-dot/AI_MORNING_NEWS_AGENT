"""Resolve the installed Git for double-click and Task Scheduler environments."""
import json
import argparse
import os
import shutil
import subprocess
from pathlib import Path


def git_executable(root):
    runtime_path = root / 'config/runtime.json'
    if runtime_path.exists():
        executable = json.loads(runtime_path.read_text(encoding='utf-8'))['git_executable']
        if Path(executable).is_file():
            return executable
    executable = shutil.which('git')
    if executable:
        return executable
    candidates = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/cmd/git.exe',
                  Path.home() / 'AppData/Local/Programs/Git/cmd/git.exe',
                  Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe']
    return next((str(path) for path in candidates if path.is_file()), 'git')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--login', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    executable = git_executable(root)
    if args.login:
        config = json.loads((root / 'config/config.json').read_text(encoding='utf-8'))
        environment = os.environ.copy()
        environment['PATH'] = str(Path(executable).parent) + os.pathsep + environment.get('PATH', '')
        raise SystemExit(subprocess.call([executable, 'credential-manager', 'github', 'login',
                                        '--username', config['publish']['account'], '--browser', '--no-ui'], env=environment))
    subprocess.run([executable, '--version'], check=True)
    (root / 'config').mkdir(exist_ok=True)
    (root / 'config/runtime.json').write_text(json.dumps({'git_executable': executable}, indent=2) + '\n', encoding='utf-8')
    print('[PASS] Git runtime configured for Task Scheduler')
