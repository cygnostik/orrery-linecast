"""Exercise real geometry and the installed Linecast renderer, offline."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from app import OrreryApp, State, main, parse_date, payload, MIN_DATE
import render
from astronomy import BODIES, orbit_points
from linecast._graphics import visible_len

INSTANT = parse_date('2026-09-16T06:00:00Z')


class RenderTest(unittest.TestCase):
    def assertFrame(self, text, width, height):
        lines = text.splitlines()
        self.assertEqual(len(lines), height)
        for i, line in enumerate(lines):
            self.assertEqual(visible_len(line), width, f'row {i + 1}: {render.plain(line)!r}')

    def test_layouts_and_reproducibility(self):
        for width, height in ((80, 24), (120, 40), (60, 20), (40, 16)):
            instrument = OrreryApp(State(moment=INSTANT, playing=False), width, height)
            a = instrument.render_static()
            self.assertFrame(a, width, height)
            self.assertEqual(a, instrument.render_static())
            if width >= 60:
                self.assertTrue(any(0x2800 < ord(ch) < 0x2900 for ch in a))
                self.assertIn('SPACED / NOT TO SCALE', a)
                self.assertIn('UTC', a)

    def test_real_sky_is_offline_and_shares_utc(self):
        from linecast import sky
        original_size = sky.get_terminal_size
        for width, height in ((80, 24), (120, 40)):
            state = State(moment=INSTANT, playing=False, location=(34.05, -118.25), view='sky')
            with patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
                instrument = OrreryApp(state, width, height)
                with patch.object(sky, 'render', wraps=sky.render) as native:
                    text = instrument.render_static()
                    self.assertEqual(native.call_args.args[0], INSTANT)
                    self.assertEqual(native.call_args.args[1:3], (34.05, -118.25))
            self.assertIs(sky.get_terminal_size, original_size)
            self.assertFrame(text, width, height)
            self.assertIn('LINECAST SKY', text)
            self.assertIn('+34.050', text)
            self.assertEqual(state.moment, INSTANT)

    def test_sky_with_moon_above_horizon_uses_supported_icons(self):
        from linecast.sky import Scene
        moment = parse_date('2026-09-17T03:00:00Z')
        location = (34.05, -118.25)
        self.assertGreater(Scene(moment, *location).moon_alt, 0)
        instrument = OrreryApp(State(moment=moment, playing=False, location=location, view='sky'), 120, 40)
        self.assertFrame(instrument.render_static(), 120, 40)

    def test_sky_outside_modern_interval_is_labeled_educational(self):
        state = State(moment=MIN_DATE, playing=False, location=(0, 0), view='sky')
        text, _ = render.render_frame(state, 80, 24, camera=object())
        self.assertIn('SKY DATE OUTSIDE MODERN INTERVAL', text)
        self.assertIn('Educational display only', text)

    def test_sky_adapter_restored_after_renderer_failure(self):
        from linecast import sky
        state = State(moment=INSTANT, playing=False, location=(0, 0), view='sky')
        instrument = OrreryApp(state, 80, 24)
        original_size, original_banner = sky.get_terminal_size, sky.install_banner
        with patch.object(sky, 'render', side_effect=RuntimeError('render failure')):
            with self.assertRaises(RuntimeError):
                instrument.render_static()
        self.assertIs(sky.get_terminal_size, original_size)
        self.assertIs(sky.install_banner, original_banner)

    def test_unset_observer_is_not_a_fake_site(self):
        instrument = OrreryApp(State(moment=INSTANT, playing=False, view='sky'), 80, 24)
        with patch('linecast.sky.Scene', side_effect=AssertionError('must not create observer')):
            text = instrument.render_static()
        self.assertIn('OBSERVER UNSET', text)
        self.assertIn('No IP lookup', text)
        self.assertIsNone(payload(instrument.state)['observer'])

    def test_controls_keep_frames_in_bounds(self):
        for width, height in ((80, 24), (120, 40)):
            instrument = OrreryApp(State(moment=INSTANT, playing=False), width, height)
            for key in ('u', 'i', 't', '+', '9', '0', '?'):
                instrument.intercept('char:' + key)
                self.assertFrame(instrument.render_static(), width, height)
            instrument.intercept('escape')
            instrument.intercept('char:l')
            self.assertFrame(instrument.render_static(), width, height)

    def test_footer_brand_and_loop_status_do_not_wrap(self):
        state = State(moment=INSTANT, playing=False, loop=True)
        text = OrreryApp(state, 80, 24).render_static()
        self.assertIn('ORRERY.ProDyn.ai', text)
        self.assertIn('LOOP', text)
        self.assertEqual(sum('ORRERY.ProDyn.ai' in line for line in text.splitlines()), 1)
        narrow = OrreryApp(state, 60, 20).render_static()
        self.assertTrue(all(visible_len(line) == 60 for line in narrow.splitlines()))

    def test_confirmation_is_explicit_and_pauses_clock(self):
        instrument = OrreryApp(State(moment=INSTANT, playing=True), 80, 24)
        instrument.intercept('char:g')
        before = instrument.state.moment
        instrument.advance(60)
        self.assertEqual(instrument.state.moment, before)
        frame = instrument.render_static()
        self.assertIn('public-IP approximate lookup', frame)
        self.assertIn('saved or cached', frame)

    def test_native_theme_is_per_instance_and_preserves_default_palette(self):
        original = render.ORRERY_PALETTE
        native = render.palette_for('native')
        orrery = render.palette_for('orrery')
        OrreryApp(State(moment=INSTANT, playing=False, theme='native'), 80, 24).render_static()
        self.assertEqual(render.ORRERY_PALETTE, original)
        self.assertIsNot(native, orrery)

    def test_spaced_geometry_does_not_modify_science(self):
        state = State(moment=INSTANT, playing=False)
        for body in BODIES:
            points = orbit_points(body['id'], INSTANT, 12)
            original = [p.copy() for p in points]
            mapped = [render.project_orbit(p, body, state, 86, 28) for p in points]
            self.assertEqual(points, original)
            self.assertEqual(mapped[0], mapped[-1])
        self.assertLess(render.display_radius(BODIES[-1]) / render.display_radius(BODIES[0]),
                        BODIES[-1]['aAU'] / BODIES[0]['aAU'])

    def test_all_nine_bodies_selectable_and_drawn(self):
        instrument = OrreryApp(State(moment=INSTANT, playing=False), 120, 40)
        instrument.render_static()
        self.assertEqual({h[0] for h in instrument.hits}, {b['id'] for b in BODIES})
        for i, body in enumerate(BODIES):
            instrument.intercept('char:' + str(i + 1))
            self.assertEqual(instrument.state.selected, body['id'])
            self.assertFrame(instrument.render_static(), 120, 40)

    def test_json_contains_physical_coordinates_and_sky(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['--json', '--date', '2026-09-16', '--view', 'sky', '--location', '0,0']), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(len(data['bodies']), len(BODIES))
        self.assertEqual(data['observer'], {'latitude': 0.0, 'longitude': 0.0})
        self.assertIn('moon', data['sky'])
        self.assertGreater(data['bodies'][-1]['position']['radiusAU'], 20)
        self.assertEqual(data['utc'], '2026-09-16T00:00:00+00:00')


if __name__ == '__main__':
    unittest.main()
