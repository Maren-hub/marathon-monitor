"""Small route checks that run without the optional web-server packages."""

import json
import unittest

from backend.app.campus_route import (
    CampusRouteError,
    MODEL_TRACED_ROUTE_FILE,
    _length_km,
    parse_course_geojson,
)


class CampusRouteGeometryTests(unittest.TestCase):
    def test_bundled_model_route_is_closed_and_has_surface_heights(self) -> None:
        segments = parse_course_geojson(MODEL_TRACED_ROUTE_FILE.read_bytes(), "route")
        self.assertEqual([segment["id"] for segment in segments], ["S1", "S2", "S3", "S4", "S5"])
        self.assertEqual(segments[0]["coordinates"][0], segments[-1]["coordinates"][-1])
        for first, second in zip(segments, segments[1:]):
            self.assertEqual(first["coordinates"][-1], second["coordinates"][0])
        for segment in segments:
            self.assertEqual(len(segment["coordinates"]), len(segment["heights_m"]))
        self.assertAlmostEqual(sum(_length_km(segment["coordinates"]) for segment in segments), 1.794, places=3)

    def test_two_dimensional_route_keeps_ground_clamping_path(self) -> None:
        data = {"type": "Feature", "properties": {}, "geometry": {
            "type": "LineString", "coordinates": [[118.813, 32.083], [118.814, 32.083]]}}
        segment = parse_course_geojson(json.dumps(data).encode(), "route")[0]
        self.assertNotIn("heights_m", segment)

    def test_mixed_height_coordinates_are_rejected(self) -> None:
        data = {"type": "Feature", "properties": {}, "geometry": {
            "type": "LineString", "coordinates": [[118.813, 32.083, -150], [118.814, 32.083]]}}
        with self.assertRaises(CampusRouteError):
            parse_course_geojson(json.dumps(data).encode(), "route")


if __name__ == "__main__":
    unittest.main()
