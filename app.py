#!/usr/bin/env python3
"""Orrery — a small, offline astronomical instrument powered by Linecast.

Run ``python app.py --help``. All displayed clocks are UTC. The orbital
model is heliocentric; the adjacent sky is Linecast's observer-centred model.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

try:
    from linecast._live import LiveApp
except ImportError as exc:
    raise SystemExit('Orrery needs the existing Linecast 2.6.1 Python environment. Run launch.py, or run app.py with Linecast\'s Python interpreter.') from exc
from linecast._framebuffer import get_terminal_size
from astronomy import BODIES, MIN_DATE, MAX_DATE, position_at, validate_date, utc_now

BODY_IDS = tuple(body['id'] for body in BODIES)
SPEEDS = (1 / 24, 1.0, 6.0, 30.0, 120.0, 365.0)  # simulated days / real second


def parse_date(value: str) -> datetime:
    """ISO date/time; a missing offset explicitly means UTC, not local time."""
    try:
        result = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return validate_date(result)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f'date must be ISO UTC, between {MIN_DATE.date()} and {MAX_DATE.date()}: {exc}') from exc


def parse_location(value: str) -> tuple[float, float]:
    """Coordinates only. Never geocode, infer a site, or make a network call."""
    try:
        lat, lon = (float(part.strip()) for part in value.split(','))
    except (ValueError, TypeError) as exc:
        raise ValueError('location must be LAT,LON in decimal degrees') from exc
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('latitude must be -90..90 and longitude -180..180 (finite numbers)')
    return lat, lon


@dataclass
class State:
    moment: datetime = field(default_factory=utc_now)
    location: tuple[float, float] | None = None
    selected: str = 'earth'
    view: str = 'orbit'
    playing: bool = True
    speed_index: int = 2
    direction: int = 1
    compressed: bool = True
    inner: bool = False
    tilted: bool = True
    zoom: float = 1.0
    rotation: float = -18.0
    note: str = ''

    def __post_init__(self):
        self.moment = validate_date(self.moment)

    @property
    def speed(self):
        return SPEEDS[self.speed_index]

    @property
    def bodies(self):
        return BODIES[:4] if self.inner else BODIES


# Linecast 2.6.1 deliberately maps space/n together and does not expose Tab.
# Keep its complete CSI/SGR/UTF-8 parser, only extending the first byte and
# asking for printable text. Installed for this app's run, restored on exit.
def read_key_extended(fd, text=False, reader=None):
    from linecast import _live, _term
    reader = reader or _live._read_key
    original = _term.read_byte
    first = original(fd)
    if first is None:
        return None
    if first == b'\t':
        return 'key:tab'
    if first == b'\x03':
        return 'quit'
    pending = [first]

    def replay(source):
        return pending.pop() if pending else original(source)

    _term.read_byte = replay
    try:
        return reader(fd, text=True)
    finally:
        _term.read_byte = original


class OrreryApp(LiveApp):
    """One LiveApp and one clock for both orbital and native sky renderers."""
    interval = 1 / 20
    mouse = True

    def __init__(self, state=None, width=None, height=None):
        self.state = state or State()
        self.width, self.height = width, height
        self.hits = []
        self.help_open = False
        self.location_edit = False
        self.location_text = ''
        self.location_error = ''
        self.camera = None
        self._last_tick = time.monotonic()
        self._drag_rotation = None

    def dimensions(self):
        cols, rows = get_terminal_size()
        return self.width or cols, self.height or rows

    def advance(self, seconds):
        if not self.state.playing or self.help_open or self.location_edit:
            return
        days = max(0, seconds) * self.state.speed * self.state.direction
        self.shift_days(days, pause=False)

    def shift_days(self, days, pause=True):
        s = self.state
        try:
            new = s.moment + timedelta(days=days)
        except OverflowError:
            new = MAX_DATE if days > 0 else MIN_DATE
        if new > MAX_DATE or new < MIN_DATE:
            s.moment = max(MIN_DATE, min(MAX_DATE, new))
            s.playing = False
            s.note = 'Model date limit reached; reverse or reset with n.'
        else:
            s.moment = new
        if pause:
            s.playing = False

    def sky_camera(self):
        if self.camera is None and self.state.location is not None:
            from linecast._sky_live import Camera
            from linecast.sky import Scene, default_view
            cols, rows = self.dimensions()
            view = default_view(Scene(self.state.moment, *self.state.location), cols, rows - 5)
            self.camera = Camera(view.az, view.alt, view.fov, view.figures)
        return self.camera

    def render_static(self):
        from render import render_frame
        cols, rows = self.dimensions()
        result, self.hits = render_frame(self.state, cols, rows, self.sky_camera() if self.state.view == 'sky' else None,
                                        help_open=self.help_open,
                                        location_text=self.location_text if self.location_edit else None,
                                        location_error=self.location_error)
        return result

    def render(self, **_frame):
        now = time.monotonic()
        self.advance(now - self._last_tick)
        self._last_tick = now
        return self.render_static()

    def text_mode(self):
        return True

    def intercept(self, action):
        if self.location_edit:
            if action in ('escape', 'quit'):
                self.location_edit = False
                return True
            if action == 'key:enter':
                try:
                    self.state.location = parse_location(self.location_text)
                except ValueError as exc:
                    self.location_error = str(exc)
                else:
                    self.location_edit = False
                    self.camera = None
                    self.state.note = 'Observer set locally. Coordinates are not sent anywhere.'
                return True
            if action == 'key:backspace':
                self.location_text = self.location_text[:-1]
            elif action == 'key:kill':
                self.location_text = ''
            elif action.startswith('char:') and action[5:].isascii() and len(self.location_text) < 48:
                self.location_text += action[5:]
            return True
        if self.help_open:
            self.help_open = False
            self._last_tick = time.monotonic()
            return True
        if action in ('quit', 'char:q', 'char:Q'):
            # live_loop only knows 'quit'; let our input adapter map q below.
            if action != 'quit':
                raise _QuitRequested
            return False
        if action == 'escape':
            return True
        if action in ('fwd', 'back'):
            self.shift_days((1 if action == 'fwd' else -1) * (1 / 96 if self.state.view == 'sky' else 1))
            return True
        if action == 'key:tab':
            self.select_next()
            return True
        if action.startswith('char:'):
            return self.on_action(action[5:])
        if action.startswith('key:'):
            return self.on_action(action[4:])
        return False

    def select_next(self):
        ids = [body['id'] for body in self.state.bodies]
        i = ids.index(self.state.selected) if self.state.selected in ids else -1
        self.select(ids[(i + 1) % len(ids)])

    def select(self, body_id):
        self.state.selected = body_id
        if body_id not in [b['id'] for b in self.state.bodies]:
            self.state.inner = False
        if self.state.view == 'sky':
            self.aim_selected()

    def aim_selected(self, moon=False):
        cam = self.sky_camera()
        if cam is None:
            return
        from linecast.sky import Scene
        scene = Scene(self.state.moment, *self.state.location)
        if moon:
            alt, az, label = scene.moon_alt, scene.moon_az, 'Moon'
        else:
            entry = next((p for p in scene.planets if p[0] == self.state.selected), None)
            if entry is None:
                self.state.note = ('Earth is the observing platform in sky mode.' if self.state.selected == 'earth' else 'Pluto is not in the Linecast sky ephemeris.')
                return
            alt, az, label = entry[2], entry[3], self.state.selected.title()
        if alt < 0:
            self.state.note = f'{label}: {alt:+.1f}° altitude, below the horizon at this UTC.'
        else:
            self.state.note = f'{label}: {alt:+.1f}° altitude / {az:.1f}° azimuth.'
        cam.fly_to(az, max(8, alt))

    def on_action(self, key):
        s = self.state
        cam = self.sky_camera() if s.view == 'sky' else None
        if key in (' ', 'p'):
            s.playing = not s.playing
            self._last_tick = time.monotonic()
        elif key == 'n':
            s.moment = utc_now()
            s.playing = False
            s.note = 'UTC reset to now.'
        elif key == 'r':
            s.direction *= -1
        elif key in ('.', ','):
            s.speed_index = max(0, min(len(SPEEDS) - 1, s.speed_index + (1 if key == '.' else -1)))
        elif key in ('[', ']'):
            self.shift_days(1 if key == ']' else -1)
        elif key == 'v':
            s.view = 'sky' if s.view == 'orbit' else 'orbit'
            s.playing = False
            s.note = 'Shared UTC clock paused on view change. Space resumes.'
        elif key == 'l':
            self.location_edit = True
            self.location_text = '' if s.location is None else f'{s.location[0]:g},{s.location[1]:g}'
            self.location_error = ''
        elif key in ('?', 'h'):
            self.help_open = True
        elif key in '123456789' and len(key) == 1:
            self.select(BODY_IDS[int(key) - 1])
        elif key in ('+', '=', '-'):
            self.on_wheel(1 if key != '-' else -1, 0, 0)
        elif key in ('a', 'd', 'w', 's'):
            if cam is not None:
                cam.pan({'a': -1, 'd': 1}.get(key, 0), {'w': 1, 's': -1}.get(key, 0))
            elif key in ('a', 'd'):
                s.rotation = (s.rotation + (8 if key == 'd' else -8)) % 360
        elif key == 'c' and cam is not None:
            cam.figures = (cam.figures + 2) % 3
        elif key == 'm' and cam is not None:
            self.aim_selected(moon=True)
        elif key == 'u':
            s.compressed = not s.compressed
        elif key == 'i':
            s.inner = not s.inner
            s.zoom = 1
            if s.inner and s.selected not in BODY_IDS[:4]:
                s.selected = 'earth'
        elif key == 't':
            s.tilted = not s.tilted
        elif key == '0':
            s.zoom, s.rotation, s.tilted = 1.0, -18.0, True
            self.camera = None
        else:
            return False
        return True

    def on_wheel(self, direction, col, row):
        if self.help_open or self.location_edit:
            return False
        cam = self.sky_camera() if self.state.view == 'sky' else None
        if cam is not None:
            cam.zoom(1 / 1.25 if direction > 0 else 1.25)
        else:
            self.state.zoom = min(8, max(0.3, self.state.zoom * (1.16 if direction > 0 else 1 / 1.16)))
        return True

    def on_drag(self, dcol, drow, done):
        if self.help_open or self.location_edit:
            return False
        cam = self.sky_camera() if self.state.view == 'sky' else None
        if cam is not None:
            cols, _ = self.dimensions()
            from linecast.sky import focal_length
            cam.focal = focal_length(cols, cam.fov)
            return cam.release() if done else cam.drag(dcol, drow)
        if self._drag_rotation is None:
            self._drag_rotation = self.state.rotation
        self.state.rotation = (self._drag_rotation + dcol * 1.2) % 360
        if done:
            self._drag_rotation = None
        return bool(dcol or drow)

    def on_click(self, col, row):
        if self.help_open or self.location_edit:
            return False
        x, y = col - 1, row - 1
        candidates = [(abs(x - hx) + 2 * abs(y - hy), body_id)
                      for body_id, hx, hy, radius in self.hits
                      if abs(x - hx) <= radius and abs(y - hy) <= 1]
        if candidates:
            self.select(min(candidates)[1])
            return True
        return False

    def run(self):
        from linecast import _live
        original = _live._read_key
        _live._read_key = lambda fd, text=False: read_key_extended(fd, text, original)
        self._last_tick = time.monotonic()
        try:
            super().run()
        except _QuitRequested:
            pass  # LiveApp/live_loop's finally restored terminal and input modes.
        finally:
            _live._read_key = original


class _QuitRequested(Exception):
    pass


def build_parser():
    parser = argparse.ArgumentParser(description='Orrery — offline solar-system instrument, powered by Linecast.',
                                     epilog='UTC everywhere. ISO dates without an offset mean UTC. No location lookup or network access.')
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--print', dest='print_frame', action='store_true', help='print one frame (use --date for reproducibility)')
    output.add_argument('--json', action='store_true', help='emit physical coordinates and state as JSON')
    parser.add_argument('--date', metavar='ISO', help='initial UTC instant; YYYY-MM-DD or ISO timestamp')
    parser.add_argument('--location', metavar='LAT,LON', help='explicit decimal coordinates, east longitude positive; use --location=-34,-70 for negative latitude')
    parser.add_argument('--width', type=int, help='frame width, 40..300 columns')
    parser.add_argument('--height', type=int, help='frame height, 16..100 rows')
    parser.add_argument('--view', choices=('orbit', 'sky'), default='orbit')
    return parser


def payload(state):
    result = {'application': 'Orrery', 'utc': state.moment.isoformat(), 'view': state.view,
              'observer': None if state.location is None else {'latitude': state.location[0], 'longitude': state.location[1]},
              'selected': state.selected,
              'model': 'approximate heliocentric Keplerian elements; not for navigation',
              'referenceFrame': 'J2000 mean ecliptic/equinox; AU; UTC approximates TDB',
              'earthPosition': 'Earth–Moon barycenter, not the geocenter',
              'display': {'scale': 'spaced' if state.compressed else 'AU', 'body_sizes_to_scale': False},
              'bodies': [dict(body, position=position_at(body['id'], state.moment)) for body in BODIES]}
    if state.view == 'sky' and state.location is not None:
        from linecast.sky import Scene
        scene = Scene(state.moment, *state.location)
        result['sky'] = {'model': 'Linecast observer-centred ephemeris',
                         'sun': {'altitudeDeg': scene.sun_alt, 'azimuthDeg': scene.sun_az},
                         'moon': {'altitudeDeg': scene.moon_alt, 'azimuthDeg': scene.moon_az, 'illuminatedFraction': scene.moon_illum},
                         'planets': [{'id': p[0], 'altitudeDeg': p[2], 'azimuthDeg': p[3], 'magnitude': p[4]} for p in scene.planets]}
    return result


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    for value, lo, hi, label in ((args.width, 40, 300, 'width'), (args.height, 16, 100, 'height')):
        if value is not None and not lo <= value <= hi:
            parser.error(f'{label} must be {lo}..{hi}')
    try:
        moment = parse_date(args.date) if args.date else utc_now()
        location = parse_location(args.location) if args.location else None
    except ValueError as exc:
        parser.error(str(exc))
    state = State(moment=moment, location=location, view=args.view,
                  playing=not (args.print_frame or args.json or args.view == 'sky'))
    if args.json:
        print(json.dumps(payload(state), ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    instrument = OrreryApp(state, args.width, args.height)
    if args.print_frame or not (sys.stdin.isatty() and sys.stdout.isatty()):
        state.playing = False
        from linecast._live import print_frame
        print_frame(instrument.render_static())
    else:
        instrument.run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
