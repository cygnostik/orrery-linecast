"""Control and command-line contracts, without a terminal or network."""
import contextlib
import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import app

MOMENT = datetime(2026, 9, 16, 0, 0, tzinfo=timezone.utc)


class ControlsTest(unittest.TestCase):
    def setUp(self):
        self.app = app.OrreryApp(app.State(moment=MOMENT, playing=False), width=80, height=24)

    def key(self, key):
        return self.app.intercept('char:' + key)

    def test_pause_keeps_instant_and_reverse(self):
        self.key(' ')
        self.app.advance(1)
        self.assertGreater(self.app.state.moment, MOMENT)
        self.key(' ')
        frozen = self.app.state.moment
        self.app.advance(20)
        self.assertEqual(self.app.state.moment, frozen)
        self.key('r')
        self.key(' ')
        self.app.advance(1)
        self.assertLess(self.app.state.moment, frozen)

    def test_steps_pause_and_modes_share_time(self):
        self.key(']')
        self.assertEqual(self.app.state.moment, MOMENT + timedelta(days=1))
        self.assertFalse(self.app.state.playing)
        self.key('v')
        self.assertEqual(self.app.state.view, 'sky')
        self.assertEqual(self.app.state.moment, MOMENT + timedelta(days=1))
        self.assertIsNone(self.app.state.location)
        self.key('v')
        self.assertEqual(self.app.state.view, 'orbit')

    def test_selection_scale_camera(self):
        self.key('8')
        self.assertEqual(self.app.state.selected, 'neptune')
        self.app.intercept('key:tab')
        self.assertEqual(self.app.state.selected, 'pluto')
        self.app.intercept('key:tab')
        self.assertEqual(self.app.state.selected, 'mercury')
        self.key('u')
        self.assertFalse(self.app.state.compressed)
        self.key('i')
        self.assertTrue(self.app.state.inner)
        self.key('t')
        self.assertFalse(self.app.state.tilted)
        before = self.app.state.rotation
        self.key('d')
        self.assertNotEqual(before, self.app.state.rotation)
        self.key('+')
        self.assertGreater(self.app.state.zoom, 1)

    def test_location_prompt_validates_without_geolocation(self):
        self.key('l')
        for char in 'nan,0':
            self.key(char)
        self.app.intercept('key:enter')
        self.assertIsNone(self.app.state.location)
        self.assertTrue(self.app.location_edit)
        self.app.intercept('key:kill')
        for char in '34.05,-118.25':
            self.key(char)
        self.app.intercept('key:enter')
        self.assertEqual(self.app.state.location, (34.05, -118.25))
        self.assertFalse(self.app.location_edit)

    def test_limits_stop_clock(self):
        self.app.state.moment = app.MAX_DATE
        self.app.state.playing = True
        self.app.advance(60)
        self.assertEqual(self.app.state.moment, app.MAX_DATE)
        self.assertFalse(self.app.state.playing)

    def test_loop_wraps_overshoot_both_directions_and_is_off_by_default(self):
        self.assertFalse(self.app.state.loop)
        self.key('b')
        self.assertTrue(self.app.state.loop)
        self.key('b')
        self.assertFalse(self.app.state.loop)
        self.app.state.loop = True
        self.app.state.moment = app.MAX_DATE
        self.app.shift_days(2, pause=False)
        self.assertEqual(self.app.state.moment, app.MIN_DATE + timedelta(days=2))
        self.app.state.moment = app.MIN_DATE
        self.app.shift_days(-2, pause=False)
        self.assertEqual(self.app.state.moment, app.MAX_DATE - timedelta(days=2))

    def test_nonfinite_and_absurd_advances_are_safe(self):
        frozen = self.app.state.moment
        self.app.state.playing = True
        self.app.advance(float('nan'))
        self.assertEqual(self.app.state.moment, frozen)
        self.app.advance(float('inf'))
        self.assertEqual(self.app.state.moment, app.MAX_DATE)
        self.assertFalse(self.app.state.playing)
        self.app.state.playing = True
        self.app.shift_days(-1e300, pause=False)
        self.assertEqual(self.app.state.moment, app.MIN_DATE)
        self.assertFalse(self.app.state.playing)

    def test_inferred_location_requires_confirmation_and_is_session_only(self):
        self.key('g')
        self.assertTrue(self.app.location_confirm)
        self.app.advance(60)
        self.assertEqual(self.app.state.moment, MOMENT)
        from linecast import _location
        provider = ('test', 'https://example.invalid', lambda data: (12.5, -45.5, 'ZZ'))
        with patch.object(_location, 'PROVIDERS', (provider,)), patch('linecast._http.fetch_json', return_value={}):
            self.app.intercept('key:enter')
        self.assertEqual(self.app.state.location, (12.5, -45.5))
        self.assertTrue(self.app.state.location_inferred)
        self.assertIn('approximate', self.app.state.note)

    def test_inferred_location_failure_keeps_ui_usable(self):
        from linecast import _location
        provider = ('test', 'https://example.invalid', lambda data: (_ for _ in ()).throw(ValueError('bad')))
        with patch.object(_location, 'PROVIDERS', (provider,)), patch('linecast._http.fetch_json', return_value={}):
            self.assertFalse(self.app.infer_location())
        self.assertIsNone(self.app.state.location)
        self.assertIn('sky remains usable', self.app.state.note)

    def test_default_mode_never_calls_ip_lookup(self):
        with patch('linecast._http.fetch_json', side_effect=AssertionError('implicit lookup')):
            self.assertEqual(app.main(['--json', '--date', '2026-09-16']), 0)

    def test_mouse_selects_inventory(self):
        self.app.render_static()
        hit = next(h for h in self.app.hits if h[0] == 'saturn')
        self.app.on_click(hit[1] + 1, hit[2] + 1)
        self.assertEqual(self.app.state.selected, 'saturn')

    def test_reset_now_and_help(self):
        with patch('app.utc_now', return_value=MOMENT):
            self.key(']')
            self.key('n')
        self.assertEqual(self.app.state.moment, MOMENT)
        self.key('?')
        self.assertTrue(self.app.help_open)
        self.app.intercept('escape')
        self.assertFalse(self.app.help_open)


