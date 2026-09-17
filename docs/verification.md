# Verification

The companion is pinned to Linecast **2.6.1**. It does not patch the installed package on disk. Its temporary in-process input/sky adapters are restored on exit or rendering failure; the separate native-port work removes those adapters.

## Local release checks

- **59 unit tests passed**, including looping in both directions, absurd/non-finite clock advances, explicit location consent and failure handling, two palettes, layout bounds, early-year formatting, genuine sky render pacing, and exact footer copy.
- **2,045 adversarial assertions passed:** 468 orbital layouts, 75 offline sky/layout cases, 1,500 seeded control events, and two overflow endpoint checks.
- **15 controlling-PTY scenarios passed**, five scenarios repeated three times: resize/quit, modal Ctrl-C, SIGINT, SIGTERM, and help/site/loop controls. Each restored terminal attributes and left the alternate screen, without a traceback or forced timeout. These were exercised on Linux; this does not certify an interactive Windows console.
- **10 colour checks passed:** both palettes in no-colour, 16-colour, 256-colour, truecolour, and `NO_COLOR` auto-detection. An explicit `LINECAST_COLOR` override follows Linecast's own precedence.
- One explicitly requested live public-IP lookup succeeded and was marked approximate/session-only. No inferred coordinates are included in the repository. Normal tests mock this service and require no network.
- Four independent numeric fixtures were checked against fresh JPL Horizons responses. See [astronomy notes](astronomy.md) for frame/time assumptions and tolerances.
- The launcher rejects incompatible Linecast versions. A clean locked project environment runs the CLI and tests.

The CI workflow runs the unit suite and static/JSON smoke checks on Linux, macOS, and Windows across the declared Python matrix. Its actual current result is shown on the repository's Actions page; local checks alone do not establish a remote CI result.

## Reproduce

```sh
uv sync --locked
uv run python -B -m unittest discover -s tests -v
uv run python -B scripts/stress.py
uv run python -B scripts/pty_smoke.py --cycles 3
```

`pty_smoke.py` is POSIX-only and creates a real controlling terminal/foreground process group. It never consents to a location lookup.

Optional static capture dependencies are isolated from the application:

```sh
LINECAST_COLOR=truecolor uv run --with pillow --with rich python scripts/capture_demo.py
```

The screenshots render actual ANSI application frames at a fixed example location and UTC date. The capture utility reproduces Unicode Braille dot cells when the selected font lacks those glyphs. It does not generate or replace astronomical imagery.

## Limits

- The orbital approximation is educational, not a precision/navigation ephemeris. Extended dates use a separate official fit, with an explicitly documented model-switch discontinuity.
- The observer sky uses Linecast's separate model. Dates outside the companion's modern observing interval show an explanatory screen instead of asserting an accurate sky frame.
- Public-IP inference identifies an approximate network location, not a device's physical position. VPNs, proxies, remote shells, and hosting networks can place it elsewhere.
- Rendering time varies by terminal, dimensions, colour mode, and machine. Sky paints are paced against measured cost; benchmark samples are not universal FPS promises.
