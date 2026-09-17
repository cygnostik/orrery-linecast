#!/usr/bin/env python3
"""POSIX controlling-TTY smoke/stress checks. No location request is consented to.

Run with the pinned Python: python scripts/pty_smoke.py --cycles 3
For a native port: python scripts/pty_smoke.py --command python -m linecast orrery
"""
import argparse
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time


def scenario(command, name, timeout):
    master, slave = pty.openpty()
    keep = os.dup(slave)
    def resize(cols, rows):
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    resize(120, 40)
    before = termios.tcgetattr(keep)
    def setup():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        os.tcsetpgrp(0, os.getpgrp())
    env = dict(os.environ, TERM='xterm-256color', LINECAST_COLOR='truecolor', PYTHONDONTWRITEBYTECODE='1')
    child = subprocess.Popen(command + ['--location=34.05,-118.25'], stdin=slave,
                             stdout=slave, stderr=slave, env=env, preexec_fn=setup)
    os.close(slave)
    steps = {
        'resize-and-quit': [(1, 'size', (80, 24)), (1.4, 'size', (40, 16)),
                            (1.8, 'size', (160, 50)), (2.2, 'key', b'v'), (3, 'key', b'q')],
        'modal-ctrl-c': [(1, 'key', b'l'), (1.4, 'key', b'\x03')],
        'SIGINT': [(1.5, 'signal', signal.SIGINT)],
        'SIGTERM': [(1.5, 'signal', signal.SIGTERM)],
        'help-site-loop': [(1, 'key', b'?'), (1.2, 'key', b'\x1b'), (1.5, 'key', b'b'),
                           (1.7, 'key', b'g'), (2, 'key', b'n'), (2.3, 'key', b'v'),
                           (2.5, 'key', b'g'), (2.8, 'key', b'\x1b'), (3.2, 'key', b'l'),
                           (3.5, 'key', b'\x15' + b'51.48,0'), (3.8, 'key', b'\r'),
                           (4.2, 'key', b'q')],
    }[name]
    data = bytearray()
    start = time.monotonic()
    timed_out = False
    try:
        while child.poll() is None and time.monotonic() - start < timeout:
            elapsed = time.monotonic() - start
            while steps and elapsed >= steps[0][0]:
                _, kind, value = steps.pop(0)
                if kind == 'size':
                    resize(*value)
                    child.send_signal(signal.SIGWINCH)
                elif kind == 'signal':
                    child.send_signal(value)
                else:
                    os.write(master, value)
            if select.select([master], [], [], .05)[0]:
                try:
                    data.extend(os.read(master, 65536))
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    break
        if child.poll() is None:
            timed_out = True
            child.terminate()
        drain_until = time.monotonic() + 3
        while time.monotonic() < drain_until:
            if select.select([master], [], [], .05)[0]:
                try:
                    chunk = os.read(master, 65536)
                    if not chunk:
                        break
                    data.extend(chunk)
                except OSError:
                    break
            elif child.poll() is not None:
                break
        if child.poll() is None:
            child.kill()
        child.wait(timeout=3)
        restored = termios.tcgetattr(keep) == before
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        os.close(keep)
        os.close(master)
    expected = {0, 130, -signal.SIGINT} if name in ('SIGINT', 'modal-ctrl-c') else {0}
    if name == 'SIGTERM':
        expected |= {143, -signal.SIGTERM}
    result = dict(scenario=name, exit_code=child.returncode, deadline=timed_out,
                  terminal_entered=b'\x1b[?1049h' in data,
                  terminal_exited=b'\x1b[?1049l' in data,
                  tty_attributes_restored=restored, traceback=b'Traceback' in data)
    result['passed'] = (child.returncode in expected and not timed_out and restored
                        and result['terminal_entered'] and result['terminal_exited']
                        and not result['traceback'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.cycles < 1 or args.timeout < 6:
        parser.error('cycles must be positive and timeout must be at least six seconds')
    root = Path(__file__).resolve().parents[1]
    command = args.command or [sys.executable, '-B', str(root / 'app.py')]
    results = []
    for cycle in range(args.cycles):
        for name in ('resize-and-quit', 'modal-ctrl-c', 'SIGINT', 'SIGTERM', 'help-site-loop'):
            result = scenario(command, name, args.timeout)
            result['cycle'] = cycle + 1
            results.append(result)
    print(json.dumps(dict(passed=sum(r['passed'] for r in results), total=len(results),
                         scenarios=results), indent=2))
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
