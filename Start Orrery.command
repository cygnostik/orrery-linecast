#!/bin/sh
# macOS: double-click. Linux: sh './Start Orrery.command'.
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUTF8=1
for PYTHON in python3 python python3.14 python3.13 python3.12 python3.11 python3.10; do
  if command -v "$PYTHON" >/dev/null 2>&1 && "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' >/dev/null 2>&1; then
    "$PYTHON" -B "$ROOT/launch.py" "$@"
    STATUS=$?
    if [ "$STATUS" -ne 0 ] && [ -t 0 ]; then
      printf '\nPress Enter to close. '
      read -r REPLY
    fi
    exit "$STATUS"
  fi
done
if command -v uv >/dev/null 2>&1; then
  TOOLROOT=$(uv tool dir 2>/dev/null)
  if [ -n "$TOOLROOT" ] && [ -x "$TOOLROOT/linecast/bin/python" ]; then
    exec "$TOOLROOT/linecast/bin/python" -B "$ROOT/launch.py" "$@"
  fi
fi
printf '\nOpen this folder in the terminal where Linecast works, then run:\n  python3 launch.py\n\nPress Enter to close. '
read -r REPLY
exit 1
