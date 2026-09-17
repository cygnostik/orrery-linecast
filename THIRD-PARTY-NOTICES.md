# Third-party notices

## Linecast

This independent companion uses a separately installed **Linecast 2.6.1**. It uses Linecast's terminal engine, graphics primitives, and observer-sky renderer. No Linecast source, catalogue, runtime, or fonts are bundled here.

- Project: https://github.com/ashuttl/linecast
- Tested revision: [`b0d4d14b533759a7564d7cecda1f6a0a87e12775`](https://github.com/ashuttl/linecast/tree/b0d4d14b533759a7564d7cecda1f6a0a87e12775)
- Author: Andrew Shuttleworth.
- Code: [MIT licence](https://github.com/ashuttl/linecast/blob/b0d4d14b533759a7564d7cecda1f6a0a87e12775/LICENSE), copyright (c) 2025 Andrew Shuttleworth.
- Installed sky data retains its own [catalogue attribution](https://github.com/ashuttl/linecast/blob/b0d4d14b533759a7564d7cecda1f6a0a87e12775/src/linecast/data/STARS.md).

This is not an official Linecast release and does not imply endorsement by its authors.

## Original Orrery

The orbital module is a Python adaptation of [Orrery](https://github.com/cygnostik/orrery), copyright (c) 2026 Chris M. / Promethean Dynamic, under the [MIT licence](https://github.com/cygnostik/orrery/blob/c7388feb1db609caa1d4843cde0fc615c57dafdd/LICENSE), reproduced in this repository's `LICENSE`.

The identified public reference revision is [`c7388feb1db609caa1d4843cde0fc615c57dafdd`](https://github.com/cygnostik/orrery/tree/c7388feb1db609caa1d4843cde0fc615c57dafdd), specifically [`src/science.js`](https://github.com/cygnostik/orrery/blob/c7388feb1db609caa1d4843cde0fc615c57dafdd/src/science.js). The supplied companion and its original `science_reference.json` fixture predate this repository; their exact export revision was not recorded. The fixture is a cross-language regression reference, not an independent astronomical reference. Independent checks and the extended model are documented in [astronomy notes](docs/astronomy.md).

No original web textures, restricted fonts, credentials, private configuration, or deployment files are included.

## Scientific sources

Orbital elements and secular rates follow [JPL's approximate planetary positions](https://ssd.jpl.nasa.gov/planets/approx_pos.html) and its linked [Explanatory Supplement chapter](https://ssd.jpl.nasa.gov/ftp/eph/planets/ioms/ExplSupplChap8.pdf). Earth denotes the Earth–Moon barycenter in the heliocentric model; UTC approximates dynamical time.

Linecast's local-sky view uses its own observer-based ephemeris and catalogue. Extending the heliocentric model's supported interval does not extend or certify the sky model's accuracy.
