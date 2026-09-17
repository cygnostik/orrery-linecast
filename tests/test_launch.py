"""Launcher discovery stays local and never installs or modifies Linecast."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class LaunchTests(unittest.TestCase):
    def test_module_exposes_launcher(self):
        spec = importlib.util.find_spec('launch')
        self.assertIsNotNone(spec, 'Orrery needs an installed-Linecast launcher')

    def test_current_linecast_interpreter_is_usable(self):
        import launch
        self.assertTrue(launch.usable_python(sys.executable))

    def test_other_linecast_version_is_not_usable(self):
        import launch
        import subprocess
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'linecast.py').write_text("__version__ = '2.6.0'\n", encoding='utf-8')
            def probe(command, **kwargs):
                command = list(command)
                command[-1] = 'import sys; sys.path.insert(0, ' + repr(directory) + '); ' + command[-1]
                return real_run(command, **kwargs)
            with patch.object(launch.subprocess, 'run', side_effect=probe):
                self.assertFalse(launch.usable_python(sys.executable))

    def test_windows_launcher_waits_and_propagates_exit_status(self):
        import launch
        with patch.object(launch, 'find_python', return_value=sys.executable), \
             patch.object(launch.sys, 'platform', 'win32'), \
             patch.object(launch.sys, 'argv', ['launch.py', '--json']), \
             patch.object(launch.os, 'execve') as replace_process, \
             patch.object(launch.subprocess, 'call', return_value=23) as child:
            self.assertEqual(launch.main(), 23)
        replace_process.assert_not_called()
        self.assertEqual(child.call_args.args[0][-1], '--json')
        self.assertEqual(child.call_args.kwargs['env']['PYTHONUTF8'], '1')

    def test_launcher_json_subprocess(self):
        import subprocess
        import json
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-B', str(root / 'launch.py'),
                                 '--json', '--date', '2000-01-01T12:00:00Z'],
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['utc'], '2000-01-01T12:00:00+00:00')

    def test_missing_interpreter_is_not_usable(self):
        import launch
        self.assertFalse(launch.usable_python('/not-an-interpreter/python'))

    def test_discovery_current_environment_first(self):
        import launch
        with patch.object(launch, 'usable_python', return_value=True):
            self.assertEqual(launch.find_python(), sys.executable)

    def test_installed_script_interpreter_with_spaces(self):
        import launch
        with tempfile.TemporaryDirectory(prefix='orrery launcher ') as d:
            root = Path(d)
            interpreter = root / 'python3'
            interpreter.touch()
            script = root / 'linecast'
            script.write_text('#!' + str(interpreter) + '\n')
            candidates = launch.script_candidates(script)
            self.assertIn(str(interpreter), candidates)

    def test_installed_bin_interpreter_candidates(self):
        import launch
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / 'linecast'
            script.write_text('#!/usr/bin/env python3\n')
            self.assertIn(str(Path(d).resolve() / 'python'), launch.script_candidates(script))

if __name__ == '__main__':
    unittest.main()
