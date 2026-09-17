#!/usr/bin/env python3
"""Find the Python environment belonging to an existing Linecast installation.

Works as a small bootstrap on Python 3.8+; the app requires Python 3.10+.
No installations, config writes, package changes or network calls are performed.
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def usable_python(candidate):
    try:
        result = subprocess.run(
            [str(candidate), '-B', '-c',
             'import sys; assert sys.version_info >= (3,10); import linecast; assert linecast.__version__ == "2.6.1"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
            cwd=str(Path.home()))
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def script_candidates(script):
    """Resolve uv/pipx/Homebrew console-script siblings and Python shebangs."""
    path = Path(script).resolve()
    result = [str(path.parent / name) for name in ('python', 'python3', 'python.exe')]
    try:
        with path.open('rb') as stream:
            line = stream.readline(4096).decode('utf-8').strip()
        if line.startswith('#!'):
            interpreter = line[2:].strip()
            # Spaces in a literal interpreter path are valid discovery hints.
            if Path(interpreter).is_file() and 'python' in Path(interpreter).name.lower():
                result.insert(0, interpreter)
            else:
                parts = shlex.split(interpreter)
                if parts and 'python' in Path(parts[0]).name.lower():
                    result.insert(0, parts[0])
                elif len(parts) == 2 and Path(parts[0]).name == 'env' and parts[1].startswith('python'):
                    found = shutil.which(parts[1])
                    if found:
                        result.insert(0, found)
    except (OSError, UnicodeError, ValueError):
        pass
    # Windows pip scripts are one directory below their interpreter.
    result.append(str(path.parent.parent / 'python.exe'))
    return result


def manager_candidates():
    """Read-only environment discovery through installed package managers."""
    uv = shutil.which('uv')
    if uv:
        try:
            result = subprocess.run([uv, 'tool', 'dir'], capture_output=True,
                                    text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                root = Path(result.stdout.strip()) / 'linecast'
                yield str(root / 'bin' / 'python')
                yield str(root / 'Scripts' / 'python.exe')
        except (OSError, subprocess.SubprocessError):
            pass
    pipx = shutil.which('pipx')
    if pipx:
        try:
            result = subprocess.run([pipx, 'environment', '--value', 'PIPX_LOCAL_VENVS'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                root = Path(result.stdout.strip()) / 'linecast'
                yield str(root / 'bin' / 'python')
                yield str(root / 'Scripts' / 'python.exe')
        except (OSError, subprocess.SubprocessError):
            pass


def find_python():
    seen = set()
    def check(candidate):
        if candidate in seen:
            return False
        seen.add(candidate)
        return usable_python(candidate)
    if check(sys.executable):
        return sys.executable
    command = shutil.which('linecast')
    if command:
        for candidate in script_candidates(command):
            if check(candidate):
                return candidate
    for candidate in manager_candidates():
        if check(candidate):
            return candidate
    for name in ('python3', 'python', 'python3.14', 'python3.13', 'python3.12', 'python3.11', 'python3.10'):
        candidate = shutil.which(name)
        if candidate and check(candidate):
            return candidate
    return None


def main():
    python = find_python()
    if not python:
        print('Orrery could not find the Python environment containing Linecast.\n'
              'This companion uses your existing Linecast installation (tested with 2.6.1).\n'
              'Run it from the same terminal where linecast works, or run:\n'
              '  /path/to/linecast-environment/python app.py\n'
              'Nothing has been installed or changed.', file=sys.stderr)
        return 1
    if sys.argv[1:] == ['--diagnose']:
        print('Linecast Python:', python)
        return subprocess.call([python, '-B', '-c', 'import linecast; print("Linecast version:", linecast.__version__)'])
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    command = [python, '-B', str(ROOT / 'app.py')] + sys.argv[1:]
    if sys.platform == 'win32':
        # Windows has no POSIX process replacement. Keep the wrapper alive
        # for its child, preserving inherited console handles and exit status.
        return subprocess.call(command, env=env)
    os.execve(python, command, env)


if __name__ == '__main__':
    sys.exit(main())
