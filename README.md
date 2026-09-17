# Orrery for Linecast

An interactive orbital instrument with a linked observing view and one UTC clock. Eight planets and Pluto, selectable portraits, simulated time, and physical or spaced orbital distances, drawn in your terminal.

![Orrery: Saturn selected, spaced orbital lanes, paused simulation](docs/images/orbit.png)

**Independent companion for Linecast 2.6.1.** It does not replace Linecast or modify its installed source. Python 3.10+ and a Unicode terminal are required. MIT licensed.

## Run

With [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/cygnostik/orrery-linecast.git
cd orrery-linecast
uv sync --locked
uv run python launch.py
```

Already have Linecast 2.6.1? Download/extract the source and run `python3 launch.py` (`py -3 launch.py` on Windows). The launcher finds its Python environment without installing anything. `Start Orrery.command` and `Start Orrery.bat` are optional convenience launchers.

Use **120×40 cells or larger** for the portrait/readout layout. **80×24** uses a compact layout. Truecolour is recommended; 256-colour, 16-colour and no-colour output are supported. No special font or Nerd Font is required.

```sh
uv run python launch.py --loop
uv run python launch.py --theme native
uv run python launch.py --view sky --location=51.48,0
uv run python launch.py --date 2400-01-01 --loop
uv run python launch.py --print --width 120 --height 40
uv run python launch.py --json --date 2000-01-01T12:00:00Z
uv run python launch.py --diagnose
```

`--theme orrery` is the default authored dark palette. `--theme native` follows Linecast's terminal-theme roles. `NO_COLOR=1` disables ANSI colour.

## Time and controls

Orbit opens animated at six simulated days per real second; entering the observing view pauses at the same instant. Dates without an offset mean UTC. Static and JSON output never animate.

Time stops at the model boundary by default. **`--loop` or `b`** enables forward/reverse wrapping across the supported interval. Looping is a playback control, not a claim that the solar system repeats exactly at either endpoint. See [model range and accuracy](docs/astronomy.md).

| Key | Action |
| --- | --- |
| Space / `p` | Pause/play |
| `,` / `.` | Slower/faster |
| `r` | Reverse time |
| `b` | Toggle looping |
| `[` / `]` | Step a day and pause |
| Left/right | Step a day in orbit, 15 minutes in sky |
| `n` | Current UTC time, paused |
| Tab / `1`–`9` | Select a planet; `9` selects Pluto |
| Click a body, label or inventory | Select a body |
| `+` / `-` / wheel | Zoom |
| `a` / `d` / drag | Rotate orbit |
| `u` | Spaced lanes / physical AU distances |
| `i` | Inner / full system |
| `t` | Tilted / top-down projection |
| `v` | Orbit / observing view |
| `l` | Enter latitude,longitude |
| `g` | Offer approximate IP-based location inference |
| WASD / drag in sky | Look around |
| `c` in sky | Cycle constellation figures |
| `m` in sky | Face the Moon |
| `0` | Reset camera |
| `?` | Controls and field notes |
| `q` | Quit and restore terminal |

## Observing site

![Linked sky view with an explicit example observing site](docs/images/sky.png)

**No location inference happens by default.** Supply `--location=LAT,LON` or press `l` for manual coordinates. Use an equals sign for a negative latitude, such as `--location=-34,-70`.

Press **`g` in either view** to request inference and confirm the public-IP lookup. Alternatively, **`--infer-location`** explicitly opts in at launch. This sends a request to a third-party location provider, which sees the connection's public IP. It is approximate: VPNs, proxies, shared connections and remote machines can place it somewhere other than the observer. The result is labelled inferred and can be replaced manually. Failed lookups leave manual entry available.

The observing site is shared by both views and exists only in memory. It changes the local sky, not the heliocentric orbit geometry. There is no location file, telemetry, or automatic geocoding.

## What the picture means

- Heliocentric positions use approximate JPL Keplerian elements. The [astronomy notes](docs/astronomy.md) identify the ranges, coefficients, frame and independent numerical checks.
- In the orbital model, Earth means the **Earth–Moon barycenter**. Coordinates are heliocentric J2000 mean-ecliptic/equinox, in AU; UTC approximates dynamical time.
- Spaced lanes retain each ellipse's shape but change its display distance. Physical-AU mode uses actual model distances. Body markers and portraits are illustrative, not physical size scales or surface maps.
- The sky is **Linecast's separate observer-centred model**. It shares the clock, not the orbital algorithm. Extending the orbit model does not certify sky accuracy over the extended interval. Pluto has no corresponding Linecast sky target; Earth is the observing platform.

This is an educational visual instrument, not a precision ephemeris or navigation tool.

## Tests and development

```sh
uv run python -B -m unittest discover -s tests -v
uv run python -B scripts/stress.py
# POSIX controlling-TTY checks; Linux/macOS only:
uv run python -B scripts/pty_smoke.py --cycles 3
```

The unit suite includes clock boundaries, looping, parsing, layout, theme isolation, offline location-provider mocks and astronomical regression fixtures. CI covers the platforms listed in [the workflow](.github/workflows/tests.yml). Unit CI does not certify every terminal emulator or native GUI launcher. Linux controlling-TTY checks exercise resizing, modal controls, signals and terminal restoration.

Reproduce the demonstration frames with `uv run --with pillow --with rich python scripts/capture_demo.py`. The captures use a fixed simulated UTC instant and explicit Greenwich-area coordinates, not inferred user data. Supply `--font` if the default development font path is unavailable.

The launcher accepts only Linecast **2.6.1**. This companion deliberately uses version-pinned internal APIs, including scoped adapters. A separate native integration is being prepared in [`cygnostik/linecast`, `feat/orrery`](https://github.com/cygnostik/linecast/tree/feat/orrery); it is not an upstream release or endorsement.

See [contributing](CONTRIBUTING.md), [third-party notices](THIRD-PARTY-NOTICES.md), and [MIT licence](LICENSE).

[ORRERY.ProDyn.ai](https://orrery.prodyn.ai) · [ProDyn.ai](https://prodyn.ai)
