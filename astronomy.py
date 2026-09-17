"""Dependency-free port of Orrery's JPL approximate Keplerian model.

Sources: https://ssd.jpl.nasa.gov/planets/approx_pos.html (Table 1), and
https://ssd.jpl.nasa.gov/ftp/eph/planets/ioms/ExplSupplChap8.pdf (original
Table 8.10.2, including Pluto). Coefficients, secular rates, Newton solver,
and rotations retain the original science.js model, without Table 2b terms.

Positions are heliocentric J2000 mean ecliptic/equinox coordinates in AU;
x points toward the equinox and z toward ecliptic north. Earth denotes the
Earth–Moon barycenter, NOT the geocenter. UTC is used as approximate TDB:
no leap-second, light-time, or apparent-position corrections are made.
This is educational geometry, not a precision ephemeris or navigation tool;
Pluto retains the lower-accuracy original fit, not modern Horizons values.

Aware datetimes are normalized to UTC. The inclusive range is UTC midnight
1800-01-01 through 2050-01-01, conservatively NOT the end of 2050. Orbit
paths are instantaneous fitted ellipses sampled in eccentric anomaly, not
integrated future trajectories. Physical descriptors are fixed references;
the position solver uses secular rates, not periodDays or display scaling.

Radii (volume-equivalent mean km) and sidereal periods (Julian years times
365.25) come from https://ssd.jpl.nasa.gov/planets/phys_par.html. Mercury's
2.11 arcminute and Venus's 177.3 degree tilts come from JPL Horizons physical
headers (targets 199 and 299); remaining tilts follow NASA planet fact pages.
Pluto's coarse retrograde tilt is 180 - 57 degrees, not a fitted spin pole.
"""

from datetime import datetime, timezone
import math


MIN_DATE = datetime(1800, 1, 1, tzinfo=timezone.utc)
MAX_DATE = datetime(2050, 1, 1, tzinfo=timezone.utc)
_J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
_CENTURY_SECONDS = 36525 * 86400
_DEG = math.pi / 180

# Columns: a (AU), e (dimensionless), I, L, perihelion longitude, node
# (angles in degrees), followed by their rates per Julian century.
_ELEMENTS = {
    "mercury": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
                (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
    "venus": ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
              (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
    "earth": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0),
              (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0)),
    "mars": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
    "jupiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
                (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
    "saturn": ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
               (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
    "uranus": ((19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
               (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589)),
    "neptune": ((30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
                (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664)),
    "pluto": ((39.48211675, 0.24882730, 17.14001206, 238.92903833, 224.06891629, 110.30393684),
              (-0.00031596, 0.00005170, 0.00004818, 145.20780515, -0.04062942, -0.01183482)),
}
_PROPERTIES = (
    ("mercury", 2439.4, 0.2408467, 2.11 / 60),
    ("venus", 6051.8, 0.61519726, 177.3),
    ("earth", 6371.0084, 1.0000174, 23.4),
    ("mars", 3389.50, 1.8808476, 25),
    ("jupiter", 69911, 11.862615, 3),
    ("saturn", 58232, 29.447498, 26.73),
    ("uranus", 25362, 84.016846, 97.77),
    ("neptune", 24622, 164.79132, 28),
    ("pluto", 1188.3, 247.92065, 123),
)
BODIES = [
    {
        "id": body_id,
        "name": body_id.capitalize(),
        "aAU": _ELEMENTS[body_id][0][0],
        "eccentricity": _ELEMENTS[body_id][0][1],
        "inclinationDeg": _ELEMENTS[body_id][0][2],
        "radiusKm": radius,
        "periodDays": years * 365.25,
        "tiltDeg": tilt,
    }
    for body_id, radius, years, tilt in _PROPERTIES
]


def utc_now():
    """Return the current aware UTC datetime (without clamping the clock)."""
    return datetime.now(timezone.utc)


def validate_date(dt):
    """Normalize an aware datetime to UTC; reject invalid types/range.

    TypeError indicates a non-datetime; ValueError indicates a naive datetime
    or an instant outside the inclusive fitted-model interval.
    """
    if not isinstance(dt, datetime):
        raise TypeError("Expected a timezone-aware datetime")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Expected a timezone-aware datetime")
    try:
        result = dt.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("Date outside the fitted-model interval") from exc
    if not MIN_DATE <= result <= MAX_DATE:
        raise ValueError("Date outside 1800-01-01 through 2050-01-01 UTC midnight")
    return result


def _elements_at(body_id, dt):
    if not isinstance(body_id, str) or body_id not in _ELEMENTS:
        raise ValueError("Unknown body ID")
    t = (validate_date(dt) - _J2000).total_seconds() / _CENTURY_SECONDS
    base, rate = _ELEMENTS[body_id]
    return tuple(value + change * t for value, change in zip(base, rate))


def _wrap_degrees(value):
    # fmod preserves the source's signed remainder before its positive wrap.
    return math.fmod(math.fmod(value, 360) + 360, 360)


def _eccentric_anomaly(mean, eccentricity):
    eccentric = mean + eccentricity * math.sin(mean)
    for _ in range(20):
        correction = (eccentric - eccentricity * math.sin(eccentric) - mean) / (
            1 - eccentricity * math.cos(eccentric)
        )
        eccentric -= correction
        if abs(correction) < 1e-13:
            return eccentric
    raise RuntimeError("Kepler solver did not converge")


def _point_on_ellipse(elements, eccentric):
    a, e, inclination, _, perihelion, node = elements
    omega = (perihelion - node) * _DEG
    i = inclination * _DEG
    ascending = node * _DEG
    cw, sw = math.cos(omega), math.sin(omega)
    co, so = math.cos(ascending), math.sin(ascending)
    ci, si = math.cos(i), math.sin(i)
    xp = a * (math.cos(eccentric) - e)
    yp = a * math.sqrt(1 - e * e) * math.sin(eccentric)
    return {
        "x": (cw * co - sw * so * ci) * xp + (-sw * co - cw * so * ci) * yp,
        "y": (cw * so + sw * co * ci) * xp + (-sw * so + cw * co * ci) * yp,
        "z": sw * si * xp + cw * si * yp,
    }


def position_at(body_id, dt):
    """Return x/y/z/radiusAU (AU) and longitudeDeg [0, 360); Earth is EMB."""
    elements = _elements_at(body_id, dt)
    mean = (_wrap_degrees(elements[3] - elements[4] + 180) - 180) * _DEG
    point = _point_on_ellipse(elements, _eccentric_anomaly(mean, elements[1]))
    return {
        **point,
        "radiusAU": math.hypot(point["x"], point["y"], point["z"]),
        "longitudeDeg": _wrap_degrees(math.atan2(point["y"], point["x"]) / _DEG),
    }


def orbit_points(body_id, dt, count=240):
    """Return count+1 x/y/z points, closing with a copy of the first point.

    count must be an integer from 3 through 10,000 (not bool). Samples are
    uniform in eccentric anomaly, not time; coordinates remain physical AU.
    """
    if isinstance(count, bool) or not isinstance(count, int) or not 3 <= count <= 10000:
        raise ValueError("Orbit segment count must be an integer from 3 through 10000")
    elements = _elements_at(body_id, dt)
    points = [_point_on_ellipse(elements, 2 * math.pi * index / count) for index in range(count)]
    points.append(points[0].copy())
    return points
