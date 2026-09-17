# Orrery — a Linecast companion

An animated orbital instrument and an adjacent observation view, sharing one UTC clock. Built for an existing **Linecast 2.6.1** installation. No bundled Linecast, sky catalogues, Python runtime, fonts or web assets.

## Open it

Unzip the whole folder, then:

- **macOS:** double-click `Start Orrery.command`.
- **Linux:** run `sh "Start Orrery.command"`.
- **Windows:** double-click `Start Orrery.bat`; Windows Terminal is recommended.
- **From a terminal:** `python3 launch.py` (or `py -3 launch.py` on Windows).

The launcher discovers the Python environment that already contains Linecast. It does not install anything, change your Linecast configuration or modify the package. Orrery uses Python 3.10+ from that environment. The small discovery launcher itself can run with Python 3.8+.

A Unicode-capable colour terminal is required. Use **120×40** or larger for the full portrait/readout layout; **80×24** has a compact layout. Truecolour offers the richest shading. Standard terminal fonts work; Nerd Fonts are not required.

The live application and macOS launcher were exercised on macOS. The Windows launcher is supplied but has not been run on Windows in this release.

## Use it

| Key / action | Effect |
|---|---|
| Space or `p` | Pause/play without resetting the date |
| `,` / `.` | Slower/faster simulation |
| `r` | Reverse time |
| `[` / `]` | Step backward/forward one day and pause |
| Left/right arrows | Step a day in orbit, 15 minutes in sky |
| `n` | Return to the current UTC time and pause |
| Tab or `1`–`9` | Select a planet; `9` selects Pluto |
| Click body, label or bottom inventory | Select a body |
| `+` / `-` or mouse wheel | Zoom |
| `a` / `d` or drag | Rotate orbital view |
| `u` | Spaced orbital lanes / true-AU distance scale |
| `i` | Inner system / full system |
| `t` | Tilted / top-down projection |
| `v` | Switch orbit / observation; pause at the same UTC instant |
| `l` | Enter latitude,longitude; Enter saves, Esc cancels |
| WASD or drag in sky | Look around |
| `c` in sky | Cycle constellation figures |
| `m` in sky | Face the Moon |
| `0` | Reset the camera |
| `?` | Controls and field notes |
| `q` | Quit and restore the terminal |

Orbit opens animated at six simulated days per real second. Observation mode is paused on entry. The date and speed remain visible. Sky mode uses Linecast's native sky renderer, star and constellation catalogues, Milky Way, planetary positions, Sun and Moon. Select a planet to aim toward it; below-horizon targets are identified as such. Earth is the observation platform, and Pluto is not part of Linecast's sky ephemeris.

### Your observing site

No site is inferred. Press `l` and enter decimal degrees, latitude first and east-positive longitude second. Coordinates remain in memory for the current run; they are not saved or sent over the network.

To supply a site on launch (the following is a Los Angeles example, not an inferred location):

```sh
python3 launch.py --location 34.05,-118.25 --view sky
```

For a negative latitude, use an equals sign:

```sh
python3 launch.py --location=-34,-70 --view sky
```

### Other commands

```sh
python3 launch.py --date 2026-09-16T05:00:00Z
python3 launch.py --print --width 120 --height 40
python3 launch.py --json --date 2000-01-01T12:00:00Z
python3 launch.py --diagnose
```

Dates without an offset are interpreted as UTC. `--print` renders a static frame; `--json` exports physical positions rather than display-scaled geometry. Neither starts animation. `--width` and `--height` are useful for static output; omit them for live resizing.

## What is being drawn

Orbital positions reuse the original Orrery's approximate JPL Keplerian model, including eccentricity, inclination and secular element rates. The accepted interval is **1800-01-01 through 2050-01-01 UTC**, inclusive. Earth is the **Earth–Moon barycenter** in this orbital model. Reference frame: heliocentric J2000 mean ecliptic/equinox; distances in AU. UTC is used as an approximation to dynamical time.

Spaced mode assigns readable orbital lanes while retaining each ellipse's shape. True-AU mode uses physical orbital distances. Body markers and the shaded sidebar portraits are illustrative, not physical size scales or surface maps. The radial profile is sampled along the fitted ellipse, not a time-axis forecast.

Observation uses **Linecast's separate observer-centred ephemeris**, evaluated at the same instant. It is an educational observing display, not a precision navigation instrument.

## If it does not open

1. Run `python3 launch.py --diagnose` from the terminal where `linecast` works.
2. The printed Linecast version should be **2.6.1**. This companion uses internal renderer APIs; compatibility with other versions is not assumed.
3. If the launcher cannot discover a custom installation, use its interpreter directly:
   `/path/to/linecast-environment/python app.py`.
4. On macOS, if executable permissions were lost during extraction, run `sh "Start Orrery.command"`.
5. If the application asks for more room, enlarge the terminal. At least 60×20 cells are needed.

No application configuration is written. Running the companion does not add an `orrery` subcommand to Linecast.

## Source and tests

`app.py` owns clock, input and view state; `render.py` composes the instrument and embeds Linecast's sky; `astronomy.py` contains the dependency-free orbital model; `launch.py` locates the installed dependency.

Run tests with the Python interpreter containing Linecast:

```sh
/path/to/linecast-environment/python -B -m unittest discover -s tests -v
```

The included numerical fixtures are portable references from the original Orrery. Node and the original web project are not required.

MIT licence. Copyright (c) 2026 Chris M. / Promethean Dynamic. Linecast by Andrew Shuttleworth is a separately installed dependency. See `THIRD-PARTY-NOTICES.md` and `LICENSE`.