class ArgumentsTest(unittest.TestCase):
    def test_dates_and_coordinates(self):
        self.assertEqual(app.parse_date('2026-09-16'), MOMENT)
        self.assertEqual(app.parse_date('2026-09-16T02:00:00+02:00'), MOMENT)
        self.assertEqual(app.parse_location('-90,180'), (-90, 180))
        for invalid in ('nan,0', '0,inf', '91,0', '0,181', 'London', '0,0,0'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                app.parse_location(invalid)

    def test_bad_args_clean_failure(self):
        bad_date = ((app.MAX_DATE + timedelta(days=1)).date().isoformat()
                    if app.MAX_DATE.year < 9999 else 'not-a-date')
        for argv in (['--date', 'no'], ['--width', '0'], ['--height', '-3'],
                     ['--location', 'nan,0'], ['--view', 'moon'],
                     ['--date', bad_date], ['--print', '--json']):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    app.main(argv)
                self.assertEqual(caught.exception.code, 2)

    def test_loop_and_theme_arguments_are_explicit(self):
        args = app.build_parser().parse_args(['--loop', '--theme', 'native', '--infer-location'])
        self.assertTrue(args.loop)
        self.assertEqual(args.theme, 'native')
        self.assertTrue(args.infer_location)

    def test_extended_reader_tab_space_and_mouse(self):
        from linecast import _term
        from linecast._live import _read_key
        for byte, expected in ((b'\t', 'key:tab'), (b' ', 'char: '), (b'n', 'char:n'), (b'\x03', 'quit')):
            with patch.object(_term, 'read_byte', return_value=byte):
                self.assertEqual(app.read_key_extended(0, reader=_read_key), expected)

    def test_extended_reader_retains_arrow_and_sgr_parser(self):
        from linecast import _term
        from linecast._live import _read_key
        for raw, expected in ((b'\x1b[C', 'fwd'), (b'\x1b[<0;12;10M', ('mouse', 0, 12, 10, False))):
            stream = iter(bytes([byte]) for byte in raw)
            with patch.object(_term, 'read_byte', side_effect=lambda fd: next(stream, None)), patch.object(_term, 'wait_readable', return_value=True):
                self.assertEqual(app.read_key_extended(0, reader=_read_key), expected)


if __name__ == '__main__':
    unittest.main()
