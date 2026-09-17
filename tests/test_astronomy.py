"""Portable science regression tests; run: python3 -m unittest discover -s tests.

The bounded fixture was produced by live Node imports of Orrery's science.js.
It checks fidelity to that implementation, not accuracy against the real sky.
Neither Node nor the original project is needed to run these tests.
"""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import unittest

import astronomy


UTC = timezone.utc
J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)
REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "science_reference.json").read_text(encoding="utf-8")
)


def parse_date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class AstronomyTests(unittest.TestCase):
    def test_positions_match_original_node_model(self):
        self.assertEqual(len(REFERENCE["positions"]), 72)
        self.assertEqual(len({row["date"] for row in REFERENCE["positions"]}), 8)
        for expected in REFERENCE["positions"]:
            with self.subTest(body=expected["id"], date=expected["date"]):
                actual = astronomy.position_at(expected["id"], parse_date(expected["date"]))
                self.assertEqual(set(actual), {"x", "y", "z", "radiusAU", "longitudeDeg"})
                for field in actual:
                    self.assertAlmostEqual(actual[field], expected[field], delta=2e-11)

    def test_body_descriptors_match_original(self):
        self.assertIsInstance(astronomy.BODIES, list)
        self.assertEqual(astronomy.BODIES, REFERENCE["bodies"])
        self.assertEqual(len({body["id"] for body in astronomy.BODIES}), 9)
        for body in astronomy.BODIES:
            self.assertIsInstance(body, dict)
            self.assertEqual(set(body), {
                "id", "name", "aAU", "eccentricity", "inclinationDeg",
                "radiusKm", "periodDays", "tiltDeg",
            })

    def test_orbits_match_original_node_model(self):
        self.assertEqual(len(REFERENCE["orbits"]), 27)
        for reference in REFERENCE["orbits"]:
            with self.subTest(body=reference["id"], date=reference["date"]):
                points = astronomy.orbit_points(
                    reference["id"], parse_date(reference["date"]), reference["count"]
                )
                self.assertEqual(len(points), reference["count"] + 1)
                for actual, expected in zip(points, reference["points"]):
                    self.assertEqual(set(actual), {"x", "y", "z"})
                    for axis in actual:
                        self.assertAlmostEqual(actual[axis], expected[axis], delta=2e-12)

    def test_orbits_close_with_independent_endpoint_and_default_count(self):
        for body in astronomy.BODIES:
            with self.subTest(body=body["id"]):
                points = astronomy.orbit_points(body["id"], J2000)
                self.assertEqual(len(points), 241)
                self.assertEqual(points[0], points[-1])
                self.assertIsNot(points[0], points[-1])
                points[-1]["x"] += 1
                self.assertNotEqual(points[0], points[-1])

    def test_j2000_orbit_perihelion_and_aphelion(self):
        for body in astronomy.BODIES:
            points = astronomy.orbit_points(body["id"], J2000, 12)
            perihelion = math.hypot(*points[0].values())
            aphelion = math.hypot(*points[6].values())
            self.assertAlmostEqual(perihelion, body["aAU"] * (1 - body["eccentricity"]), delta=2e-13)
            self.assertAlmostEqual(aphelion, body["aAU"] * (1 + body["eccentricity"]), delta=2e-13)

    def test_position_radius_and_longitude(self):
        for row in REFERENCE["positions"]:
            result = astronomy.position_at(row["id"], parse_date(row["date"]))
            self.assertAlmostEqual(result["radiusAU"], math.hypot(result["x"], result["y"], result["z"]))
            self.assertGreaterEqual(result["longitudeDeg"], 0)
            self.assertLess(result["longitudeDeg"], 360)
            self.assertTrue(all(math.isfinite(value) for value in result.values()))

    def test_inclusive_utc_endpoints(self):
        self.assertEqual(astronomy.MIN_DATE, datetime(1800, 1, 1, tzinfo=UTC))
        self.assertEqual(astronomy.MAX_DATE, datetime(2050, 1, 1, tzinfo=UTC))
        for endpoint in (astronomy.MIN_DATE, astronomy.MAX_DATE):
            self.assertIs(endpoint.tzinfo, UTC)
            self.assertEqual(astronomy.validate_date(endpoint), endpoint)
            for body in astronomy.BODIES:
                astronomy.position_at(body["id"], endpoint)
                astronomy.orbit_points(body["id"], endpoint, 3)
        for outside in (
            astronomy.MIN_DATE - timedelta(microseconds=1),
            astronomy.MAX_DATE + timedelta(microseconds=1),
            datetime(2050, 12, 31, tzinfo=UTC),
        ):
            for function in (astronomy.validate_date,
                             lambda dt: astronomy.position_at("earth", dt),
                             lambda dt: astronomy.orbit_points("earth", dt)):
                with self.subTest(date=outside, function=function), self.assertRaises(ValueError):
                    function(outside)

    def test_aware_offsets_normalize_to_same_instant(self):
        for instant in (astronomy.MIN_DATE, J2000, astronomy.MAX_DATE):
            for hours in (-8, 5.5, 14):
                local = instant.astimezone(timezone(timedelta(hours=hours)))
                result = astronomy.validate_date(local)
                self.assertIs(result.tzinfo, UTC)
                self.assertEqual(result, instant)
                self.assertEqual(astronomy.position_at("earth", local), astronomy.position_at("earth", instant))
                self.assertEqual(astronomy.orbit_points("earth", local, 3), astronomy.orbit_points("earth", instant, 3))

    def test_invalid_dates(self):
        for invalid in (None, "2000-01-01", "2000-01-01T12:00:00Z", 0, True, [], {}, J2000.date()):
            for function in (astronomy.validate_date,
                             lambda dt: astronomy.position_at("earth", dt),
                             lambda dt: astronomy.orbit_points("earth", dt)):
                with self.subTest(value=invalid), self.assertRaises(TypeError):
                    function(invalid)
        with self.assertRaises(ValueError):
            astronomy.validate_date(datetime(2000, 1, 1))
        # Overflow while normalizing an extreme civil date is also a range error.
        with self.assertRaises(ValueError):
            astronomy.validate_date(datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=14))))

    def test_unknown_body_ids(self):
        for body_id in ("", "Earth", "sun", "moon", "__proto__", "constructor", None, 0, [], {}):
            for function in (astronomy.position_at, astronomy.orbit_points):
                with self.subTest(body=body_id, function=function), self.assertRaises(ValueError):
                    function(body_id, J2000)

    def test_orbit_count_validation(self):
        for count in (0, -1, 2, 10001, 3.0, 4.5, True, False, None, "12", float("nan"), float("inf")):
            with self.subTest(count=count), self.assertRaises(ValueError):
                astronomy.orbit_points("earth", J2000, count)
        for count in (3, 10000):
            points = astronomy.orbit_points("earth", J2000, count)
            self.assertEqual(len(points), count + 1)
            self.assertEqual(points[0], points[-1])

    def test_earth_period_behavior(self):
        earth = next(body for body in astronomy.BODIES if body["id"] == "earth")
        self.assertAlmostEqual(earth["periodDays"], 1.0000174 * 365.25)
        start = astronomy.position_at("earth", J2000)

        def displacement(days):
            end = astronomy.position_at("earth", J2000 + timedelta(days=days))
            return math.hypot(*(end[axis] - start[axis] for axis in ("x", "y", "z")))

        self.assertGreater(displacement(1), 0.015)
        self.assertLess(displacement(1), 0.020)
        self.assertGreater(displacement(earth["periodDays"] / 2), 1.9)
        # Near one revolution, not an exact repeat: elements keep evolving.
        self.assertLess(displacement(earth["periodDays"]), 0.002)
        self.assertGreater(displacement(earth["periodDays"]), 1e-9)
        original_period = earth["periodDays"]
        future_date = J2000 + timedelta(days=100)
        future_position = astronomy.position_at("earth", future_date)
        try:
            earth["periodDays"] = 1
            self.assertEqual(astronomy.position_at("earth", future_date), future_position)
        finally:
            earth["periodDays"] = original_period

    def test_utc_now_is_current_aware_utc(self):
        before = datetime.now(UTC)
        actual = astronomy.utc_now()
        after = datetime.now(UTC)
        self.assertIs(actual.tzinfo, UTC)
        self.assertLessEqual(before, actual)
        self.assertLessEqual(actual, after)


if __name__ == "__main__":
    unittest.main()
