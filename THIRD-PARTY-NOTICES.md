# Third-party notices

## Linecast integration

This independent Orrery companion uses your **existing Linecast installation**. It was developed against Linecast 2.6.1 and uses its terminal engine, graphics primitives and observer-sky renderer. No copy of Linecast, its sky catalogues, or its runtime is included in this distribution.

- Linecast: https://github.com/ashuttl/linecast
- Author: Andrew Shuttleworth.
- Linecast code licence: MIT, copyright (c) 2025 Andrew Shuttleworth.
- Linecast's installed data retains its own catalogue attribution and licensing. See that project's `linecast/data/STARS.md`.

This is not an official Linecast release and does not imply endorsement by its authors.

## Orrery orbital model

The orbital module is adapted from the original **Orrery**, copyright (c) 2026 Chris M. / Promethean Dynamic, MIT. See `LICENSE`.

Planetary orbital elements and secular rates follow JPL's approximate planetary positions:
https://ssd.jpl.nasa.gov/planets/approx_pos.html

The original source project's JPL model uses the interval 1800-01-01 through 2050-01-01 UTC, inclusive; Earth denotes the Earth–Moon barycenter. It models heliocentric J2000-ecliptic geometry, not apparent positions. The local-sky view uses Linecast's observer-based ephemeris and catalogue instead. These are complementary views, not identical astronomical algorithms.

No original Orrery web textures, restricted fonts, credentials, private configuration or deployment files are included.
