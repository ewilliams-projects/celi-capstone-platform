"""Checks on the saved map data in data/snapshots/ (no network needed)."""

import json
import unittest
from pathlib import Path

SNAPSHOTS = Path(__file__).parent.parent / "data" / "snapshots"


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((SNAPSHOTS / "manifest.json").read_text())

    def test_manifest_matches_the_files(self):
        files = sorted(p.stem for p in SNAPSHOTS.glob("*.geojson"))
        self.assertEqual(files, sorted(self.manifest))

    def test_each_snapshot_is_valid_and_documented(self):
        for name, info in self.manifest.items():
            with self.subTest(name):
                data = json.loads((SNAPSHOTS / f"{name}.geojson").read_text())
                self.assertEqual(data["type"], "FeatureCollection")
                self.assertEqual(len(data["features"]), info["features"])
                self.assertGreater(info["features"], 0)
                for key in ["title", "publisher", "license", "item_url", "layer_url", "saved_on"]:
                    self.assertTrue(info.get(key), f"{name} manifest is missing {key}")
                for feature in data["features"]:
                    self.assertIn(feature["geometry"]["type"],
                                  ["Polygon", "MultiPolygon", "LineString", "MultiLineString"])

    def test_snapshots_cover_colorado(self):
        # Every coordinate should sit in the continental U.S. (the state outlines include all of Texas).
        for name in self.manifest:
            data = json.loads((SNAPSHOTS / f"{name}.geojson").read_text())
            text = json.dumps([f["geometry"]["coordinates"] for f in data["features"]])
            numbers = [float(n) for n in text.replace("[", " ").replace("]", " ").replace(",", " ").split()]
            lons, lats = numbers[0::2], numbers[1::2]
            with self.subTest(name):
                self.assertGreater(min(lons), -125)
                self.assertLess(max(lons), -90)
                self.assertGreater(min(lats), 24)
                self.assertLess(max(lats), 50)

    def test_wholesale_suppliers_are_left_out(self):
        data = json.loads((SNAPSHOTS / "electric.geojson").read_text())
        names = {f["properties"]["NAME"] for f in data["features"]}
        self.assertFalse([n for n in names if n.startswith(("WAPA", "DESERET"))])
        self.assertIn("PUBLIC SERVICE CO OF COLORADO", names)


if __name__ == "__main__":
    unittest.main()
